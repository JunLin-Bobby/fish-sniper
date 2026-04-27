-- P1 seed: dev user + preferences for P2+ local testing (phased MVP design).
-- Requires schema from supabase_p1_schema.sql.

INSERT INTO users (id, email) VALUES
  ('00000000-0000-0000-0000-000000000001', 'dev@fishsniper.local')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_preferences (user_id, region, onboarding_completed) VALUES
  ('00000000-0000-0000-0000-000000000001', 'Boston', true)
ON CONFLICT (user_id) DO UPDATE SET
  region = EXCLUDED.region,
  onboarding_completed = EXCLUDED.onboarding_completed;
