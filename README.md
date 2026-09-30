# FishSniper

![FishSniper](images/logo.png)

> Auth-first rebuild in progress. Phase 0 now connects Google identity to an internal
> Supabase user and protects application APIs with a FishSniper JWT.

Live demo: https://fish-sniper.pages.dev | Backend: Railway | Frontend: Cloudflare Pages

---

## What works now

1. Sign in with Google (authorization code + PKCE).
2. Backend exchanges the code at `POST /auth/google/exchange` and verifies the Google `id_token`.
3. Backend upserts a `users` row by `google_sub` and signs a FishSniper JWT whose `sub` is the internal user UUID.
4. Protected routes validate `Authorization: Bearer <token>` and load the current user from Supabase.
5. The signed-in dashboard calls `GET /api/v1/me` to validate the saved session.

---

## Tech stack

| Layer | Choices |
|-------|---------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router |
| Backend | Python 3.11, FastAPI, Pydantic v2 |
| Data | Supabase Postgres + Data API (backend-only secret key) |
| Auth | Google OAuth 2.0 + PKCE (server-side token exchange + JWKS) |
| Infra | Railway (backend), Cloudflare Pages (frontend) |

---

## Project structure

```txt
backend/
  app/
    main.py         FastAPI app factory, middleware, router registration
    core/           Settings, security, errors, rate limiting, time
    auth/           Google OAuth exchange, JWT, auth schemas and routes
    db/             Supabase REST client, users repository, DB dependencies
    users/          Protected current-user API
  tests/            pytest coverage for health, rate limiting, Google OAuth

frontend/
  src/
    app/            React app composition and routes
    auth/           Sign-in pages, auth UI, hooks, OAuth lib, auth API calls
    api/            Generic JSON HTTP client and common API envelope types
    config/         Public runtime environment readers
    i18n/           English/Traditional Chinese strings and language switcher
    users/          Current-user API and session validation hook
    dashboard/      Rebuilt tactical dashboard baseline

supabase/
  migrations/       Database schema migrations
```

---

## Frontend languages

The UI supports English (`en`) and Traditional Chinese (`zh-TW`) with i18next and
react-i18next. `frontend/src/i18n/translations.ts` contains matching translation keys
for both languages; components display them with `useTranslation()` and `t('key')`.
For dynamic text, pass variables such as `t('dashboard.signedInAs', { email })`.

The first visit follows the browser language (`zh*` selects Traditional Chinese;
otherwise English). A manual selection is saved as `fishsniper.language` in browser
`localStorage` and survives reloads in that browser. This is a frontend preference only:
it does not change Google OAuth, the JWT, Supabase user data, or API response language.

If an existing Docker development container uses the persistent `frontend_node_modules`
volume, install the new packages into that volume with
`docker compose -f docker-compose-dev.yaml run --rm --no-deps frontend npm ci` before
restarting the frontend.

---

## Local setup (short)

Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to
`frontend/.env`, fill Google OAuth + Supabase + JWT values, then apply
`supabase/migrations/202609240001_create_users.sql` to the target Supabase project.

Existing local environments using `JWT_SECRET` and `SUPABASE_SERVICE_ROLE_KEY` remain
supported during migration. New environments should use `JWT_SECRET_KEY` and
`SUPABASE_SECRET_KEY`.

```bash
# backend
cd backend && uv sync --all-groups && uv run uvicorn app.main:app --reload

# frontend
cd frontend && npm ci && npm run dev
```

CI: `.github/workflows/ci.yml` runs backend lint/tests and frontend build.

### Docker Desktop

After creating `backend/.env` and `frontend/.env`, start the development containers:

```bash
docker compose -f docker-compose-dev.yaml up --build
```

Open the frontend at `http://localhost:5173`; the backend health endpoint is
`http://localhost:8000/health`. Source directories are mounted into both containers,
so Vite and Uvicorn reload after local code changes.

Run all checks in disposable containers:

```bash
docker compose -f docker-compose-dev.yaml --profile test run --rm backend-lint
docker compose -f docker-compose-dev.yaml --profile test run --rm backend-test
docker compose -f docker-compose-dev.yaml --profile test run --rm frontend-build
```

Stop the development environment with `docker compose -f docker-compose-dev.yaml down`. Add `--volumes` only
when you intentionally want to recreate the container-managed Python and Node dependency
volumes.

The Docker environment connects to the Supabase project configured in `backend/.env`.
A standalone PostgreSQL container is not included because the backend currently uses the
Supabase Data API rather than a direct PostgreSQL connection.
