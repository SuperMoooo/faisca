# mobile/

Reserved for the Faísca Flutter app. It is not built yet; this folder only
holds this file.

## How it fits in the repository

- **The app is a client of `/api/v1`.** It uses the same endpoints as the
  web app: catalogue search, digital search, records, basket, targets. It
  never talks to the catalogues directly.
- **The contract is `contracts/openapi.json`.** Generate the Dart client
  from it, for example with
  [openapi-generator](https://openapi-generator.tech/docs/generators/dart-dio)
  (`dart-dio`) or `swagger_parser`. Regenerate it whenever the file changes;
  CI keeps that file in step with the backend.
- **No login.** The API has no authentication: it is meant to run on the
  cataloguer's own computer or behind an access-controlled proxy (see the
  root README). Point the app at that base URL, for example a Tailscale
  address.
- **Offline development.** Run the backend with `MOCK_RESPONSES=true` to get
  stable sample responses (`X-Mock-Response: true`) with no network or
  database.
- **Excluded from the server image.** `mobile/` is listed in the root
  `.dockerignore`, so it is never even sent to `docker build`, and the
  `Dockerfile` copies only `backend/`, `web/` and `config/`.

## Starting the app

Scaffold it in this folder with the Flutter
[moarch](https://pub.dev/packages/moarch) CLI, the Flutter sibling of the
`moarch-py` that generated `backend/`:

```bash
cd mobile
moarch init
```

Add its own CI job next to the backend and web jobs in
`.github/workflows/ci.yml`.
