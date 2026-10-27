-- Run against a disposable PostgreSQL database after all migrations; fixtures roll back.
begin;
insert into public.users (id, google_sub, email) values
    ('10000000-0000-0000-0000-000000000001', 'photo-sql-a', 'photo-a@example.test'),
    ('10000000-0000-0000-0000-000000000002', 'photo-sql-b', 'photo-b@example.test');

-- Force an error AFTER child photos were updated to demonstrate transaction rollback.
create function pg_temp.reject_test_publish() returns trigger language plpgsql as $$
begin
    if new.status = 'ready' and new.species_name = 'force-publish-failure' then
        raise check_violation;
    end if;
    return new;
end $$;
create trigger reject_test_publish after update on public.catch_logs
    for each row execute function pg_temp.reject_test_publish();

set local role service_role;
do $$
<<test_case>>
declare
    owner_id uuid := '10000000-0000-0000-0000-000000000001';
    other_id uuid := '10000000-0000-0000-0000-000000000002';
    log_id uuid := '20000000-0000-0000-0000-000000000001';
    photo_id uuid := '30000000-0000-0000-0000-000000000001';
    submission_id uuid := '40000000-0000-0000-0000-000000000001';
    payload jsonb := '{"species_name":"Bass","caught_at":"2026-10-22T08:00:00Z"}';
    manifest jsonb;
    result jsonb;
begin
    if has_table_privilege('anon', 'public.catch_log_photos', 'select')
        or has_table_privilege('authenticated', 'public.catch_log_submissions', 'select')
        or has_function_privilege('authenticated',
            'public.publish_catch_submission(uuid,uuid)', 'execute') then
        raise exception 'Private grants leaked';
    end if;
    manifest := jsonb_build_array(jsonb_build_object(
        'id', photo_id, 'photo_order', 1, 'bucket', 'catch-photos',
        'object_path', owner_id::text || '/' || log_id::text || '/' || photo_id::text || '.jpg',
        'size_bytes', 1000, 'width', 80, 'height', 40, 'metadata', '{}'::jsonb
    ));
    result := public.begin_catch_submission(
        owner_id, submission_id, repeat('a', 64), log_id, payload, manifest);
    if result->>'outcome' <> 'new' then raise exception 'Draft not created'; end if;
    if (select status from public.catch_logs where id = log_id) <> 'pending' then
        raise exception 'Draft visible before publish';
    end if;
    if public.publish_catch_submission(owner_id, log_id) is not null then
        raise exception 'Published without uploaded photos';
    end if;
    if public.mark_catch_photo_uploaded(other_id, log_id, photo_id) then
        raise exception 'Other owner can mark uploads';
    end if;
    if not public.mark_catch_photo_uploaded(owner_id, log_id, photo_id) then
        raise exception 'Upload mark failed';
    end if;
    update public.catch_logs set species_name = 'force-publish-failure' where id = log_id;
    begin
        perform public.publish_catch_submission(owner_id, log_id);
        raise exception 'Forced publish failure did not execute';
    exception when check_violation then null;
    end;
    if (select status from public.catch_logs where id = log_id) <> 'pending'
        or (select status from public.catch_log_photos where id = photo_id) <> 'uploaded'
        or (select s.status from public.catch_log_submissions s
            where s.user_id = owner_id and s.submission_id = test_case.submission_id)
            <> 'pending' then
        raise exception 'Partial publication was not rolled back';
    end if;
    update public.catch_logs set species_name = 'Bass' where id = log_id;
    result := public.publish_catch_submission(owner_id, log_id);
    if result->>'status' <> 'ready'
        or (select status from public.catch_log_photos where id = photo_id) <> 'ready' then
        raise exception 'Publication not atomic';
    end if;
    result := public.begin_catch_submission(
        owner_id, submission_id, repeat('a', 64), gen_random_uuid(), payload, manifest);
    if result->>'outcome' <> 'ready' or (result->>'log_id')::uuid <> log_id then
        raise exception 'Idempotency failed';
    end if;
    result := public.begin_catch_submission(
        owner_id, submission_id, repeat('b', 64), gen_random_uuid(), payload, manifest);
    if result->>'outcome' <> 'conflict' then raise exception 'Payload reuse accepted'; end if;
    if public.claim_catch_cleanup(owner_id, log_id) then
        raise exception 'Compensation would delete a committed catch';
    end if;
    if public.claim_catch_cleanup(other_id, log_id, true) then
        raise exception 'Another owner can delete';
    end if;
    if not public.claim_catch_cleanup(owner_id, log_id, true)
        or not public.finish_catch_cleanup(owner_id, log_id) then
        raise exception 'Ready catch deletion failed';
    end if;
    if exists (select from public.catch_log_photos where catch_log_id = log_id) then
        raise exception 'Photo cascade failed';
    end if;
    result := public.begin_catch_submission(
        owner_id, submission_id, repeat('a', 64), gen_random_uuid(), payload, manifest);
    if result->>'outcome' <> 'deleted' then raise exception 'Deleted submission recreated'; end if;

    submission_id := gen_random_uuid();
    result := public.begin_catch_submission(
        owner_id, submission_id, repeat('c', 64), log_id, payload, manifest);
    if public.claim_catch_cleanup(owner_id, log_id, false, true) then
        raise exception 'Recovery stole a fresh active upload';
    end if;
    if not public.claim_catch_cleanup(owner_id, log_id) then
        raise exception 'Could not cancel draft';
    end if;
    if public.publish_catch_submission(owner_id, log_id) is not null
        or public.mark_catch_photo_uploaded(owner_id, log_id, photo_id) then
        raise exception 'Cancelled draft still accepts writes';
    end if;
    if public.finish_catch_cleanup(owner_id, log_id) then
        raise exception 'Path manifest removed before late-upload grace period';
    end if;
    update public.catch_logs set cleanup_after = now() - interval '1 minute' where id = log_id;
    if not public.finish_catch_cleanup(owner_id, log_id) then
        raise exception 'Recovery cannot finalize cleanup';
    end if;

    -- A failed reservation must roll back the catch, manifest and idempotency receipt.
    begin
        perform public.begin_catch_submission(
            owner_id, gen_random_uuid(), repeat('d', 64), log_id, payload, manifest || manifest);
        raise exception 'Duplicate slot accepted';
    exception when unique_violation then null;
    end;
    if exists (select from public.catch_logs where id = log_id) then
        raise exception 'Failed transaction left a draft';
    end if;
end $$;
reset role;
rollback;
