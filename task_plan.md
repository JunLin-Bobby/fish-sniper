# Task Plan: Auth-only strip-down (Google OAuth)

## Goal
Strip FishSniper down so only Google OAuth auth remains; after login, show `frontend/public/ui-exploration/index.html` as the signed-in success surface.

## Current Phase
Phase 5 complete — verify / handoff

## Phases

### Phase 1: Requirements & Discovery
- **Status:** complete

### Phase 2: Planning & Structure
- Decisions locked: Google-only; delete users/OTP/product domains; post-login iframe + Sign out
- **Status:** complete

### Phase 3: Backend strip
- **Status:** complete

### Phase 4: Frontend strip
- **Status:** complete

### Phase 5: Wiring, deps, verification
- Backend: 22 pytest passed; ruff pending in progress.md
- Frontend: `npm run build` passed
- **Status:** complete

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Post-login = iframe of ui-exploration + Sign out | Keeps SPA session control without editing static HTML |
| Delete Email OTP + users prefs/delete-account | Auth-only scope |
| Slim persistence to users find/create | Only what Google exchange needs |
| Drop langgraph/openai/genai/langfuse/yaml deps | No longer imported |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| frontend deletes no-op (cwd was backend) | 1 | Re-ran deletes from repo root |
| conftest ImportError fake_embedding | 1 | Slimmed tests/doubles/__init__.py |
