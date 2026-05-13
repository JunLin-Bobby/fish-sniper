-- =============================================================================
-- FishSniper — FULL DATABASE RESET (schema + RPC + indexes + Data API GRANTs)
-- =============================================================================
-- 用途：FishSniper 的 **唯一** DB source of truth（self-contained，無需搭配其他 SQL 檔）。
--       在 **任何** 舊 schema 狀態下，把 Supabase / Postgres 裡 FishSniper 相關物件
--       全部拆掉後，依本檔重建。適合：
--         * 本機 / staging 一鍵洗白
--         * 從早期只有半套 `fishing_logs` 的 DB 升級失敗時，直接重來
--         * CI 或新同事 clone 專案後第一次對準 DB
--         * 新開的 Supabase project（2026-05-30 起新預設）一次到位
--
-- 警告：**會刪除** `users`、`otp_codes`、`user_preferences`、`fishing_logs` 內
--       所有資料（含 dev seed）。不要在 production 共用庫上未備份就執行。
--
-- 不包含：`DROP EXTENSION vector`（同一 instance 若還有其他專案用 pgvector 會誤傷）。
--       本腳本只 `CREATE EXTENSION IF NOT EXISTS vector`。
--
-- Data API GRANT（PHASE 4b / 5b）：Supabase 自 2026-05-30 起，新 project 的 `public.*`
--       不再預設暴露給 PostgREST / supabase-js；2026-10-30 起套用至所有既有 project。
--       本檔已 explicit `GRANT ... TO service_role`，backend（用 SUPABASE_SERVICE_ROLE_KEY）
--       仍可透過 supabase-py 正常讀寫與呼叫 RPC。
--
-- 執行方式：Supabase Dashboard → SQL Editor → 整檔貼上 → Run 一次即可。
-- 執行後（可選）：`scripts/seed_p3.sql` 插入 dev 使用者 + 範例日誌（需先有本腳本 schema）。
-- =============================================================================

-- ---------------------------------------------------------------------------
-- PHASE 1 — TEARDOWN（順序：先拆依賴 fishing_logs 的函式，再拆表）
-- ---------------------------------------------------------------------------

-- RPC（簽名須與下方 CREATE FUNCTION 完全一致，否則 DROP 不生效）
DROP FUNCTION IF EXISTS public.fish_sniper_update_log_with_embedding(
  uuid, uuid, date, text, text, text, double precision, text, text, text, integer,
  double precision, double precision, double precision, double precision, integer,
  text, text, text, smallint, timestamptz
) CASCADE;

DROP FUNCTION IF EXISTS public.fish_sniper_insert_log_with_embedding(
  uuid, date, text, text, text, double precision, text, text, text, integer,
  double precision, double precision, double precision, double precision, integer,
  text, text, text, smallint, timestamptz
) CASCADE;

DROP FUNCTION IF EXISTS public.fish_sniper_find_similar_fishing_log(
  uuid, text, text, integer
) CASCADE;

DROP TRIGGER IF EXISTS trg_fishing_logs_set_updated_at ON public.fishing_logs;
DROP FUNCTION IF EXISTS public.fish_sniper_set_fishing_logs_updated_at() CASCADE;

DROP TABLE IF EXISTS public.fishing_logs CASCADE;

DROP TABLE IF EXISTS public.user_preferences CASCADE;
DROP TABLE IF EXISTS public.otp_codes CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

-- ---------------------------------------------------------------------------
-- PHASE 2 — EXTENSION
-- ---------------------------------------------------------------------------

CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- PHASE 3 — P1 核心表（users / otp_codes / user_preferences；CREATE 非 IF）
-- ---------------------------------------------------------------------------

CREATE TABLE public.users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.otp_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_otp_codes_email_created_at
  ON public.otp_codes (email, created_at DESC);

CREATE TABLE public.user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  region TEXT NOT NULL,
  onboarding_completed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT user_preferences_user_id_unique UNIQUE (user_id)
);

-- ---------------------------------------------------------------------------
-- PHASE 4 — fishing_logs（P3 欄位 + P4 Part 1 向量欄位；**無** pinecone_synced）
-- ---------------------------------------------------------------------------

CREATE TABLE public.fishing_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  fishing_location TEXT NOT NULL,
  fishing_scene TEXT NOT NULL,
  target_species TEXT NOT NULL
    CHECK (target_species IN ('Largemouth Bass', 'Smallmouth Bass')),
  water_depth_m DOUBLE PRECISION NOT NULL,
  lure_type TEXT NOT NULL,
  lure_color TEXT NOT NULL,
  retrieve_speed TEXT NOT NULL,
  caught_count INTEGER NOT NULL CHECK (caught_count >= 0),
  weight_lb DOUBLE PRECISION NULL,
  length_cm DOUBLE PRECISION NULL,
  temperature_c DOUBLE PRECISION NOT NULL,
  wind_speed_ms DOUBLE PRECISION NOT NULL,
  pressure_hpa INTEGER NOT NULL,
  condition_code TEXT NOT NULL,
  notes TEXT NOT NULL DEFAULT '',
  embedding vector(1536) NULL,
  embedding_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (embedding_status IN ('pending', 'done', 'failed')),
  embedding_text_version SMALLINT NOT NULL DEFAULT 1,
  embedding_attempt_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (water_depth_m >= 0)
);

