# Progress Log

## Session: 2026-07-28 — Auth-only strip execution

### Done
- Backend: removed strategy/llm/logs/weather/embedding/users; slimmed main, settings, persistence, tests
- Frontend: Google-only sign-in; signed-in iframe → `/ui-exploration/index.html`; deleted product UI
- Deps: trimmed `pyproject.toml` + `uv.lock`; updated `.env.example` files + README
- Verified: `pytest` 22 passed; `npm run build` ok

### Notes
- SQL script `scripts/supabase_reset_full_environment.sql` still describes old full schema (left for later slim)
- `docs/strategy-report-payload-v2-steps.md` leftover product doc (optional cleanup)

## Session: 2026-07-28 — Drop FishSniper code prefixes

### Done
- Backend + frontend identifier rename per findings.md
- Kept UI brand strings (`title="FishSniper"`, etc.)
- Verified: pytest 22 passed; `npm run build` ok
- Storage keys bumped (`access_token_jwt_v1`, `google_oauth_pkce_*_v1`) — existing sessions cleared once
