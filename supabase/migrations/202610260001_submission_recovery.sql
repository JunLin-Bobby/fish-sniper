-- Register before reading multipart; the database, not browser timers, fences late publishers.
alter table public.catch_log_submissions alter column fingerprint drop not null;
alter table public.catch_log_submissions add column attempt_id uuid;
alter table public.catch_log_submissions add column deadline timestamptz not null
    default (now() + interval '45 seconds');
create index catch_submissions_expiry_idx on public.catch_log_submissions (deadline)
    where status = 'pending';

-- Each HTTP attempt gets a server-only token; duplicate requests cannot take over its lease.
create function public.register_catch_submission(
    p_user_id uuid, p_submission_id uuid, p_attempt_id uuid, p_seconds integer
) returns jsonb language plpgsql set search_path = '' as $$
declare receipt public.catch_log_submissions;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || p_submission_id::text, 0));
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and submission_id = p_submission_id for update;
    if found then
        return jsonb_build_object('outcome', receipt.status, 'log_id', receipt.log_id);
    end if;
    insert into public.catch_log_submissions
        (user_id, submission_id, status, attempt_id, deadline)
        values (p_user_id, p_submission_id, 'pending', p_attempt_id,
            clock_timestamp() + make_interval(secs => least(greatest(p_seconds, 1), 120)));
    return jsonb_build_object('outcome', 'new');
end;
$$;

-- Start a separate processing budget only after the complete request has arrived.
create function public.start_catch_processing(
    p_user_id uuid, p_submission_id uuid, p_attempt_id uuid, p_seconds integer
) returns boolean language plpgsql set search_path = '' as $$
begin
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || p_submission_id::text, 0));
    update public.catch_log_submissions
        set deadline = clock_timestamp() + make_interval(secs => least(greatest(p_seconds, 1), 120))
        where user_id = p_user_id and submission_id = p_submission_id
        and attempt_id = p_attempt_id and status = 'pending' and fingerprint is null
        and deadline > clock_timestamp();
    return found;
end;
$$;

-- Share the advisory-lock ordering with publication and recovery to avoid deadlocks.
create or replace function public.claim_catch_cleanup(
    p_user_id uuid, p_log_id uuid, p_delete boolean default false, p_stale boolean default false
) returns boolean language plpgsql set search_path = '' as $$
declare record public.catch_logs; receipt public.catch_log_submissions;
begin
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and log_id = p_log_id;
    if found then
        perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || receipt.submission_id::text, 0));
    end if;
    select * into record from public.catch_logs
        where id = p_log_id and user_id = p_user_id for update;
    if not found then return false; end if;
    if record.status in ('cleanup_pending', 'deleting') then return true; end if;
    if p_delete and record.status = 'ready' then
        update public.catch_logs set status = 'deleting', cleanup_after = now() where id = p_log_id;
        update public.catch_log_submissions set status = 'deleted'
            where user_id = p_user_id and log_id = p_log_id;
        return true;
    end if;
    if not p_delete and record.status = 'pending' then
        if p_stale and receipt.deadline > clock_timestamp() then return false; end if;
        if p_stale and receipt.submission_id is null
            and record.updated_at > now() - interval '1 hour' then return false; end if;
        update public.catch_logs set status = 'cleanup_pending',
            cleanup_after = now() + interval '5 minutes' where id = p_log_id;
        update public.catch_log_submissions set status = 'failed'
            where user_id = p_user_id and log_id = p_log_id;
        return true;
    end if;
    return false;
end;
$$;

-- Missing IDs become terminal tombstones, blocking uploads that arrive after recovery.
create function public.resolve_catch_submission(p_user_id uuid, p_submission_id uuid)
returns jsonb language plpgsql set search_path = '' as $$
declare receipt public.catch_log_submissions;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || p_submission_id::text, 0));
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and submission_id = p_submission_id for update;
    if not found then
        insert into public.catch_log_submissions (user_id, submission_id, status, deadline)
            values (p_user_id, p_submission_id, 'failed', clock_timestamp());
        return jsonb_build_object('status', 'failed', 'log_id', null, 'retry_after_ms', 0);
    end if;
    if receipt.status = 'pending' and receipt.deadline <= clock_timestamp() then
        if receipt.log_id is not null then
            perform public.claim_catch_cleanup(p_user_id, receipt.log_id);
        end if;
        update public.catch_log_submissions set status = 'failed'
            where user_id = p_user_id and submission_id = p_submission_id;
        receipt.status := 'failed';
    end if;
    return jsonb_build_object('status', receipt.status, 'log_id', receipt.log_id,
        'retry_after_ms', case when receipt.status = 'pending' then
            greatest(250, ceil(extract(epoch from (receipt.deadline - clock_timestamp())) * 1000)::integer + 100)
            else 0 end);
end;
$$;

-- Only the owning HTTP attempt may fail its reservation; committed success always wins.
create function public.fail_catch_submission(p_user_id uuid, p_submission_id uuid, p_attempt_id uuid)
returns jsonb language plpgsql set search_path = '' as $$
declare receipt public.catch_log_submissions;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || p_submission_id::text, 0));
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and submission_id = p_submission_id for update;
    if found and receipt.status = 'pending' and receipt.attempt_id = p_attempt_id then
        if receipt.log_id is not null then
            perform public.claim_catch_cleanup(p_user_id, receipt.log_id);
        end if;
        update public.catch_log_submissions set status = 'failed'
            where user_id = p_user_id and submission_id = p_submission_id;
    end if;
    return public.resolve_catch_submission(p_user_id, p_submission_id);
end;
$$;

