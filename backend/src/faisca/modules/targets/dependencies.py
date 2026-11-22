"""Builds the targets service for each request, or its mock with `MOCK_RESPONSES=true`."""

from typing import Annotated

from fastapi import Depends, Request

from faisca.core.config import Settings
from faisca.core.http import HttpClientDep
from faisca.modules.targets.mocks import TargetMockService
from faisca.modules.targets.schemas import TargetsConfig
from faisca.modules.targets.service import TargetService


def get_targets_config(request: Request) -> TargetsConfig:
    """The targets loaded at startup (tests give the app their own)."""
    config: TargetsConfig = request.app.state.targets
    return config


TargetsConfigDep = Annotated[TargetsConfig, Depends(get_targets_config)]


def get_target_service(
    config: TargetsConfigDep, http_client: HttpClientDep, request: Request
) -> TargetService:
    """The real service, or the mock one that never touches the network."""
    settings: Settings = request.app.state.settings
    if settings.mock_responses:
        return TargetMockService(config)
    return TargetService(config, http_client)


TargetServiceDep = Annotated[TargetService, Depends(get_target_service)]
