"""HTTP endpoints for targets: the configured list, and a live reachability check."""

from fastapi import APIRouter

from faisca.modules.targets.dependencies import TargetServiceDep
from faisca.modules.targets.schemas import TargetList, TargetStatusList

router = APIRouter(prefix="/targets", tags=["Targets"])


@router.get("")
async def list_targets(service: TargetServiceDep) -> TargetList:
    """Every catalogue and digital-copy source in config/targets.yaml."""
    return await service.list_targets()


@router.get("/status")
async def check_targets(service: TargetServiceDep) -> TargetStatusList:
    """Contacts every enabled target now and reports which answer (takes up to ~8 s)."""
    return await service.check_all()
