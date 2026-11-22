"""The targets endpoints without the network, for `MOCK_RESPONSES=true`.

The list is the real targets.yaml (reading a file is not live data); the
reachability check answers "reachable" for every enabled target, so a client
can draw the settings page offline.
"""

from faisca.modules.targets.schemas import (
    Reachability,
    TargetsConfig,
    TargetStatus,
    TargetStatusList,
)
from faisca.modules.targets.service import TargetService

SAMPLE_LATENCY_MS = 120


class TargetMockService(TargetService):
    """Answers like TargetService, with every enabled target up."""

    def __init__(self, config: TargetsConfig) -> None:
        self.config = config

    async def check_all(self) -> TargetStatusList:
        """Every enabled target reachable in 120 ms; disabled ones disabled."""
        ids_and_flags = [(target.id, target.enabled) for target in self.config.catalogues]
        ids_and_flags += [(source.id, source.enabled) for source in self.config.digital_sources]
        return TargetStatusList(
            statuses=[
                TargetStatus(
                    id=target_id, reachability=Reachability.REACHABLE, latency_ms=SAMPLE_LATENCY_MS
                )
                if enabled
                else TargetStatus(id=target_id, reachability=Reachability.DISABLED)
                for target_id, enabled in ids_and_flags
            ]
        )
