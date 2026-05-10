-- P4 Part 1: pgvector embedding columns + RPC functions for fishing_logs (FishSniper)
-- Apply after `scripts/supabase_p3_fishing_logs.sql`.
--
-- Decision (see docs/superpowers/specs/2026-05-09-p4-part1-embedding-crud-design.md):
--   * Embedding writes & queries both use OpenAI Embeddings (independent from Gemini LLM stack).
--   * Vector storage = same Postgres + pgvector column on `fishing_logs` (not Pinecone).
--   * `pinecone_synced` is a legacy naming relic from the early phased MVP (which considered Pinecone)
--     and is dropped here. The single source of truth for vector readiness is `embedding_status`.
--
-- Idempotent: every statement uses IF NOT EXISTS / IF EXISTS / CREATE OR REPLACE.

-- ---------------------------------------------------------------------------
-- 1. pgvector extension
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- 2. New columns on fishing_logs
-- ---------------------------------------------------------------------------
-- Embedding vector. Dimension matches OpenAI `text-embedding-3-small` (1536).
-- If the model changes, this column must be migrated to a new dimension.
ALTER TABLE fishing_logs
  ADD COLUMN IF NOT EXISTS embedding vector(1536) NULL;

-- Single source of truth for vector readiness.
ALTER TABLE fishing_logs
  ADD COLUMN IF NOT EXISTS embedding_status TEXT NOT NULL DEFAULT 'pending';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fishing_logs_embedding_status_check'
      AND conrelid = 'fishing_logs'::regclass
  ) THEN
    ALTER TABLE fishing_logs
      ADD CONSTRAINT fishing_logs_embedding_status_check
        CHECK (embedding_status IN ('pending', 'done', 'failed'));
  END IF;
END;
$$;

-- Embedding text template version. Bumped if the natural-language compose template changes;
-- queries in Part 2 will filter by version to avoid mixing vector spaces across template versions.
ALTER TABLE fishing_logs
  ADD COLUMN IF NOT EXISTS embedding_text_version SMALLINT NOT NULL DEFAULT 1;

-- Background-retry attempt counter. Part 1 never reads or writes this; the column is created
-- now so Part 2 (background worker) can ship without another Supabase ALTER TABLE migration.
ALTER TABLE fishing_logs
  ADD COLUMN IF NOT EXISTS embedding_attempt_count INTEGER NOT NULL DEFAULT 0;

-- ---------------------------------------------------------------------------
-- 3. Drop legacy column
-- ---------------------------------------------------------------------------
ALTER TABLE fishing_logs
  DROP COLUMN IF EXISTS pinecone_synced;

-- ---------------------------------------------------------------------------
-- 4. Partial index for the future background scheduler (Part 2)
--    Vector ANN index (ivfflat / hnsw) intentionally NOT created yet — current data volume
--    is too small to benefit. Add `CREATE INDEX … USING ivfflat (embedding vector_cosine_ops)`
--    once we cross ~1k rows.
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fishing_logs_pending_embeddings
  ON fishing_logs (created_at)
  WHERE embedding_status = 'pending';

-- ---------------------------------------------------------------------------
-- 5. RPC functions
--    supabase-py / PostgREST cannot run multi-statement transactions from the client side,
--    so atomic "insert row + write vector + flip status" is implemented as a single SQL
--    function the backend invokes via `client.rpc(...)`.
--
--    The vector is passed as text (e.g. '[0.1,-0.2,...]') and cast inside the function;
--    this keeps the Python adapter free of pgvector-specific serialization libraries.
-- ---------------------------------------------------------------------------

-- 5a. INSERT
CREATE OR REPLACE FUNCTION fish_sniper_insert_log_with_embedding(
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
  v_row fishing_logs%ROWTYPE;
BEGIN
  -- embedding_attempt_count intentionally omitted; uses DEFAULT 0.
  -- Part 2 background worker is the only writer of that column.
  INSERT INTO fishing_logs (
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

  -- Strip the raw vector from the response payload — saves bandwidth and avoids
  -- leaking a high-dimensional float array into application logs.
  RETURN to_jsonb(v_row) - 'embedding';
END;
$$;

-- 5b. UPDATE (full replace; matches the PATCH semantics already used by the API)
CREATE OR REPLACE FUNCTION fish_sniper_update_log_with_embedding(
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
  v_row fishing_logs%ROWTYPE;
BEGIN
  -- embedding_attempt_count intentionally not updated here — owned by Part 2 worker.
  UPDATE fishing_logs
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
    -- Log not found, or belongs to a different user → caller maps to HTTP 404.
    RETURN NULL;
  END IF;

  RETURN to_jsonb(v_row) - 'embedding';
END;
$$;

-- ---------------------------------------------------------------------------
-- 6. Quick verification queries (run manually after applying):
--      \d fishing_logs                                    -- expect new cols, no pinecone_synced
--      SELECT proname FROM pg_proc                        -- expect both functions
--       WHERE proname LIKE 'fish_sniper%embedding%';
-- ---------------------------------------------------------------------------
