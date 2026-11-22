"""Builds the catalogue service for each request: session, targets, searcher → service."""

from typing import Annotated

from fastapi import Depends, Request

from faisca.core.config import Settings
from faisca.core.http import HttpClientDep
from faisca.core.politeness import ThrottlesDep
from faisca.db.session import SessionDep
from faisca.modules.catalogues.mocks import CatalogueMockService
from faisca.modules.catalogues.searcher import LiveTargetSearcher, TargetSearcher
from faisca.modules.catalogues.service import CatalogueService
from faisca.modules.targets.public import TargetsConfigDep


def get_target_searcher(http_client: HttpClientDep, throttles: ThrottlesDep) -> TargetSearcher:
    """The live searcher; tests replace this dependency with a fake one."""
    return LiveTargetSearcher(http_client, throttles)


TargetSearcherDep = Annotated[TargetSearcher, Depends(get_target_searcher)]


def get_catalogue_service(
    session: SessionDep, config: TargetsConfigDep, searcher: TargetSearcherDep, request: Request
) -> CatalogueService:
    """The real service, or the mock one with `MOCK_RESPONSES=true`."""
    settings: Settings = request.app.state.settings
    if settings.mock_responses:
        return CatalogueMockService(config, settings)
    return CatalogueService(session, config, searcher, settings)


CatalogueServiceDep = Annotated[CatalogueService, Depends(get_catalogue_service)]
