-- Existing text-only records remain published. Drafts never appear in normal API queries.
alter table public.catch_logs add column status text not null default 'ready'
    check (status in ('pending', 'ready', 'cleanup_pending', 'deleting'));
alter table public.catch_logs add column cleanup_after timestamptz;

-- Retain only a small idempotency receipt after a failed draft or deleted catch is cleaned.
create table public.catch_log_submissions (
    user_id uuid not null references public.users(id) on delete cascade,
    submission_id uuid not null,
    fingerprint text not null check (fingerprint ~ '^[a-f0-9]{64}$'),
    log_id uuid references public.catch_logs(id) on delete set null,
    status text not null check (status in ('pending', 'ready', 'failed', 'deleted')),
    created_at timestamptz not null default now(),
    primary key (user_id, submission_id)
);

create table public.catch_log_photos (
    id uuid primary key,
    catch_log_id uuid not null references public.catch_logs(id) on delete cascade,
    photo_order smallint not null check (photo_order between 1 and 2),
    bucket text not null check (bucket = 'catch-photos'),
    object_path text not null unique,
    content_type text not null default 'image/jpeg' check (content_type = 'image/jpeg'),
    size_bytes integer not null check (size_bytes > 0),
    width integer not null check (width > 0),
    height integer not null check (height > 0),
    metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
    status text not null default 'pending'
        check (status in ('pending', 'uploaded', 'ready', 'deleting')),
    created_at timestamptz not null default now(),
    unique (catch_log_id, photo_order)
);
create index catch_logs_cleanup_idx on public.catch_logs (status, updated_at)
    where status <> 'ready';

alter table public.catch_log_photos enable row level security;
alter table public.catch_log_submissions enable row level security;
revoke all on public.catch_log_photos, public.catch_log_submissions
    from public, anon, authenticated;
grant select, insert, update, delete on public.catch_log_photos, public.catch_log_submissions
    to service_role;

-- One RPC = one PostgreSQL transaction. Only the backend service role may call these.
create function public.begin_catch_submission(
    p_user_id uuid, p_submission_id uuid, p_fingerprint text,
    p_log_id uuid, p_values jsonb, p_photos jsonb
) returns jsonb language plpgsql set search_path = '' as $$
declare
    receipt public.catch_log_submissions;
    photo jsonb;
begin
    -- Serialize the same user/submission across backend workers, not with a Python lock.
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || p_submission_id::text, 0));
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and submission_id = p_submission_id for update;
    if found then
        if receipt.fingerprint <> p_fingerprint then
            return jsonb_build_object('outcome', 'conflict');
        end if;
        return jsonb_build_object('outcome', receipt.status, 'log_id', receipt.log_id);
    end if;
    if jsonb_typeof(p_photos) <> 'array' or jsonb_array_length(p_photos) > 2 then
        raise exception 'Invalid photo count';
    end if;
    insert into public.catch_logs (
        id, user_id, species_name, caught_at, length_cm, weight_g,
        fishing_method, notes, status
    ) values (
        p_log_id, p_user_id, p_values->>'species_name', (p_values->>'caught_at')::timestamptz,
        (p_values->>'length_cm')::numeric, (p_values->>'weight_g')::numeric,
        p_values->>'fishing_method', p_values->>'notes', 'pending'
    );
    for photo in select value from jsonb_array_elements(p_photos) loop
        if photo->>'object_path' <>
            p_user_id::text || '/' || p_log_id::text || '/' || (photo->>'id') || '.jpg' then
            raise exception 'Invalid photo path';
        end if;
        insert into public.catch_log_photos (
            id, catch_log_id, photo_order, bucket, object_path,
            size_bytes, width, height, metadata
        ) values (
            (photo->>'id')::uuid, p_log_id, (photo->>'photo_order')::smallint,
            photo->>'bucket', photo->>'object_path', (photo->>'size_bytes')::integer,
            (photo->>'width')::integer, (photo->>'height')::integer, photo->'metadata'
        );
    end loop;
    insert into public.catch_log_submissions
        (user_id, submission_id, fingerprint, log_id, status)
        values (p_user_id, p_submission_id, p_fingerprint, p_log_id, 'pending');
    return jsonb_build_object('outcome', 'new', 'log_id', p_log_id);
end;
$$;

-- Mark one upload complete without exposing it before the parent is published.
create function public.mark_catch_photo_uploaded(p_user_id uuid, p_log_id uuid, p_photo_id uuid)
returns boolean language plpgsql set search_path = '' as $$
begin
    perform 1 from public.catch_logs
        where id = p_log_id and user_id = p_user_id and status = 'pending' for update;
    if not found then return false; end if;
    update public.catch_log_photos set status = 'uploaded'
        where id = p_photo_id and catch_log_id = p_log_id and status = 'pending';
    return found;
end;
$$;

