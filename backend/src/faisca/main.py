"""The FastAPI application: settings, database, targets, HTTP client, routers and web app."""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from faisca.api.health import router as health_router
from faisca.api.v1.router import api_router as api_v1_router
from faisca.core.config import APP_VERSION, Settings, get_settings
from faisca.core.errors import register_error_handlers
from faisca.core.http import create_http_client
from faisca.core.logging import configure_logging
from faisca.core.politeness import ThrottleRegistry
from faisca.core.web_app import ExportedWebApp
from faisca.db.session import create_engine, create_session_factory
from faisca.modules.cached_responses.public import purge_expired
from faisca.modules.targets.public import TargetsConfig, load_targets

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, targets: TargetsConfig | None = None) -> FastAPI:
    """Builds the app. Tests pass their own [settings] (in-memory database) and [targets]."""
    settings = settings or get_settings()
    configure_logging(settings)
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    http_client = create_http_client(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await _purge_expired_cache(session_factory)
        yield
        # Close pooled connections on shutdown, so neither the database nor
        # the external services are left holding them until they time out.
        await http_client.aclose()
        await engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        description="Pesquisa de registos bibliográficos (UNIMARC) e de cópias digitais.",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url=None,
    )
    # Built here, not in the lifespan, so tests that skip the lifespan
    # (httpx's ASGITransport) still get them.
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.http_client = http_client
    app.state.throttles = ThrottleRegistry(settings)
    app.state.targets = targets or load_targets(settings.targets_file)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    if settings.mock_responses:
        mark_responses_as_mocked(app)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    mount_web_app(app, settings)
    return app


def mount_web_app(app: FastAPI, settings: Settings) -> None:
    """Serves the exported Next.js site at "/", after every API route.

    Mounted last, because a mount at "/" would otherwise catch /api and /health.
    `html=True` serves `cesto/index.html` for `/cesto/` and `404.html` for
    anything unknown, which is how a Next.js static export expects to be hosted.
    """
    web_dist_dir = settings.web_dist_dir
    if web_dist_dir is None or not (web_dist_dir / "index.html").exists():
        logger.info("No exported web app at %s; serving the API only.", web_dist_dir)
        return
    app.mount("/", ExportedWebApp(directory=str(web_dist_dir)), name="web")


async def _purge_expired_cache(session_factory: async_sessionmaker[AsyncSession]) -> None:
    # The cache table only grows during a run; a restart is a good moment to
    # drop what expired. A missing table (migrations not run yet) is not fatal.
    try:
        async with session_factory() as session:
            removed = await purge_expired(session)
            await session.commit()
    except Exception:
        logger.warning("Could not purge the response cache (run `alembic upgrade head`?).")
        return
    logger.info("Purged %d expired cache entries.", removed)


def mark_responses_as_mocked(app: FastAPI) -> None:
    """Adds `X-Mock-Response: true` to every response, so no one takes sample data for real."""
    logger.warning(
        "MOCK_RESPONSES is on: modules answer from their samples, not the network or database."
    )

    @app.middleware("http")
    async def add_mock_header(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Mock-Response"] = "true"
        return response


app = create_app()
