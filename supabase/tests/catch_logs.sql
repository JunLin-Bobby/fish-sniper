-- 在測試資料庫套用 migrations 後，以 psql -v ON_ERROR_STOP=1 執行；資料最後全部 rollback。
begin;

insert into public.users (id, google_sub, email)
values ('b0000000-0000-0000-0000-000000000001', 'catch-sql-test', 'catch-test@example.invalid');

insert into public.catch_logs (id, user_id, species_name, caught_at, fishing_method)
values (
    'c0000000-0000-0000-0000-000000000001',
    'b0000000-0000-0000-0000-000000000001', 'Bass', '2026-10-20T00:00:00Z', 'lure'
);

-- 驗證 grants 與 RLS，即使建立表的環境沒有 Supabase 自動 default grants 也能使用。
do $$
begin
    if exists (
        select 1 from unnest(array['select', 'insert', 'update', 'delete']) as p(privilege)
        where not has_table_privilege('service_role', 'public.catch_logs', p.privilege)
    ) then
        raise exception 'Missing backend grants';
    end if;
    if has_table_privilege('anon', 'public.catch_logs', 'select')
       or has_table_privilege('authenticated', 'public.catch_logs', 'select') then
        raise exception 'Private table is exposed to client roles';
    end if;
    if not (select relrowsecurity from pg_class where oid = 'public.catch_logs'::regclass) then
        raise exception 'RLS is not enabled';
    end if;
end;
$$;

-- 驗證資料庫本身拒絕空魚種、非正數、NaN、Infinity、未知釣法及不存在的 user。
do $$
begin
    begin
        update public.catch_logs set species_name = ' ';
        raise exception 'Blank species accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set length_cm = 0;
        raise exception 'Zero length accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set weight_g = -1;
        raise exception 'Negative weight accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set weight_g = 'NaN'::numeric;
        raise exception 'NaN weight accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set length_cm = 'Infinity'::numeric;
        raise exception 'Infinite length accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set caught_at = 'infinity'::timestamptz;
        raise exception 'Infinite time accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set fishing_method = 'invalid';
        raise exception 'Unknown method accepted';
    exception when check_violation then null;
    end;
    begin
        update public.catch_logs set user_id = 'b0000000-0000-0000-0000-000000000099';
        raise exception 'Invalid user accepted';
    exception when foreign_key_violation then null;
    end;
end;
$$;

-- 驗證 backend role 可使用明確授權的 CRUD，且 trigger 自動維護 updated_at。
set local role service_role;
insert into public.catch_logs (id, user_id, species_name, caught_at)
values (
    'c0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000001', 'Trout', '2026-10-19T00:00:00Z'
);
update public.catch_logs
set length_cm = 30, weight_g = null, notes = null, updated_at = '2000-01-01T00:00:00Z'
where id = 'c0000000-0000-0000-0000-000000000002';
do $$
begin
    if not exists (
        select 1 from public.catch_logs
        where id = 'c0000000-0000-0000-0000-000000000002' and updated_at = now()
    ) then
        raise exception 'Backend CRUD or timestamp trigger failed';
    end if;
end;
$$;
delete from public.catch_logs where id = 'c0000000-0000-0000-0000-000000000002';
reset role;

rollback;
