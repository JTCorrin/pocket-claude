# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Monorepo containing two apps that work together:
- **`/app`** - Mobile-first SvelteKit frontend (iOS/Android via Capacitor + web SPA)
- **`/api`** - FastAPI backend wrapping Claude Code CLI for HTTP-based session management

## Commands

### Frontend (`/app`)

```bash
cd app
pnpm dev          # Dev server (localhost:5173)
pnpm build        # Production build
pnpm check        # TypeScript type checking
pnpm lint         # Prettier + ESLint
pnpm test         # Run all tests
pnpm test -- --run --project=client   # Browser tests only
pnpm test -- --run --project=server   # Node tests only
pnpm sync         # Sync to Capacitor native projects
pnpm open:ios     # Open Xcode
pnpm open:android # Open Android Studio
```

### Backend (`/api`)

```bash
cd api
uv sync                                              # Install dependencies
python -m uvicorn app.main:app --reload --port 8000  # Dev server
pytest                                               # Run tests
pytest -v                                            # Verbose tests
```

Docker:
```bash
docker build -t api:latest .
docker run -p 8000:8000 api:latest
```

## Architecture

### Frontend

SSR is disabled (`prerender = true`, `ssr = false` in `+layout.ts`):
- No `+page.server.ts` files
- `load` functions run client-side only
- Use global `fetch` directly

**Svelte 5 Runes:** Use `$state`, `$derived`, `$effect` - not stores. Files using runes at module level must be `.svelte.ts`.

**API Layer (`$lib/api/`):**
- Type-safe client with JWT auth, Zod validation, timeout handling
- Offline support: request queuing, response caching, connectivity monitoring
- New endpoints: copy `endpoints/example.ts` and adapt

**Testing:** Two Vitest projects - `*.svelte.test.ts` (browser/Playwright), `*.test.ts` (Node)

See [app/CLAUDE.md](app/CLAUDE.md) for detailed frontend patterns.

### Backend

Clean architecture pattern:
```
api/app/
├── main.py              # FastAPI app, middleware registration
├── core/
│   ├── config.py        # Settings (pydantic-settings)
│   ├── exceptions.py    # AppException, NotFoundException, etc.
│   └── error_handlers.py
├── api/v1/
│   ├── router.py        # Aggregates all route modules
│   ├── routes/          # Endpoint definitions
│   └── controllers/     # Business logic coordination
└── services/            # Business logic
```

**Exception hierarchy:** `AppException` (base, 500) → `NotFoundException` (404), `BadRequestException` (400), `UnauthorizedException` (401), `ForbiddenException` (403)

**API docs:** Auto-generated at `/docs` (Swagger) and `/redoc`

**Planned endpoints** (see `API_PLAN.md`):
- `GET /sessions` - List Claude Code sessions
- `POST /chat` - Send message, optionally resume session
- `GET /projects` - List known projects

## Tech Stack

| | Frontend | Backend |
|---|---|---|
| Framework | SvelteKit 2 (Svelte 5) | FastAPI |
| Language | TypeScript | Python 3.13+ |
| Validation | Zod 4 | Pydantic 2 |
| Testing | Vitest + Playwright | pytest + pytest-asyncio |
| Styling | Tailwind CSS 4 + shadcn-svelte | - |
| Mobile | Capacitor 8 | - |
| Package Manager | pnpm | uv |

## Environment Variables

Frontend (`.env`):
- `VITE_API_URL` - Backend API base URL

Backend (`.env`):
- `API_V1_PREFIX`, `PROJECT_NAME`, `VERSION`, `ENVIRONMENT`, `DEBUG`, `CORS_ORIGINS`
