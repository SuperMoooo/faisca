"""Builds the basket service for each request: session → repository → service."""

from typing import Annotated

from fastapi import Depends, Request

from faisca.core.config import Settings
from faisca.db.session import SessionDep
from faisca.modules.basket_items.mocks import BasketMockService
from faisca.modules.basket_items.repository import BasketItemRepository
from faisca.modules.basket_items.service import BasketService
from faisca.modules.catalogues.public import TargetSearcherDep
from faisca.modules.targets.public import TargetsConfigDep


def get_basket_service(
    session: SessionDep, config: TargetsConfigDep, searcher: TargetSearcherDep, request: Request
) -> BasketService:
    """The real service, or the mock one with `MOCK_RESPONSES=true`."""
    settings: Settings = request.app.state.settings
    if settings.mock_responses:
        return BasketMockService()
    return BasketService(session, BasketItemRepository(session), config, searcher, settings)


BasketServiceDep = Annotated[BasketService, Depends(get_basket_service)]