-- Publish the parent, children and receipt atomically, guarded by a parent row lock.
create function public.publish_catch_submission(p_user_id uuid, p_log_id uuid)
returns jsonb language plpgsql set search_path = '' as $$
declare record public.catch_logs;
begin
    select * into record from public.catch_logs
        where id = p_log_id and user_id = p_user_id for update;
    if not found then return null; end if;
    if record.status = 'ready' then return to_jsonb(record); end if;
    if record.status <> 'pending' or exists (
        select 1 from public.catch_log_photos
        where catch_log_id = p_log_id and status <> 'uploaded'
    ) then return null; end if;
    update public.catch_log_photos set status = 'ready' where catch_log_id = p_log_id;
    update public.catch_logs set status = 'ready' where id = p_log_id returning * into record;
    update public.catch_log_submissions set status = 'ready'
        where user_id = p_user_id and log_id = p_log_id;
    return to_jsonb(record);
end;
$$;

-- Persist cancellation/delete intent before attempting any external Storage cleanup.
create function public.claim_catch_cleanup(
    p_user_id uuid, p_log_id uuid, p_delete boolean default false, p_stale boolean default false
) returns boolean language plpgsql set search_path = '' as $$
declare record public.catch_logs;
begin
    select * into record from public.catch_logs
        where id = p_log_id and user_id = p_user_id for update;
    if not found then return false; end if;
    if record.status in ('cleanup_pending', 'deleting') then return true; end if;
    if p_delete and record.status = 'ready' then
        update public.catch_logs set status = 'deleting', cleanup_after = now()
            where id = p_log_id;
        update public.catch_log_submissions set status = 'deleted'
            where user_id = p_user_id and log_id = p_log_id;
        return true;
    end if;
    if not p_delete and record.status = 'pending' then
        if p_stale and record.updated_at > now() - interval '1 hour' then return false; end if;
        -- Keep a durable path manifest through a second cleanup pass, allowing late uploads
        -- after network timeouts to finish before final removal. Not a distributed transaction.
        update public.catch_logs set status = 'cleanup_pending',
            cleanup_after = now() + interval '5 minutes' where id = p_log_id;
        update public.catch_log_submissions set status = 'failed'
            where user_id = p_user_id and log_id = p_log_id;
        return true;
    end if;
    return false;
end;
$$;

-- Remove the durable path manifest only after cleanup and the late-upload grace period.
create function public.finish_catch_cleanup(p_user_id uuid, p_log_id uuid)
returns boolean language plpgsql set search_path = '' as $$
declare record public.catch_logs;
begin
    select * into record from public.catch_logs
        where id = p_log_id and user_id = p_user_id for update;
    if not found or record.status not in ('cleanup_pending', 'deleting')
        or record.cleanup_after > now() then return false; end if;
    update public.catch_log_submissions
        set status = case when record.status = 'deleting' then 'deleted' else 'failed' end
        where user_id = p_user_id and log_id = p_log_id;
    delete from public.catch_logs where id = p_log_id;
    return true;
end;
$$;

-- Authorize and reserve a single-photo deletion in the same database operation.
create function public.begin_catch_photo_delete(p_user_id uuid, p_log_id uuid, p_photo_id uuid)
returns jsonb language plpgsql set search_path = '' as $$
declare photo public.catch_log_photos;
begin
    perform 1 from public.catch_logs
        where id = p_log_id and user_id = p_user_id and status = 'ready' for update;
    if not found then return null; end if;
    update public.catch_log_photos set status = 'deleting'
        where id = p_photo_id and catch_log_id = p_log_id and status in ('ready', 'deleting')
        returning * into photo;
    if not found then return null; end if;
    return to_jsonb(photo);
end;
$$;

-- Avoid default EXECUTE grants on newly created functions/tables.
revoke all on function public.begin_catch_submission(uuid, uuid, text, uuid, jsonb, jsonb),
    public.mark_catch_photo_uploaded(uuid, uuid, uuid),
    public.publish_catch_submission(uuid, uuid),
    public.claim_catch_cleanup(uuid, uuid, boolean, boolean),
    public.finish_catch_cleanup(uuid, uuid),
    public.begin_catch_photo_delete(uuid, uuid, uuid)
    from public, anon, authenticated;
grant execute on function public.begin_catch_submission(uuid, uuid, text, uuid, jsonb, jsonb),
    public.mark_catch_photo_uploaded(uuid, uuid, uuid),
    public.publish_catch_submission(uuid, uuid),
    public.claim_catch_cleanup(uuid, uuid, boolean, boolean),
    public.finish_catch_cleanup(uuid, uuid),
    public.begin_catch_photo_delete(uuid, uuid, uuid)
    to service_role;

-- Storage is optional in disposable PostgreSQL tests. Never create a public bucket.
do $$ begin
    if to_regclass('storage.buckets') is not null then
        execute $bucket$
            insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
            values ('catch-photos', 'catch-photos', false, 6291456, array['image/jpeg'])
            on conflict (id) do update set public = false,
                file_size_limit = 6291456, allowed_mime_types = array['image/jpeg']
        $bucket$;
    end if;
end $$;
