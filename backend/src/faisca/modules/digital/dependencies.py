"""Builds the digital-copy search service for each request, or its mock."""

from typing import Annotated

from fastapi import Depends, Request

from faisca.core.config import Settings
from faisca.core.http import HttpClientDep
from faisca.core.politeness import ThrottlesDep
from faisca.db.session import SessionDep
from faisca.modules.catalogues.public import TargetSearcherDep
from faisca.modules.digital.mocks import DigitalSearchMockService
from faisca.modules.digital.service import DigitalSearchService
from faisca.modules.targets.public import TargetsConfigDep


def get_digital_search_service(
    session: SessionDep,
    config: TargetsConfigDep,
    http_client: HttpClientDep,
    throttles: ThrottlesDep,
    catalogue_searcher: TargetSearcherDep,
    request: Request,
) -> DigitalSearchService:
    """The real service, or the mock one with `MOCK_RESPONSES=true`."""
    settings: Settings = request.app.state.settings
    if settings.mock_responses:
        return DigitalSearchMockService(config, settings)
    return DigitalSearchService(
        session, config, http_client, throttles, catalogue_searcher, settings
    )


DigitalSearchServiceDep = Annotated[DigitalSearchService, Depends(get_digital_search_service)]