CREATE INDEX idx_fishing_logs_user_id_date_desc
  ON public.fishing_logs (user_id, date DESC);

CREATE INDEX idx_fishing_logs_user_id_updated_at_desc
  ON public.fishing_logs (user_id, updated_at DESC);

CREATE INDEX idx_fishing_logs_pending_embeddings
  ON public.fishing_logs (created_at)
  WHERE embedding_status = 'pending';

CREATE OR REPLACE FUNCTION public.fish_sniper_set_fishing_logs_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_fishing_logs_set_updated_at
  BEFORE UPDATE ON public.fishing_logs
  FOR EACH ROW
  EXECUTE PROCEDURE public.fish_sniper_set_fishing_logs_updated_at();

ALTER TABLE public.fishing_logs ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- PHASE 4b — Data API GRANTS（service_role only）
-- ---------------------------------------------------------------------------
-- 背景：Supabase 自 2026-05-30 起，新 project 的 `public.*` 表不再預設暴露給
-- PostgREST / supabase-js；2026-10-30 起套用至所有既有 project。少了 GRANT，
-- backend 透過 supabase-py 的呼叫會收到 `42501 permission denied`。
--
-- 為何只授權 `service_role`：
--   * Backend 是唯一的 Data API caller（FastAPI → supabase-py，使用 SERVICE_ROLE_KEY）。
--   * `service_role` 預設 bypass RLS；`fishing_logs` 已 ENABLE RLS 維持 defense-in-depth。
--   * Frontend 不直接連 Supabase，因此暫不需 `anon` / `authenticated` GRANT。
--   * 將來若新增 frontend 直連場景，再補對應角色 + RLS POLICY。

GRANT SELECT, INSERT, UPDATE, DELETE ON public.users            TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.otp_codes        TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_preferences TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.fishing_logs     TO service_role;

