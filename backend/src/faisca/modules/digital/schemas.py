"""What the digital-copy search returns. A stable contract for the web and Flutter clients."""

from enum import StrEnum

from pydantic import BaseModel, Field

from faisca.modules.catalogues.public import SearchQuery


class AccessType(StrEnum):
    """Whether anyone can read the copy online."""

    FREE = "free"
    # Lending, search-only, in-copyright or a login: the copy exists, but not open.
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class DigitalCopy(BaseModel):
    """One digitised book found in one source."""

    source_id: str
    source_name: str
    title: str
    authors: list[str] = []
    year: str | None = None
    access: AccessType
    url: str = Field(description="Opens the copy, or its page at the source.")
    thumbnail_url: str | None = None
    provider: str | None = Field(
        default=None, description="The institution that holds it (Europeana)."
    )
    catalogue_record_id: str | None = Field(
        default=None, description="A catalogue record id (BND copies come from the BNP catalogue)."
    )


class SourceSearchStatus(StrEnum):
    """How the search went on one source."""

    OK = "ok"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    # Not searched: it needs an API key, or an ISBN (HathiTrust), that is missing.
    SKIPPED = "skipped"


class SourceOutcome(BaseModel):
    """One source's part of a search."""

    source_id: str
    source_name: str
    status: SourceSearchStatus
    found_count: int = 0
    elapsed_ms: int | None = None
    from_cache: bool = False
    error: str | None = None


class DigitalSearchResponse(BaseModel):
    """Every copy found, in targets.yaml source order, and how each source did."""

    query: SearchQuery
    copies: list[DigitalCopy]
    sources: list[SourceOutcome]
