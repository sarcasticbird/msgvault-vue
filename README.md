# msgvault-vue

Standalone Vue 3 frontend for [msgvault](https://github.com/wesm/msgvault).

## About msgvault

[msgvault](https://github.com/wesm/msgvault) is an excellent offline email archival tool that exports and stores Gmail data locally with full-text search, Parquet-based analytics, and a Bubble Tea TUI. It supports multi-account sync, incremental updates, Apple Mail import, and content-addressed attachment deduplication. If you have years of email you want to own and search locally, msgvault is the tool for the job. Check out the [msgvault repo](https://github.com/wesm/msgvault) for the backend, CLI, and TUI.

## Why This Project

This is a 1:1 port of msgvault's embedded templ+HTMX web UI into an independent SPA that talks to the `/api/v1` REST API. The original web UI is tightly coupled to the Go binary (embedded templates, direct query engine access). This project decouples the frontend so it can evolve independently, run on different hosts, and eventually replace the embedded UI.

## Stack

- **Vue 3** with Composition API (`<script setup lang="ts">`)
- **Vite** for dev server and production builds
- **TypeScript** in strict mode
- **Vue Router** with HTML5 history mode
- **Vitest** for unit tests
- **ESLint** with vue + typescript-eslint rules
- **Husky** pre-commit hooks (lint, typecheck, tests)

No UI framework — uses the same CSS from the original web UI.

## Quick Start

Requires [Flox](https://flox.dev) and a running msgvault server on port 8080.

```bash
git clone <repo-url> && cd msgvault-vue
flox activate -c 'npm install'
flox activate -c 'npm run dev'
```

Open http://localhost:3000. The Vite dev server proxies `/api`, `/messages`, and `/attachments` to `localhost:8080`.

## Commands

```bash
flox activate -c 'npm run dev'        # Dev server (port 3000, hot reload)
flox activate -c 'npm run build'      # Production build (typecheck + vite build)
flox activate -c 'npm run preview'    # Preview production build
flox activate -c 'npm run test'       # Run tests
flox activate -c 'npm run test:watch' # Watch mode tests
flox activate -c 'npm run lint'       # Lint (ESLint)
flox activate -c 'npm run lint:fix'   # Lint with auto-fix
flox activate -c 'npm run typecheck'  # Type check (vue-tsc)
```

## Pages

| Route | View | Description |
|-------|------|-------------|
| `/` | Dashboard | Stats cards, account list with sync buttons, quick links |
| `/browse` | Browse | Aggregate views (senders, domains, labels, time) with drill-down |
| `/messages` | Messages | Filtered message list with sorting and pagination |
| `/messages/:id` | Message Detail | Full message headers, attachments, sandboxed HTML body |
| `/search` | Search | Fast search with deep search fallback |

## Architecture

```
src/
  api/client.ts          # Typed API client (fetch-based, all endpoints)
  composables/
    useKeyboard.ts       # Vim-style keyboard shortcuts (j/k, /, ?, etc.)
    useMessageNav.ts     # Prev/next message navigation state
    useTheme.ts          # Theme toggle (auto/dark/light)
  components/
    HelpOverlay.vue      # Keyboard shortcuts help dialog
    MessageTable.vue     # Reusable message list table
    Pagination.vue       # Page navigation controls
    PillGroup.vue        # Toggle pill buttons (views, sort)
    StatsBar.vue         # Compact stats summary bar
  views/
    BrowseView.vue       # Aggregate browse + drill-down
    DashboardView.vue    # Dashboard with stats + accounts
    MessageDetailView.vue # Single message with iframe body
    MessagesView.vue     # Filtered message list
    SearchView.vue       # Search interface
  utils/format.ts        # Formatting helpers (bytes, counts, dates)
  router.ts              # Vue Router config
  main.ts                # App entry point
  App.vue                # Root component (nav, theme, keyboard)
```

## API

Talks to msgvault's `/api/v1` REST API. All endpoints are typed in `src/api/client.ts`.

Key endpoints used:
- `GET /api/v1/stats/total` — dashboard stats
- `GET /api/v1/accounts` — account list
- `POST /api/v1/sync/{account}` — trigger manual sync
- `GET /api/v1/scheduler/status` — poll sync progress
- `GET /api/v1/aggregates` — browse views
- `GET /api/v1/messages/filter` — filtered message list
- `GET /api/v1/messages/{id}` — message detail
- `GET /messages/{id}/html` — rendered HTML body (proxied, not under `/api`)
- `GET /api/v1/search/fast` — fast search
- `GET /api/v1/search/deep` — deep (paginated) search

## Configuration

Copy `.env.example` to `.env` for local overrides:

```bash
# API base URL (dev server proxies by default, only needed for production)
VITE_API_URL=/api/v1

# API key for remote access (WARNING: inlined into JS bundle at build time)
# VITE_API_KEY=your-key
```

The Vite dev server proxy config is in `vite.config.ts`.

## Keyboard Shortcuts

Press `?` to see the help overlay. Highlights:

| Key | Action |
|-----|--------|
| `j` / `k` | Navigate table rows |
| `Enter` | Open selected row |
| `/` | Focus search |
| `n` / `p` | Next / previous page |
| `<` / `>` | Previous / next message |
| `H` | Go to dashboard |
| `B` | Go to browse |
| `?` | Toggle help |

## Email Rendering

Message HTML bodies are rendered in a sandboxed iframe (`sandbox="allow-scripts"`) that loads from `/messages/{id}/html`. The iframe communicates its content height via `postMessage` for auto-resizing.

## Development Notes

- **No deletion features** — intentionally removed from this port
- **Theme** — cycles auto/dark/light, persisted to localStorage
- **Race conditions** — all async data fetching uses fetchId counters to discard stale responses
- **Navigation** — prev/next message navigation uses a stored ID list from the last message list view
- **Accounts** — the API merges database sources with config entries, so newly added accounts appear immediately

## Tests

```bash
flox activate -c 'npm run test'
```

45 tests across 4 files:
- `format.test.ts` — all formatting functions (bytes, counts, dates, relative times)
- `client.test.ts` — API client (auth, errors, all endpoints, URL encoding)
- `useMessageNav.test.ts` — message navigation composable (edge cases, state management)
- `useTheme.test.ts` — theme toggle cycle and DOM/localStorage persistence

## Pre-commit Hooks

Husky runs three gates on every commit:
1. `npm run lint` — ESLint
2. `npm run typecheck` — vue-tsc
3. `npm run test` — vitest

## License

Same as msgvault.
