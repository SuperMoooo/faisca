"""Reads config/targets.yaml into validated settings, once at startup."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from faisca.modules.targets.schemas import TargetsConfig


class TargetsFileError(RuntimeError):
    """targets.yaml is missing or invalid; the app refuses to start without it."""


def load_targets(path: Path) -> TargetsConfig:
    """The targets in [path], or TargetsFileError naming what is wrong."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TargetsFileError(f"Targets file not found: {path}. Set TARGETS_FILE.") from error
    except yaml.YAMLError as error:
        raise TargetsFileError(f"{path} is not valid YAML: {error}") from error
    try:
        return TargetsConfig.model_validate(raw)
    except ValidationError as error:
        raise TargetsFileError(f"{path} has invalid targets:\n{error}") from error
