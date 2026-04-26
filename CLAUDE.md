# CLAUDE.md — msgvault-vue

## Project Overview

Standalone Vue 3 frontend for msgvault — a 1:1 port of the existing templ+HTMX web UI. Communicates with msgvault's `/api/v1` REST API.

## Tech Stack

Vue 3 + Vite + TypeScript + Vue Router

## Commands

ALL commands must run inside `flox activate`:

```bash
flox activate -c 'npm run dev'        # Dev server (port 3000)
flox activate -c 'npm run build'      # Production build
flox activate -c 'npm run test'       # Run tests (vitest)
flox activate -c 'npm run test:watch' # Watch mode tests
flox activate -c 'npm install'        # Install deps
```

**NEVER run bare npm, npx, node, or vite commands outside of flox.**

## Dev Server

Vite dev server runs on port 3000. Proxies `/api`, `/messages`, `/attachments` to `localhost:8080` (msgvault backend).

## Git Workflow

- Conventional commits: `feat:`, `fix:`, `chore:`, `refactor:`
- Stage all modified files before committing
- Run `git diff` and `git status` before committing

## Code Style

- TypeScript strict mode
- Vue 3 Composition API with `<script setup lang="ts">`
- No deletion features in this UI (removed from port)
