# Findings: Rename plan — drop `FishSniper` / `fish_sniper` code prefixes

## Scope
Auth-only codebase currently on disk. **Product brand text** in UI (`title="FishSniper"`) can stay.  
**Out of scope unless you say otherwise:** repo folder name, `pyproject.toml` package name `fishsniper-backend`, env var names (`GOOGLE_OAUTH_*`, `JWT_*`), HTTP paths.

## Naming convention (proposed)
| Pattern today | Proposed |
|---------------|----------|
| `FishSniperX` (type/component) | `X` or domain-clear name (`UserRow`, `AuthShell`) |
| `fishSniperX` / `fish_sniper_x` | `x` camelCase / snake_case |
| `FISH_SNIPER_*` constants | shorter domain key (`ACCESS_TOKEN_*`, `GOOGLE_OAUTH_PKCE_*`) |
| `fish_sniper_*` storage keys | bump version + new key (see note below) |

---

## Frontend — file renames

| Current path | Proposed path |
|--------------|---------------|
| `src/api/fishSniperApiTypes.ts` | `src/api/apiTypes.ts` |
| `src/api/fishSniperJsonHttpClient.ts` | `src/api/jsonHttpClient.ts` |
| `src/auth/fishSniperAccessTokenStorage.ts` | `src/auth/accessTokenStorage.ts` |
| `src/auth/fishSniperGoogleOAuthPkce.ts` | `src/auth/googleOAuthPkce.ts` |
| `src/auth/fishSniperGoogleOAuthExchangeDedupe.ts` | `src/auth/googleOAuthExchangeDedupe.ts` |
| `src/auth/readEmailFromFishSniperAccessTokenJwt.ts` | `src/auth/readEmailFromAccessTokenJwt.ts` |
| `src/config/readFishSniperPublicEnv.ts` | `src/config/readPublicEnv.ts` |
| `src/hooks/useFishSniperAuthSessionState.ts` | `src/hooks/useAuthSessionState.ts` |
| `src/pages/FishSniperGoogleOAuthCallbackPage.tsx` | `src/pages/GoogleOAuthCallbackPage.tsx` |
| `src/ui/FishSniperTacticalAuthShell.tsx` | `src/ui/TacticalAuthShell.tsx` |
| `src/ui/FishSniperTacticalBackdrop.tsx` | `src/ui/TacticalBackdrop.tsx` |
| `src/ui/fishSniperTacticalUi.ts` | `src/ui/tacticalUi.ts` |
| `src/App.tsx` | keep path; rename internal symbols |

Also touch imports in: `App.tsx`, callback page, auth modules (all consumers of above).

---

## Frontend — symbol / parameter renames

### API
| Current | Proposed |
|---------|----------|
| `FishSniperTopLevelErrorPayload` | `TopLevelErrorPayload` |
| `FishSniperHttpDetailEnvelopePayload` | `HttpDetailEnvelopePayload` |
| `FishSniperHttpTimeoutError` | `HttpTimeoutError` |
| `FishSniperHttpStatusError` | `HttpStatusError` |
| `parseFishSniperErrorMessageFromResponseBody` | `parseErrorMessageFromResponseBody` |
| `postJsonWithFishSniperApi` | `postJson` |
| `getJsonWithFishSniperApi` | `getJson` |
| `deleteJsonWithFishSniperApi` | `deleteJson` |

### Auth / config / hooks
| Current | Proposed |
|---------|----------|
| `readFishSniperAccessTokenJwtFromBrowserStorage` | `readAccessTokenFromStorage` |
| `writeFishSniperAccessTokenJwtToBrowserStorage` | `writeAccessTokenToStorage` |
| `clearFishSniperAccessTokenJwtFromBrowserStorage` | `clearAccessTokenFromStorage` |
| `FISH_SNIPER_ACCESS_TOKEN_LOCAL_STORAGE_KEY` / `'fish_sniper_access_token_jwt_v1'` | `ACCESS_TOKEN_STORAGE_KEY` / `'access_token_jwt_v1'` |
| `FISH_SNIPER_GOOGLE_OAUTH_PKCE_*` / `fish_sniper_google_oauth_pkce_*_v1` | `GOOGLE_OAUTH_PKCE_*` / `google_oauth_pkce_*_v1` |
| `FishSniperGoogleOAuthExchangeDedupeResult` | `GoogleOAuthExchangeDedupeResult` |
| `readEmailFromFishSniperAccessTokenJwt` | `readEmailFromAccessTokenJwt` |
| `readFishSniperApiBaseUrlFromPublicEnv` | `readApiBaseUrlFromPublicEnv` |
| `FishSniperGoogleOAuthPublicConfig` | `GoogleOAuthPublicConfig` |
| `readFishSniperGoogleOAuthPublicConfigFromEnvOrNull` | `readGoogleOAuthPublicConfigFromEnvOrNull` |
| `useFishSniperAuthSessionState` | `useAuthSessionState` |