-- ---------------------------------------------------------------------------
-- PHASE 5 — P4 RPC（insert/update with embedding + similarity search；供 PostgREST client.rpc）
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.fish_sniper_insert_log_with_embedding(
  p_user_id uuid,
  p_date date,
  p_fishing_location text,
  p_fishing_scene text,
  p_target_species text,
  p_water_depth_m double precision,
  p_lure_type text,
  p_lure_color text,
  p_retrieve_speed text,
  p_caught_count integer,
  p_weight_lb double precision,
  p_length_cm double precision,
  p_temperature_c double precision,
  p_wind_speed_ms double precision,
  p_pressure_hpa integer,
  p_condition_code text,
  p_notes text,
  p_embedding text,
  p_embedding_text_version smallint,
  p_reference_time_utc timestamptz
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_status text := CASE WHEN p_embedding IS NULL THEN 'pending' ELSE 'done' END;
  v_row public.fishing_logs%ROWTYPE;
BEGIN
  INSERT INTO public.fishing_logs (
    user_id, date, fishing_location, fishing_scene, target_species,
    water_depth_m, lure_type, lure_color, retrieve_speed, caught_count,
    weight_lb, length_cm, temperature_c, wind_speed_ms, pressure_hpa,
    condition_code, notes,
    embedding, embedding_status, embedding_text_version,
    created_at, updated_at
  ) VALUES (
    p_user_id, p_date, p_fishing_location, p_fishing_scene, p_target_species,
    p_water_depth_m, p_lure_type, p_lure_color, p_retrieve_speed, p_caught_count,
    p_weight_lb, p_length_cm, p_temperature_c, p_wind_speed_ms, p_pressure_hpa,
    p_condition_code, p_notes,
    CASE WHEN p_embedding IS NULL THEN NULL ELSE p_embedding::vector END,
    v_status,
    p_embedding_text_version,
    p_reference_time_utc, p_reference_time_utc
  ) RETURNING * INTO v_row;

  RETURN to_jsonb(v_row) - 'embedding';
END;
$$;

CREATE OR REPLACE FUNCTION public.fish_sniper_update_log_with_embedding(
  p_log_id uuid,
  p_user_id uuid,
  p_date date,
  p_fishing_location text,
  p_fishing_scene text,
  p_target_species text,
  p_water_depth_m double precision,
  p_lure_type text,
  p_lure_color text,
  p_retrieve_speed text,
  p_caught_count integer,
  p_weight_lb double precision,
  p_length_cm double precision,
  p_temperature_c double precision,
  p_wind_speed_ms double precision,
  p_pressure_hpa integer,
  p_condition_code text,
  p_notes text,
  p_embedding text,
  p_embedding_text_version smallint,
  p_reference_time_utc timestamptz
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_status text := CASE WHEN p_embedding IS NULL THEN 'pending' ELSE 'done' END;
  v_row public.fishing_logs%ROWTYPE;
BEGIN
  UPDATE public.fishing_logs
     SET date                   = p_date,
         fishing_location       = p_fishing_location,
         fishing_scene          = p_fishing_scene,
         target_species         = p_target_species,
         water_depth_m          = p_water_depth_m,
         lure_type              = p_lure_type,
         lure_color             = p_lure_color,
         retrieve_speed         = p_retrieve_speed,
         caught_count           = p_caught_count,
         weight_lb              = p_weight_lb,
         length_cm              = p_length_cm,
         temperature_c          = p_temperature_c,
         wind_speed_ms          = p_wind_speed_ms,
         pressure_hpa           = p_pressure_hpa,
         condition_code         = p_condition_code,
         notes                  = p_notes,
         embedding              = CASE WHEN p_embedding IS NULL THEN NULL ELSE p_embedding::vector END,
         embedding_status       = v_status,
         embedding_text_version = p_embedding_text_version,
         updated_at             = p_reference_time_utc
   WHERE id      = p_log_id
     AND user_id = p_user_id
   RETURNING * INTO v_row;

  IF NOT FOUND THEN
    RETURN NULL;
  END IF;

  RETURN to_jsonb(v_row) - 'embedding';
END;
$$;

-- P4 Part 2 — similarity search RPC（user_id + target_species filter，cosine ASC + id ASC tie-break）
CREATE OR REPLACE FUNCTION public.fish_sniper_find_similar_fishing_log(
  p_user_id         uuid,
  p_target_species  text,
  p_query_embedding text,
  p_limit           integer
) RETURNS TABLE (log_jsonb jsonb, cosine_distance double precision)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_query_vec vector;
BEGIN
  v_query_vec := p_query_embedding::vector;
  RETURN QUERY
    SELECT
      to_jsonb(fl.*) - 'embedding'                              AS log_jsonb,
      (fl.embedding <=> v_query_vec)::double precision          AS cosine_distance
    FROM public.fishing_logs fl
   WHERE fl.user_id          = p_user_id
     AND fl.target_species   = p_target_species
     AND fl.embedding_status = 'done'
     AND fl.embedding IS NOT NULL
   ORDER BY fl.embedding <=> v_query_vec ASC, fl.id ASC
   LIMIT p_limit;
END;
$$;

-- ---------------------------------------------------------------------------
-- PHASE 5b — RPC EXECUTE GRANTS（service_role only）
-- ---------------------------------------------------------------------------
-- supabase-py 的 `client.rpc(...)` 走 PostgREST；雖然這三支 RPC 是 SECURITY DEFINER，
-- PostgREST 仍會先檢查 caller role 對 function 的 EXECUTE 權限。簽名必須與上方
-- CREATE FUNCTION 的參數列完全一致（順序與型別）。

GRANT EXECUTE ON FUNCTION public.fish_sniper_insert_log_with_embedding(
  uuid, date, text, text, text, double precision, text, text, text, integer,
  double precision, double precision, double precision, double precision, integer,
  text, text, text, smallint, timestamptz
) TO service_role;

GRANT EXECUTE ON FUNCTION public.fish_sniper_update_log_with_embedding(
  uuid, uuid, date, text, text, text, double precision, text, text, text, integer,
  double precision, double precision, double precision, double precision, integer,
  text, text, text, smallint, timestamptz
) TO service_role;

GRANT EXECUTE ON FUNCTION public.fish_sniper_find_similar_fishing_log(
  uuid, text, text, integer
) TO service_role;

-- ---------------------------------------------------------------------------
-- PHASE 6 — 驗證（可於 SQL Editor 檢視結果）
-- ---------------------------------------------------------------------------
-- SELECT column_name, data_type, is_nullable
--   FROM information_schema.columns
--  WHERE table_schema = 'public' AND table_name = 'fishing_logs'
--  ORDER BY ordinal_position;
--
-- SELECT proname FROM pg_proc
--  WHERE proname IN (
--    'fish_sniper_insert_log_with_embedding',
--    'fish_sniper_update_log_with_embedding',
--    'fish_sniper_find_similar_fishing_log'
--  );
--
-- -- 確認 service_role 已拿到表的 DML 權限
-- SELECT table_name, privilege_type
--   FROM information_schema.role_table_grants
--  WHERE grantee = 'service_role'
--    AND table_schema = 'public'
--    AND table_name IN ('users','otp_codes','user_preferences','fishing_logs')
--  ORDER BY table_name, privilege_type;
--
-- -- 確認 service_role 已拿到 RPC 的 EXECUTE 權限
-- SELECT routine_name, privilege_type
--   FROM information_schema.role_routine_grants
--  WHERE grantee = 'service_role'
--    AND specific_schema = 'public'
--    AND routine_name LIKE 'fish_sniper_%';
