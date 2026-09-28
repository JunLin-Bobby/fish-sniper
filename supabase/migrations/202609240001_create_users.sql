create extension if not exists pgcrypto;

create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    google_sub text,
    email text not null,
    display_name text,
    avatar_url text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_login_at timestamptz not null default now()
);

-- 相容可能由舊版 auth 建立、但尚未具有 Google identity 欄位的 users table。
alter table public.users add column if not exists google_sub text;
alter table public.users add column if not exists display_name text;
alter table public.users add column if not exists avatar_url text;
alter table public.users add column if not exists created_at timestamptz not null default now();
alter table public.users add column if not exists updated_at timestamptz not null default now();
alter table public.users add column if not exists last_login_at timestamptz not null default now();

create unique index if not exists users_google_sub_unique
    on public.users (google_sub);

alter table public.users enable row level security;

-- FishSniper 目前只允許 FastAPI backend 使用 elevated server credential 存取此表。
revoke all on table public.users from anon, authenticated;
grant select, insert, update on table public.users to service_role;
