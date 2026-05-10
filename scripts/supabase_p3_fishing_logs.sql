-- P3: fishing_logs (FishSniper)
-- Apply after `scripts/supabase_p1_schema.sql`.
--
-- Destructive reset (wipes all rows and removes the table). Uncomment only for local/dev rebuilds.
-- DROP TRIGGER IF EXISTS trg_fishing_logs_set_updated_at ON fishing_logs;
-- DROP TABLE IF EXISTS fishing_logs CASCADE;

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
  pinecone_synced BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (water_depth_m >= 0)
);

CREATE INDEX IF NOT EXISTS idx_fishing_logs_user_id_date_desc
  ON fishing_logs (user_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_fishing_logs_user_id_updated_at_desc
  ON fishing_logs (user_id, updated_at DESC);

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

-- Row Level Security (RLS)
-- FishSniper only connects from FastAPI using the Supabase service_role key, which bypasses RLS.
-- No policies are defined for anon/authenticated: PostgREST access with those roles cannot
-- read or write rows (default deny). Add policies only if you intentionally expose this table to clients.
ALTER TABLE fishing_logs ENABLE ROW LEVEL SECURITY;

