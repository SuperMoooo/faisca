# syntax=docker/dockerfile:1
#
# Faísca in one image: the FastAPI backend, the exported Next.js web app it
# serves at "/", and config/targets.yaml. Three stages:
#   web-build      Node builds web/ into static files (web/out)
#   backend-build  uv installs the backend and its dependencies into a venv
#   runtime        slim Python + libyaz5 (Z39.50) + the two results + config/
# Folders are copied one by one, never `COPY . .`: mobile/, the tests and the
# dev tooling never reach the image (see also .dockerignore).

# ── web-build ────────────────────────────────────────────────────────────
FROM node:22-slim AS web-build
WORKDIR /build/web

# Dependencies first, from the lock file alone: rebuilt only when it changes.
COPY web/package.json web/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

COPY web/next.config.ts web/tsconfig.json web/postcss.config.mjs* web/eslint.config.mjs web/next-env.d.ts ./
COPY web/public ./public
COPY web/src ./src
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── backend-build ────────────────────────────────────────────────────────
FROM python:3.12-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:0.12.11 /uv /uvx /bin/

# Bytecode compiled at build time: the container starts faster.
# copy mode: the cache is a mount, so hard links into it would dangle.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app/backend
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/uv.lock,target=uv.lock \
    --mount=type=bind,source=backend/pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
COPY backend/src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ── runtime ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# libyaz5: YAZ's ZOOM library, which the Z39.50 client calls through ctypes.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libyaz5 \
    && rm -rf /var/lib/apt/lists/*

# A user without root rights: a compromised process cannot change the image.
RUN groupadd --system app && useradd --system --gid app --no-create-home app
# The SQLite file (cache + basket) lives here; compose mounts a volume over it.
RUN mkdir /data && chown app:app /data

WORKDIR /app/backend
COPY --from=backend-build --chown=app:app /app/backend/.venv /app/backend/.venv
COPY --chown=app:app backend/alembic.ini /app/backend/alembic.ini
COPY --chown=app:app backend/migrations /app/backend/migrations
COPY --from=web-build --chown=app:app /build/web/out /app/web/out
COPY --chown=app:app config /app/config

ENV PATH="/app/backend/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    DATABASE_URL=sqlite+aiosqlite:////data/faisca.db \
    TARGETS_FILE=/app/config/targets.yaml \
    WEB_DIST_DIR=/app/web/out

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]

# Migrate first, then serve: the app never starts against an old schema.
# --proxy-headers: behind Caddy/nginx (HTTPS), trust X-Forwarded-* for the
# client's address and scheme.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn faisca.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]
