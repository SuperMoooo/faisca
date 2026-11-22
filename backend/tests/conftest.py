"""Fixtures every test shares: an app on a fresh in-memory database, fixed targets, a fake searcher.

No test reaches the network: catalogue searches go through `FakeTargetSearcher`
(records read from tests/fixtures/records, captured live from the real
targets), and HTTP sources are mocked with respx.
"""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from faisca.core.config import Settings
from faisca.db.models import Base
from faisca.main import create_app
from faisca.modules.catalogues.dependencies import get_target_searcher
from tests.helpers import (
    REPOSITORY_ROOT,
    FakeTargetSearcher,
    build_test_targets,
    make_test_settings,
)


@pytest.fixture
def fake_searcher() -> FakeTargetSearcher:
    """The catalogue searcher every test app uses; tests fill in its results."""
    return FakeTargetSearcher()


@pytest.fixture
def settings() -> Settings:
    """The test settings; a test may replace this fixture to change one value."""
    return make_test_settings()


@pytest.fixture
async def app(settings: Settings, fake_searcher: FakeTargetSearcher) -> AsyncIterator[FastAPI]:
    """A new app per test, on its own empty in-memory SQLite database, with fixed targets.

    Tests never share rows, and need neither a database server nor the network.
    """
    test_app = create_app(settings, targets=build_test_targets())
    test_app.dependency_overrides[get_target_searcher] = lambda: fake_searcher
    async with test_app.state.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield test_app
    await test_app.state.http_client.aclose()
    await test_app.state.engine.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """Calls the app in-process, without a running server."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def session(app: FastAPI) -> AsyncIterator[AsyncSession]:
    """A session on the test database, for service and repository tests."""
    async with app.state.session_factory() as session:
        yield session


@pytest.fixture
async def mock_client() -> AsyncIterator[AsyncClient]:
    """Calls an app with `mock_responses` on, whose database has no tables at all.

    Any mocked endpoint that reached the database would fail here, which is
    how these tests prove that mock mode needs no data and no database.
    """
    mock_app = create_app(make_test_settings(mock_responses=True), targets=build_test_targets())
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
        yield client
    await mock_app.state.http_client.aclose()
    await mock_app.state.engine.dispose()


@pytest.fixture
def repository_targets_file() -> Path:
    """The real config/targets.yaml, to check that it stays valid."""
    return REPOSITORY_ROOT / "config" / "targets.yaml"
