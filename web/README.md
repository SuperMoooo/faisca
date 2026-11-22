# Faísca web

The Portuguese (pt-PT) web interface: Next.js App Router, TypeScript,
Tailwind CSS 4, TanStack Query. `next build` makes a static export
(`out/`) that the FastAPI backend serves at `/`. There is no Node server in
production. The user documentation is the [root README](../README.md).

## Run

```bash
npm install
npm run dev          # http://localhost:3000, proxies /api to FastAPI on 127.0.0.1:8000
```

## Layout

```text
src/
├── app/                 routes: / (search), /registo, /comparar, /cesto, /definicoes, manifest
├── components/          search/, records/ (MARC display, compare), basket/, settings/
└── lib/
    ├── api/schema.d.ts  generated from ../contracts/openapi.json (npm run generate:api)
    ├── api/client.ts    typed openapi-fetch client and type aliases
    ├── api/queries.ts   one TanStack Query hook per endpoint
    ├── labels.ts        every Portuguese label for an API value
    └── search-params.ts the search lives in the URL
public/                  sw.js (service worker), icons
```

Pages that read the URL (`useSearchParams`) render inside a `<Suspense>`
boundary, as a static export requires.

## Checks

```bash
npm run generate:api   # after the backend contract changes
npm run typecheck
npm run lint
npm run build
```
