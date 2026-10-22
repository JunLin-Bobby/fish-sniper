-- 一筆紀錄代表一隻魚；照片與地圖位置留待後續 migration，不預先暴露 API。
create table public.catch_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.users(id) on delete cascade,
    species_name text not null
        check (char_length(btrim(species_name)) between 1 and 100),
    caught_at timestamptz not null check (isfinite(caught_at)),
    length_cm numeric check (length_cm > 0 and length_cm < 'Infinity'::numeric),
    weight_g numeric check (weight_g > 0 and weight_g < 'Infinity'::numeric),
    fishing_method text check (
        fishing_method in ('lure', 'front_strike', 'bottom', 'hand_pole', 'fly_fishing', 'other')
    ),
    notes text check (char_length(notes) <= 2000),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index catch_logs_user_caught_at_idx
    on public.catch_logs (user_id, caught_at desc, id desc);

-- 由資料庫維護修改時間，避免前端或個別 repository 路徑漏更新。
create function public.set_catch_log_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

revoke all on function public.set_catch_log_updated_at()
    from public, anon, authenticated, service_role;

create trigger catch_logs_set_updated_at
before update on public.catch_logs
for each row execute function public.set_catch_log_updated_at();

-- 不信任前端提供的 owner；FastAPI 驗證自家 JWT 後，每次查詢也必須限定 user_id。
alter table public.catch_logs enable row level security;
revoke all on table public.catch_logs from public, anon, authenticated;
grant select, insert, update, delete on table public.catch_logs to service_role;

comment on table public.catch_logs is
    'Private single-fish catch logs. Backend-only Data API access; no public sharing.';
