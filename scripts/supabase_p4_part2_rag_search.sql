-- P4 Part 2: pgvector RAG search RPC for fishing_logs (FishSniper)
-- Apply after `scripts/supabase_p4_part1_log_embeddings.sql`.
--
-- Idempotent: CREATE OR REPLACE.

CREATE OR REPLACE FUNCTION fish_sniper_find_similar_fishing_log(
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
    FROM fishing_logs fl
   WHERE fl.user_id          = p_user_id
     AND fl.target_species   = p_target_species
     AND fl.embedding_status = 'done'
     AND fl.embedding IS NOT NULL
   ORDER BY fl.embedding <=> v_query_vec ASC, fl.id ASC
   LIMIT p_limit;
END;
$$;
