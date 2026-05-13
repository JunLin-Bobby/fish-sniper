-- P3 seed: dev user + preferences + sample fishing_logs (phased MVP design).
-- Apply after schema is in place, using either:
--   A) `scripts/supabase_reset_full_environment.sql` (recommended: wipe + latest schema + RPC), or
--   B) `supabase_p1_schema.sql` -> `supabase_p3_fishing_logs.sql` -> `supabase_p4_part1_log_embeddings.sql`
-- Idempotent for the P1 rows; fishing log rows use fixed ids so re-runs do not duplicate.

INSERT INTO users (id, email) VALUES
  ('00000000-0000-0000-0000-000000000001', 'dev@fishsniper.local')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_preferences (user_id, region, onboarding_completed) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Boston', true)
ON CONFLICT (user_id) DO UPDATE SET
  region = EXCLUDED.region,
  onboarding_completed = EXCLUDED.onboarding_completed;

-- `pinecone_synced` was a P3 column (named after an early Pinecone exploration). It is
-- DROPPED in P4 Part 1 (see scripts/supabase_p4_part1_log_embeddings.sql) and replaced
-- by `embedding_status`. Seed rows insert without an explicit status — the column's
-- DEFAULT 'pending' takes effect, and the runtime POST /logs path (or future Part 2
-- background worker) will flip it to 'done' once Gemini embeddings are written.
INSERT INTO fishing_logs
  (id, user_id, date, fishing_location, fishing_scene, target_species, water_depth_m,
   lure_type, lure_color, retrieve_speed, caught_count, weight_lb,
   length_cm, temperature_c, condition_code, wind_speed_ms, pressure_hpa,
   notes)
VALUES
  ('10000000-0000-0000-0000-000000000001',
   '00000000-0000-0000-0000-000000000001',
   '2026-04-20', 'Charles River', 'river', 'Largemouth Bass', 3.0,
   'Soft plastic swimbait', 'Green pumpkin', 'Slow', 2, 3.09,
   38.0, 18.5, 'cloudy', 2.1, 1008,
   'Best action near the bridge pillars at 6am'),
  ('10000000-0000-0000-0000-000000000002',
   '00000000-0000-0000-0000-000000000001',
   '2026-04-15', 'Charles River', 'river', 'Smallmouth Bass', 2.5,
   'Crankbait', 'Chartreuse', 'Medium', 0, NULL,
   NULL, 16.0, 'rainy', 4.0, 1012,
   'No bites, tried structure near dam')
ON CONFLICT (id) DO NOTHING;
