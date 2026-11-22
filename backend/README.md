# Faísca backend

The FastAPI modular monolith behind Faísca: federated catalogue search
(Z39.50 + SRU), MARC21 → UNIMARC conversion, digital-copy search, the
export basket, and the exported web app served at `/`. Generated with
[moarch-py](https://pypi.org/project/moarch-py/); rules for changing it are
in [AGENTS.md](AGENTS.md). The user documentation (Portuguese) is the
[root README](../README.md).

## Run

```bash
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run fastapi dev src/faisca/main.py      # http://127.0.0.1:8000/docs
```

Z39.50 needs YAZ's shared library: `apt install libyaz5` (Debian/Ubuntu)
or `brew install yaz` (macOS). Without it, the Z39.50 targets report
`unavailable` and SRU targets still work. On Windows, use the root
`docker compose up --build`.

## Modules

| Module | Job | Tables |
| --- | --- | --- |
| `records` | UNIMARC helpers, MARC21 → UNIMARC, MARCXML, ISO 2709, dedup | none |
| `catalogues` | Federated search, Z39.50 client (`ctypes` over YAZ ZOOM), SRU client, record views | none (uses the cache) |
| `digital` | One adapter per digital-copy source | none (uses the cache) |
| `basket_items` | Export basket, ISO 2709 export | `basket_items` |
| `cached_responses` | 24 h response cache | `cached_responses` |
| `targets` | `config/targets.yaml`, reachability checks | none |

Modules import each other only through `public.py`; `uv run lint-imports`
enforces it.

## Checks

```bash
uv run ruff format . && uv run ruff check .
uv run mypy src tests
uv run lint-imports
uv run pytest
uv run python scripts/export_openapi.py     # after a schema change: updates contracts/openapi.json
```
