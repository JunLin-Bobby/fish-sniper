-- =============================================================================
-- P3: fishing_logs (FishSniper) — self-healing schema
-- =============================================================================
-- Apply after `scripts/supabase_p1_schema.sql`.
-- Then apply `scripts/supabase_p4_part1_log_embeddings.sql` to add the vector
-- column, embedding-status flags, and the two atomic INSERT/UPDATE RPCs.
--
-- For a full local/staging wipe (drops users, otp_codes, user_preferences,
-- fishing_logs and re-creates everything against the latest contract), use
-- `scripts/supabase_reset_full_environment.sql` instead — it is the destructive
-- single-paste path. **This** file is the non-destructive, re-runnable path.
--
-- Self-healing properties (re-run any number of times — every step is a no-op
-- once the schema matches):
--   * Fresh DB (table missing)             → CREATE TABLE branch fires.
--   * Drifted DB (older revision created
--     the table without later columns
--     such as `target_species`)            → ADD COLUMN IF NOT EXISTS +
--                                            backfill + SET NOT NULL converge.
--   * Already-correct DB                   → all statements are idempotent.
--
-- Symptom this file fixes (taken from real backend logs):
--   postgrest.exceptions.APIError:
--     {'message': 'column fishing_logs.target_species does not exist',
--      'code': '42703', ...}
--
-- This file deliberately does NOT touch `pinecone_synced`, `embedding`,
-- `embedding_status`, `embedding_text_version`, or `embedding_attempt_count`
-- — those are the responsibility of `supabase_p4_part1_log_embeddings.sql`,
-- which both creates the new vector columns and DROPs the legacy
-- `pinecone_synced`. Keeping that boundary makes the migration history easy
-- to read.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. CREATE TABLE for fresh databases (no-op if table already exists)
--    Defines the canonical P3 shape. Drift repair below converges existing
--    tables to this same shape.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fishing_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  date DATE NOT NULL,
  fishing_location TEXT NOT NULL,
  fishing_scene TEXT NOT NULL,
  target_species TEXT NOT NULL CHECK (target_species IN ('Largemouth Bass', 'Smallmouth Bass')),
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
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (water_depth_m >= 0)
);

-- ---------------------------------------------------------------------------
-- 2. Drift repair — ADD COLUMN IF NOT EXISTS as nullable so existing rows
--    don't blow up the migration. Foundational columns (id / user_id / date)
--    are NOT re-added defensively: if they are missing the table is too
--    broken to repair safely and you should run
--    `scripts/supabase_reset_full_environment.sql` instead.
-- ---------------------------------------------------------------------------
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS fishing_location TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS fishing_scene    TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS target_species   TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS water_depth_m    DOUBLE PRECISION;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS lure_type        TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS lure_color       TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS retrieve_speed   TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS caught_count     INTEGER;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS weight_lb        DOUBLE PRECISION;  -- nullable in P3 spec
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS length_cm        DOUBLE PRECISION;  -- nullable in P3 spec
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS temperature_c    DOUBLE PRECISION;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS wind_speed_ms    DOUBLE PRECISION;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS pressure_hpa     INTEGER;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS condition_code   TEXT;
ALTER TABLE fishing_logs ADD COLUMN IF NOT EXISTS notes            TEXT;

-- ---------------------------------------------------------------------------
-- 3. Back-fill NULLs with safe placeholders before tightening NOT NULL.
--    These values are intentionally obvious-looking ('(unknown)' / 0 / 1013)
--    so a human auditing the table later can spot pre-drift rows and
--    correct them by hand. Adjust before running if you have better data.
--    `weight_lb` and `length_cm` stay NULL because they are nullable in P3.
-- ---------------------------------------------------------------------------
UPDATE fishing_logs SET fishing_location = '(unknown)'       WHERE fishing_location IS NULL;
UPDATE fishing_logs SET fishing_scene    = '(unknown)'       WHERE fishing_scene    IS NULL;
UPDATE fishing_logs SET target_species   = 'Largemouth Bass' WHERE target_species   IS NULL;
UPDATE fishing_logs SET water_depth_m    = 0                 WHERE water_depth_m    IS NULL;
UPDATE fishing_logs SET lure_type        = '(unknown)'       WHERE lure_type        IS NULL;
UPDATE fishing_logs SET lure_color       = '(unknown)'       WHERE lure_color       IS NULL;
UPDATE fishing_logs SET retrieve_speed   = '(unknown)'       WHERE retrieve_speed   IS NULL;
UPDATE fishing_logs SET caught_count     = 0                 WHERE caught_count     IS NULL;
UPDATE fishing_logs SET temperature_c    = 0                 WHERE temperature_c    IS NULL;
UPDATE fishing_logs SET wind_speed_ms    = 0                 WHERE wind_speed_ms    IS NULL;
UPDATE fishing_logs SET pressure_hpa     = 1013              WHERE pressure_hpa     IS NULL;
UPDATE fishing_logs SET condition_code   = 'cloudy'          WHERE condition_code   IS NULL;
UPDATE fishing_logs SET notes            = ''                WHERE notes            IS NULL;