### UI / App local components
| Current | Proposed |
|---------|----------|
| `FishSniperTacticalAuthShell` | `TacticalAuthShell` |
| `FishSniperTacticalBackdrop` | `TacticalBackdrop` |
| `fishSniperTactical*ClassName` | `tactical*ClassName` (e.g. `tacticalAuthCardClassName`) |
| `FishSniperGoogleOAuthCallbackPage` | `GoogleOAuthCallbackPage` |
| `FishSniperGoogleOAuthCallbackRoute` | `GoogleOAuthCallbackRoute` |
| `FishSniperGoogleSignInPage` | `GoogleSignInPage` |
| `FishSniperSignedInExplorationPage` | `SignedInExplorationPage` |
| `fishSniperApiBaseUrl` | `apiBaseUrl` |
| `fishSniperAuthSession` | `authSession` |

**Keep as brand copy (not code ids):** UI `title="FishSniper"`, eyebrow `"FishSniper · …"`, iframe `title="FishSniper UI exploration"`.

---

## Backend — file renames

| Current path | Proposed path |
|--------------|---------------|
| `persistence/supabase_fish_sniper_persistence_adapter.py` | `persistence/supabase_adapter.py` |

All other backend files keep path; symbols inside change.

---

## Backend — symbol / parameter renames

### App / infra
| Current | Proposed |
|---------|----------|
| `create_fish_sniper_app` | `create_app` |
| `fish_sniper_api_limiter` | `api_limiter` |
| `fish_sniper_handle_rate_limit_exceeded` | `handle_rate_limit_exceeded` |
| `fish_sniper_jwt_email_slowapi_key_func` | `jwt_email_slowapi_key_func` |
| `fish_sniper_http_exception_handler` | `http_exception_handler` |
| `fish_sniper_request_validation_handler` | `request_validation_handler` |
| `fish_sniper_backend_settings` (locals/params) | `settings` |
| FastAPI `title="FishSniper API"` | keep brand **or** `"API"` — recommend keep brand |

### Auth / JWT
| Current | Proposed |
|---------|----------|
| `issue_access_token_jwt_for_fish_sniper_user_id` | `issue_access_token` |
| `decode_fish_sniper_user_id_from_access_token_jwt` | `decode_user_id_from_access_token` |
| `decode_fish_sniper_rate_limit_key_from_access_token_jwt` | `decode_rate_limit_key_from_access_token` |
| `perform_google_oauth_exchange_for_fish_sniper_user` | `perform_google_oauth_exchange` |
| `fish_sniper_user_id` | `user_id` |
| `fish_sniper_persistence` | `persistence` |
| `__fish_sniper_expired_jwt__` etc. | `__expired_jwt__` / `__invalid_jwt__` / `__missing_jwt_claims__` / `__missing_bearer__` |

### Persistence / security
| Current | Proposed |
|---------|----------|
| `FishSniperUserRow` | `UserRow` |
| `.fish_sniper_user_id` field | `.user_id` |
| `FishSniperPersistenceUnavailableError` | `PersistenceUnavailableError` |
| `SupabaseFishSniperPersistenceAdapter` | `SupabasePersistenceAdapter` |
| `InMemoryFishSniperPersistenceAdapter` | `InMemoryPersistenceAdapter` |
| `get_current_fish_sniper_user_id_from_authorization_header` | `get_current_user_id_from_authorization_header` |
| `FishSniperUserIdDep` | `UserIdDep` |
| `reset_fish_sniper_backend_settings_cache` (fixture) | `reset_settings_cache` |

### Tests that import the above
- `tests/api/auth/test_google_oauth_exchange.py`
- `tests/api/test_health.py`
- `tests/api/test_rate_limiting.py`
- `tests/doubles/in_memory_db.py`, `__init__.py`
- `tests/support/jwt_helpers.py`, `app_factory.py`
- `tests/conftest.py`
- unit auth tests (if they reference renamed helpers)

---

## Storage key migration note
Changing `localStorage` / `sessionStorage` key strings logs everyone out once (harmless for auth-only).  
Options: (A) new keys only, or (B) read old key once then migrate. Recommend **A**.

## Explicitly not renaming (unless requested)
- Repo / folder `FishSniper`
- Package name `fishsniper-backend`
- Env: `SKIP_AUTH_RATE_LIMIT_EMAIL=skip-auth-dev@fishsniper.local`
- Test fake Google client id string containing `fishsniper`
- User-facing brand strings

## Open question for you
Confirm: **UI 上顯示的「FishSniper」品牌字要保留**，只改程式識別名稱？
