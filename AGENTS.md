# AGENTS.md

Guidance for coding agents working in the Faísca monorepo. Each app has its
own rules, and they win inside their folder:

- `backend/AGENTS.md`: the FastAPI modular monolith (moarch-py), with its
  layers, `public.py` boundaries and checks.
- `web/AGENTS.md`: Next.js (read the bundled docs in
  `node_modules/next/dist/docs/` before using an API).
- `mobile/`: the future Flutter app (moarch). It is not built yet.

## How the pieces connect

- `contracts/openapi.json` is the API contract.
  - After changing a backend schema, run
    `uv run python scripts/export_openapi.py` (in `backend/`).
  - Then run `npm run generate:api` (in `web/`).
  - CI fails when either is stale.
- `config/targets.yaml` lists every catalogue and digital source. The
  backend validates it at startup.
- The root `Dockerfile` builds one image from `backend/` (no tests), the
  `web/` static export and `config/`. Never `COPY . .`; `mobile/` stays out
  through `.dockerignore`.
- The app is read-only towards BIBLIO.NET: it only produces ISO 2709 files.
  Never add code that writes to a library system.
- Searches are live. The SQLite cache is a short-lived optimisation, not a
  data source.

## Done when

- `backend/`: ruff format/check, `mypy src tests`, `lint-imports` and
  `pytest` all pass.
- `web/`: `typecheck`, `lint` and `build` pass.
- `docker build .` succeeds.

## After every change, tell the user

What changed, what happens now when it runs, the concepts used (with
links), and how to see it.
