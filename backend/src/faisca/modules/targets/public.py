"""What other modules may use from targets: the configuration and its dependency."""

from faisca.modules.targets.dependencies import TargetsConfigDep, get_targets_config
from faisca.modules.targets.loader import TargetsFileError, load_targets
from faisca.modules.targets.schemas import (
    CatalogueProtocol,
    CatalogueTarget,
    DigitalSource,
    DigitalSourceKind,
    SruIndexes,
    TargetsConfig,
)

__all__ = [
    "CatalogueProtocol",
    "CatalogueTarget",
    "DigitalSource",
    "DigitalSourceKind",
    "SruIndexes",
    "TargetsConfig",
    "TargetsConfigDep",
    "TargetsFileError",
    "get_targets_config",
    "load_targets",
]
