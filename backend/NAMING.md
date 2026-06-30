# Backend naming conventions

FishSniper backend code uses short, domain-local names. Avoid repeating the product name in every identifier.

## Rules

| Context | Convention | Example |
|---------|------------|---------|
| Settings class | `AppSettings` | was `FishSniperBackendSettings` |
| Settings getter | `get_settings()` | was `get_fish_sniper_backend_settings()` |
| Settings DI | `SettingsDep` | was `FishSniperSettingsDep` |
| Persistence port | `PersistencePort` | was `FishSniperPersistencePort` |
| Persistence getter | `get_persistence()` | was `get_fish_sniper_persistence_port()` |
| Persistence DI | `PersistenceDep` | was `FishSniperPersistenceDep` |
| Handler locals | `settings`, `persistence`, `user_id` | not `fish_sniper_backend_settings` |
| Row field | `user_id` | not `fish_sniper_user_id` (incremental migration) |
| Module paths | domain package | `auth/router.py`, `strategy/graph.py` |

## Keep `fish_sniper` prefix

- Public API URL paths (`/agent`, product branding)
- Database migration SQL scripts
- Frontend code (out of backend scope)

## Domain layout

```
auth/       router, schemas, deps, jwt, google oauth
users/      preferences_router, account_router, schemas
logs/       router, schemas
strategy/   router, schemas, graph, deps, prompts
weather/    router, schemas, service, deps
persistence/ users.py, logs.py, port.py (composite)
embedding/  adapters + deps
llm/        adapters + registry
```

## Tests

```
tests/
  api/        TestClient + dependency overrides
  unit/       no HTTP; mocked externals
  doubles/    in-memory DB, fake embedding
  support/    app_factory, jwt_helpers
```
