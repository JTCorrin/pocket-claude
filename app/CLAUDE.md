# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Commands

```bash
pnpm dev          # Start dev server
pnpm build        # Build for production (outputs to /build)
pnpm check        # TypeScript type checking
pnpm lint         # Prettier + ESLint
pnpm test         # Run tests once
pnpm test:unit    # Run tests in watch mode
```

**Capacitor (after build):**

```bash
pnpm sync      # Sync web build to native projects
pnpm open:android
pnpm open:ios
```

## Architecture

### SSR Configuration

SSR is disabled in `+layout.ts`:

```typescript
export const prerender = true;
export const ssr = false;
```

This means:

- No `+page.server.ts` files (form actions won't work)
- `load` functions in `+page.ts` run client-side only
- No need to inject `fetch` - use global fetch directly

### API Layer (`$lib/api/`)

Type-safe API client with JWT auth and offline support:

```
src/lib/api/
├── client.ts           # Base fetch wrapper, auth token management
├── errors.ts           # ApiError, NetworkError, TimeoutError, etc.
├── types.ts            # TypeScript interfaces
├── schemas.ts          # Zod validation schemas
├── index.ts            # Main exports, apiClient object
├── offline/
│   ├── connectivity.svelte.ts  # Network status ($state)
│   ├── queue.svelte.ts         # Offline request queue ($state)
│   ├── cache.ts                # Response caching with TTL
│   └── index.ts
└── endpoints/
    └── example.ts      # Example endpoint pattern
```

**Creating new endpoints:** Copy `endpoints/example.ts` and adapt.

**Environment:** Set `VITE_API_URL` in `.env`

### Key Patterns

**Svelte 5 Runes:** Use `$state`, `$derived`, `$effect` - not stores. Files
using runes at module level must be `.svelte.ts`.

**Offline support:** Initialize in root layout:

```svelte
<script>
  import { onMount, onDestroy } from 'svelte';
  import { initOfflineSupport, stopOfflineSupport } from '$lib/api/offline';

  onMount(() => initOfflineSupport());
  onDestroy(() => stopOfflineSupport());
</script>
```

## Testing

Vitest with two test projects configured in `vite.config.ts`:

| Project  | Environment          | File Pattern        | Use For                         |
| -------- | -------------------- | ------------------- | ------------------------------- |
| `client` | Browser (Playwright) | `*.svelte.test.ts`  | Svelte component tests          |
| `server` | Node                 | `*.test.ts`         | Unit tests, API logic, utilities |

**Test files are colocated** next to source files:

```
src/lib/components/
├── Button.svelte
└── Button.svelte.test.ts
```

For adding new components use shadcn-svelte:

`pnpm dlx shadcn-svelte@latest add {the component you need}`

See: https://www.shadcn-svelte.com/docs/components

**Running specific projects:**

```bash
pnpm test -- --run --project=client   # Browser tests only
pnpm test -- --run --project=server   # Node tests only
```

**Note:** `requireAssertions: true` is enabled - every test must have at least
one assertion.

## Tech Stack

- **Svelte 5** with runes
- **SvelteKit** (static adapter)
- **Capacitor 8** for native mobile
- **Tailwind CSS 4** + shadcn-svelte (bits-ui)
- **Zod 4** for validation
- **Vitest 4** with Playwright browser testing
