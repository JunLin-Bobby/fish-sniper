-- Run after all migrations in an isolated database; all test data rolls back.
begin;
insert into public.users (id, google_sub, email) values
    ('11000000-0000-0000-0000-000000000001', 'recovery-sql-a', 'recovery@example.test');
set local role service_role;
do $$
declare
    owner_id uuid := '11000000-0000-0000-0000-000000000001';
    sid uuid := gen_random_uuid(); aid uuid := gen_random_uuid(); lid uuid := gen_random_uuid();
    result jsonb;
    payload jsonb := '{"species_name":"Bass","caught_at":"2026-10-26T08:00:00Z"}';
begin
    if has_function_privilege('authenticated', 'public.resolve_catch_submission(uuid,uuid)', 'execute')
        or has_function_privilege('anon', 'public.register_catch_submission(uuid,uuid,uuid,integer)', 'execute') then
        raise exception 'Server-only transitions exposed';
    end if;
    result := public.resolve_catch_submission(owner_id, sid);
    if result->>'status' <> 'failed' then raise exception 'Missing ID not fenced'; end if;
    result := public.register_catch_submission(owner_id, sid, aid, 45);
    if result->>'outcome' <> 'failed' then raise exception 'Late request revived failed ID'; end if;

    sid := gen_random_uuid();
    result := public.register_catch_submission(owner_id, sid, aid, 45);
    if result->>'outcome' <> 'new' then raise exception 'Registration failed'; end if;
    if public.start_catch_processing(owner_id, sid, gen_random_uuid(), 30) then
        raise exception 'Another attempt stole reservation';
    end if;
    result := public.fail_catch_submission(owner_id, sid, gen_random_uuid());
    if result->>'status' <> 'pending' then raise exception 'Another attempt cancelled work'; end if;
    if not public.start_catch_processing(owner_id, sid, aid, 30) then
        raise exception 'Owner cannot process';
    end if;
    result := public.begin_catch_submission(owner_id,sid,repeat('a',64),lid,payload,'[]',aid);
    if result->>'outcome' <> 'new' then raise exception 'Reservation not attached'; end if;
    update public.catch_log_submissions set deadline = clock_timestamp() - interval '1 second'
        where user_id = owner_id and submission_id = sid;
    if public.publish_catch_submission(owner_id,lid) is not null then
        raise exception 'Expired work published';
    end if;
    result := public.resolve_catch_submission(owner_id,sid);
    if result->>'status' <> 'failed' then raise exception 'Expired work not failed'; end if;
    if (select status from public.catch_logs where id = lid) <> 'cleanup_pending' then
        raise exception 'Expired manifest not retained';
    end if;

    sid := gen_random_uuid(); lid := gen_random_uuid();
    perform public.register_catch_submission(owner_id,sid,aid,45);
    perform public.start_catch_processing(owner_id,sid,aid,30);
    perform public.begin_catch_submission(owner_id,sid,repeat('a',64),lid,payload,'[]',aid);
    result := public.publish_catch_submission(owner_id,lid);
    if result->>'status' <> 'ready' then raise exception 'Publication failed'; end if;
    result := public.fail_catch_submission(owner_id,sid,aid);
    if result->>'status' <> 'ready' or public.claim_catch_cleanup(owner_id,lid) then
        raise exception 'Lost success response caused compensation';
    end if;

    sid := gen_random_uuid();
    perform public.register_catch_submission(owner_id,sid,aid,45);
    update public.catch_log_submissions set deadline = clock_timestamp() - interval '1 second'
        where user_id = owner_id and submission_id = sid;
    perform public.expire_catch_submissions();
    result := public.resolve_catch_submission(owner_id,sid);
    if result->>'status' <> 'failed' then raise exception 'Orphan reservation stuck'; end if;
end $$;
reset role;
rollback;