-- Keep the six-argument call compatible for older server-only callers during deployment.
drop function public.begin_catch_submission(uuid, uuid, text, uuid, jsonb, jsonb);
create function public.begin_catch_submission(
    p_user_id uuid, p_submission_id uuid, p_fingerprint text,
    p_log_id uuid, p_values jsonb, p_photos jsonb, p_attempt_id uuid default null
) returns jsonb language plpgsql set search_path = '' as $$
declare receipt public.catch_log_submissions; photo jsonb;
begin
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || p_submission_id::text, 0));
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and submission_id = p_submission_id for update;
    if found then
        if receipt.status <> 'pending' or receipt.fingerprint is not null then
            if receipt.fingerprint is not null and receipt.fingerprint <> p_fingerprint then
                return jsonb_build_object('outcome', 'conflict');
            end if;
            return jsonb_build_object('outcome', receipt.status, 'log_id', receipt.log_id);
        end if;
        if receipt.attempt_id is distinct from p_attempt_id or receipt.deadline <= clock_timestamp() then
            return jsonb_build_object('outcome', 'pending');
        end if;
    else
        if p_attempt_id is not null then return jsonb_build_object('outcome', 'failed'); end if;
        insert into public.catch_log_submissions
            (user_id, submission_id, status, deadline) values
            (p_user_id, p_submission_id, 'pending', clock_timestamp() + interval '30 seconds');
    end if;
    if jsonb_typeof(p_photos) <> 'array' or jsonb_array_length(p_photos) > 2 then
        raise exception 'Invalid photo count';
    end if;
    insert into public.catch_logs (
        id, user_id, species_name, caught_at, length_cm, weight_g, fishing_method, notes, status
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
            id, catch_log_id, photo_order, bucket, object_path, size_bytes, width, height, metadata
        ) values (
            (photo->>'id')::uuid, p_log_id, (photo->>'photo_order')::smallint,
            photo->>'bucket', photo->>'object_path', (photo->>'size_bytes')::integer,
            (photo->>'width')::integer, (photo->>'height')::integer, photo->'metadata'
        );
    end loop;
    update public.catch_log_submissions set fingerprint = p_fingerprint, log_id = p_log_id
        where user_id = p_user_id and submission_id = p_submission_id;
    return jsonb_build_object('outcome', 'new', 'log_id', p_log_id);
end;
$$;

-- No deadline-expired/failed operation may publish, even if Python cancellation arrives late.
create or replace function public.publish_catch_submission(p_user_id uuid, p_log_id uuid)
returns jsonb language plpgsql set search_path = '' as $$
declare record public.catch_logs; receipt public.catch_log_submissions;
begin
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and log_id = p_log_id;
    if not found then return null; end if;
    perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || receipt.submission_id::text, 0));
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and submission_id = receipt.submission_id for update;
    select * into record from public.catch_logs
        where id = p_log_id and user_id = p_user_id for update;
    if not found then return null; end if;
    if record.status = 'ready' then return to_jsonb(record); end if;
    if receipt.status <> 'pending' or receipt.deadline <= clock_timestamp() then
        perform public.resolve_catch_submission(p_user_id, receipt.submission_id);
        return null;
    end if;
    if record.status <> 'pending' or exists (
        select 1 from public.catch_log_photos where catch_log_id = p_log_id and status <> 'uploaded'
    ) then return null; end if;
    update public.catch_log_photos set status = 'ready' where catch_log_id = p_log_id;
    update public.catch_logs set status = 'ready' where id = p_log_id returning * into record;
    update public.catch_log_submissions set status = 'ready'
        where user_id = p_user_id and log_id = p_log_id;
    return to_jsonb(record);
end;
$$;

-- Recover reservations without a catch row too; process death must not leave them pending forever.
-- Cleanup must use the same lock ordering, including its final metadata deletion.
create or replace function public.finish_catch_cleanup(p_user_id uuid, p_log_id uuid)
returns boolean language plpgsql set search_path = '' as $$
declare record public.catch_logs; receipt public.catch_log_submissions;
begin
    select * into receipt from public.catch_log_submissions
        where user_id = p_user_id and log_id = p_log_id;
    if found then
        perform pg_advisory_xact_lock(hashtextextended(p_user_id::text || receipt.submission_id::text, 0));
    end if;
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

-- Expire reservations without requiring any client query.
create function public.expire_catch_submissions() returns integer
language plpgsql set search_path = '' as $$
declare entry record; total integer := 0;
begin
    for entry in select user_id, submission_id from public.catch_log_submissions
        where status = 'pending' and deadline <= clock_timestamp()
        order by user_id, submission_id limit 100 loop
        perform public.resolve_catch_submission(entry.user_id, entry.submission_id);
        total := total + 1;
    end loop;
    return total;
end;
$$;

-- Explicit function grants: API roles never gain access to server-only state transitions.
revoke all on function public.register_catch_submission(uuid,uuid,uuid,integer),
    public.start_catch_processing(uuid,uuid,uuid,integer),
    public.resolve_catch_submission(uuid,uuid), public.fail_catch_submission(uuid,uuid,uuid),
    public.begin_catch_submission(uuid,uuid,text,uuid,jsonb,jsonb,uuid),
    public.expire_catch_submissions() from public, anon, authenticated;
grant execute on function public.register_catch_submission(uuid,uuid,uuid,integer),
    public.start_catch_processing(uuid,uuid,uuid,integer),
    public.resolve_catch_submission(uuid,uuid), public.fail_catch_submission(uuid,uuid,uuid),
    public.begin_catch_submission(uuid,uuid,text,uuid,jsonb,jsonb,uuid),
    public.expire_catch_submissions() to service_role;