-- ---------------------------------------------------------------------------
-- 4. SET NOT NULL + DEFAULTs to converge with the canonical CREATE TABLE.
--    On a fresh database every line is a no-op (already enforced).
-- ---------------------------------------------------------------------------
ALTER TABLE fishing_logs ALTER COLUMN fishing_location SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN fishing_scene    SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN target_species   SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN water_depth_m    SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN lure_type        SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN lure_color       SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN retrieve_speed   SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN caught_count     SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN temperature_c    SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN wind_speed_ms    SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN pressure_hpa     SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN condition_code   SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN notes            SET NOT NULL;
ALTER TABLE fishing_logs ALTER COLUMN notes            SET DEFAULT '';

-- ---------------------------------------------------------------------------
-- 5. CHECK constraints (idempotent via pg_constraint lookup).
--    The CREATE TABLE branch installs them on fresh DBs; this block adds
--    them on tables created before the constraints existed.
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fishing_logs_target_species_check'
      AND conrelid = 'fishing_logs'::regclass
  ) THEN
    ALTER TABLE fishing_logs
      ADD CONSTRAINT fishing_logs_target_species_check
        CHECK (target_species IN ('Largemouth Bass', 'Smallmouth Bass'));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fishing_logs_caught_count_check'
      AND conrelid = 'fishing_logs'::regclass
  ) THEN
    ALTER TABLE fishing_logs
      ADD CONSTRAINT fishing_logs_caught_count_check
        CHECK (caught_count >= 0);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'fishing_logs_water_depth_m_check'
      AND conrelid = 'fishing_logs'::regclass
  ) THEN
    ALTER TABLE fishing_logs
      ADD CONSTRAINT fishing_logs_water_depth_m_check
        CHECK (water_depth_m >= 0);
  END IF;
END;
$$;

-- ---------------------------------------------------------------------------
-- 6. Indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_fishing_logs_user_id_date_desc
  ON fishing_logs (user_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_fishing_logs_user_id_updated_at_desc
  ON fishing_logs (user_id, updated_at DESC);

-- ---------------------------------------------------------------------------
-- 7. updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fish_sniper_set_fishing_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_fishing_logs_set_updated_at ON fishing_logs;
CREATE TRIGGER trg_fishing_logs_set_updated_at
  BEFORE UPDATE ON fishing_logs
  FOR EACH ROW
  EXECUTE PROCEDURE fish_sniper_set_fishing_logs_updated_at();

-- ---------------------------------------------------------------------------
-- 8. Row Level Security
--    FishSniper only connects from FastAPI using the Supabase service_role
--    key, which bypasses RLS. No policies are defined for anon/authenticated:
--    PostgREST access with those roles cannot read or write rows
--    (default deny). Add policies only if you intentionally expose this
--    table to clients.
-- ---------------------------------------------------------------------------
ALTER TABLE fishing_logs ENABLE ROW LEVEL SECURITY;

COMMIT;

-- ---------------------------------------------------------------------------
-- 9. Verification (read-only). Compare the column list to:
--    id, user_id, date, fishing_location, fishing_scene, target_species,
--    water_depth_m, lure_type, lure_color, retrieve_speed, caught_count,
--    weight_lb, length_cm, temperature_c, wind_speed_ms, pressure_hpa,
--    condition_code, notes, created_at, updated_at
--
--    After this file, also run `scripts/supabase_p4_part1_log_embeddings.sql`
--    so the table also exposes embedding / embedding_status /
--    embedding_text_version / embedding_attempt_count and the two RPCs.
-- ---------------------------------------------------------------------------
SELECT column_name, data_type, is_nullable
  FROM information_schema.columns
 WHERE table_name = 'fishing_logs'
 ORDER BY ordinal_position;
