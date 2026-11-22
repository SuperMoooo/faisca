"""The shape of config/targets.yaml, and what the targets endpoints return."""

from datetime import date
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from faisca.modules.records.public import MarcFormat


class CatalogueProtocol(StrEnum):
    """How a catalogue is searched."""

    Z3950 = "z3950"
    SRU = "sru"


class SruIndexes(BaseModel):
    """The CQL index each search field maps to on one SRU server (they differ per server)."""

    title: str
    author: str
    isbn: str
    year: str | None = None
    # Used to fetch one record again by its 001 when the cache has expired.
    control_number: str | None = None


class CatalogueTarget(BaseModel):
    """One library catalogue from config/targets.yaml."""

    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2.")
    protocol: CatalogueProtocol
    format: MarcFormat
    enabled: bool = True
    verified_on: date | None = None
    notes: str | None = None
    timeout_seconds: int = Field(default=15, ge=1, le=60)

    # Z39.50
    host: str | None = None
    port: int | None = None
    database: str | None = None
    record_syntax: str = "unimarc"
    # The charset the server's MARC records are in; YAZ recodes it to UTF-8.
    charset: str = "utf-8"
    username: str | None = None
    password: str | None = None

    # SRU
    url: str | None = None
    sru_version: str = "1.2"
    record_schema: str | None = None
    # "=" on most servers; BnF needs "all" for a word search.
    relation: str = "="
    indexes: SruIndexes | None = None

    @model_validator(mode="after")
    def require_protocol_settings(self) -> Self:
        """A Z39.50 target needs host/port/database; an SRU one its URL, schema and indexes."""
        if self.protocol is CatalogueProtocol.Z3950:
            missing = [name for name in ("host", "port", "database") if getattr(self, name) is None]
        else:
            missing = [
                name for name in ("url", "record_schema", "indexes") if getattr(self, name) is None
            ]
        if missing:
            raise ValueError(f"Target {self.id}: {self.protocol} needs {', '.join(missing)}.")
        return self

    @property
    def endpoint(self) -> str:
        """Where it lives, for the settings page: host:port/database or the SRU URL."""
        if self.protocol is CatalogueProtocol.Z3950:
            return f"{self.host}:{self.port}/{self.database}"
        return self.url or ""


class DigitalSourceKind(StrEnum):
    """Which adapter searches a digital-copy source."""

    BND = "bnd"
    EUROPEANA = "europeana"
    INTERNET_ARCHIVE = "internet_archive"
    OPEN_LIBRARY = "open_library"
    GOOGLE_BOOKS = "google_books"
    GALLICA = "gallica"
    HATHITRUST = "hathitrust"


class DigitalSource(BaseModel):
    """One source of digital copies from config/targets.yaml."""

    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    kind: DigitalSourceKind
    url: str
    # Requested by the settings page to tell whether the service answers.
    check_url: str
    enabled: bool = True
    verified_on: date | None = None
    notes: str | None = None
    timeout_seconds: int = Field(default=15, ge=1, le=60)
    # BND: the catalogue target whose records link to purl.pt.
    catalogue_target: str | None = None


class TargetsConfig(BaseModel):
    """The whole of config/targets.yaml."""

    catalogues: list[CatalogueTarget]
    digital_sources: list[DigitalSource]

    @model_validator(mode="after")
    def require_unique_ids(self) -> Self:
        """Ids name targets in URLs, caches and record ids, so each must be unique."""
        ids = [target.id for target in self.catalogues] + [
            source.id for source in self.digital_sources
        ]
        duplicates = sorted({target_id for target_id in ids if ids.count(target_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate target ids in targets.yaml: {', '.join(duplicates)}.")
        return self

    def catalogue(self, target_id: str) -> CatalogueTarget | None:
        """The catalogue with this id, or None."""
        return next((target for target in self.catalogues if target.id == target_id), None)


class TargetKind(StrEnum):
    """Whether a target is a library catalogue or a source of digital copies."""

    CATALOGUE = "catalogue"
    DIGITAL = "digital"


class TargetRead(BaseModel):
    """One target as the API lists it; never its password."""

    id: str
    name: str
    kind: TargetKind
    country: str | None
    protocol: str = Field(description="z3950, sru, or the web API's name.")
    format: MarcFormat | None
    endpoint: str
    enabled: bool
    verified_on: date | None
    notes: str | None


class TargetList(BaseModel):
    """Every configured target, catalogues first."""

    catalogues: list[TargetRead]
    digital_sources: list[TargetRead]


class Reachability(StrEnum):
    """What a live check of one target found."""

    REACHABLE = "reachable"
    # It answers, but refuses us (HTTP 401/403/429): often an IP block.
    BLOCKED = "blocked"
    UNREACHABLE = "unreachable"
    DISABLED = "disabled"


class TargetStatus(BaseModel):
    """The result of checking one target live."""

    id: str
    reachability: Reachability
    latency_ms: int | None = None
    detail: str | None = None


class TargetStatusList(BaseModel):
    """The live check of every target, in the order of `TargetList`."""

    statuses: list[TargetStatus]
