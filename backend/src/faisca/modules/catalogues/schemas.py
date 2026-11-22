"""What the catalogue-search endpoints accept and return.

These shapes are the contract with the web app and the future Flutter app:
add optional fields freely, but never rename or remove one in /api/v1.
"""

import json
import re
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, field_validator, model_validator

from faisca.modules.records.public import BibliographicDescription, MarcFormat, MarcRecordView


class SearchQuery(BaseModel):
    """A search by title, author, ISBN and/or year; at least one of the first three."""

    title: str | None = Field(default=None, max_length=300)
    author: str | None = Field(default=None, max_length=200)
    isbn: str | None = Field(default=None, max_length=40)
    year: str | None = Field(default=None, pattern=r"^\d{4}$")
    targets: list[str] | None = Field(
        default=None, description="Target ids to search; all enabled targets when omitted."
    )

    @field_validator("title", "author", "isbn", "year", mode="before")
    @classmethod
    def blank_to_none(cls, value: object) -> object:
        """An empty form field means "not given", not "search for nothing"."""
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("isbn")
    @classmethod
    def keep_isbn_characters(cls, value: str | None) -> str | None:
        """Hyphens and spaces are how people type ISBNs; catalogues index the digits."""
        if not value:
            return None
        digits = re.sub(r"[^0-9Xx]", "", value).upper()
        return digits or None

    @model_validator(mode="after")
    def require_a_search_term(self) -> Self:
        """A year alone would match half a catalogue."""
        if not (self.title or self.author or self.isbn):
            raise ValueError("Indique pelo menos o título, o autor ou o ISBN.")
        return self

    def cache_fragment(self) -> str:
        """The query terms as canonical text, part of every cache key (targets excluded)."""
        terms = {"title": self.title, "author": self.author, "isbn": self.isbn, "year": self.year}
        return json.dumps(
            {key: (value or "").lower() for key, value in terms.items()}, sort_keys=True
        )


class TargetSearchStatus(StrEnum):
    """How the search went on one target."""

    OK = "ok"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    # Z39.50 needs libyaz on the server; without it Z39.50 targets are skipped.
    UNAVAILABLE = "unavailable"


class TargetOutcome(BaseModel):
    """One target's part of a search: so the UI can show partial results and what failed."""

    target_id: str
    target_name: str
    status: TargetSearchStatus
    hit_count: int | None = Field(default=None, description="Matches on the target.")
    returned_count: int = Field(default=0, description="Records fetched and shown.")
    elapsed_ms: int | None = None
    from_cache: bool = False
    error: str | None = None


class RecordSummary(BaseModel):
    """One record in the results: where it came from and its description."""

    id: str = Field(description="Stable for the cache's lifetime; use it to open or export.")
    target_id: str
    target_name: str
    country: str
    source_format: MarcFormat
    description: BibliographicDescription
    has_digital_copy: bool = Field(description="The record links to an online copy (856 $u).")


class RecordGroup(BaseModel):
    """Records of the same book from several targets, best source first."""

    key: str
    records: list[RecordSummary]


class CatalogueSearchResponse(BaseModel):
    """The merged, deduplicated results, and how each target did."""

    query: SearchQuery
    groups: list[RecordGroup]
    record_count: int
    targets: list[TargetOutcome]


class RecordDetail(BaseModel):
    """One record in UNIMARC, with the MARC21 original when it was converted."""

    summary: RecordSummary
    unimarc: MarcRecordView
    original: MarcRecordView | None = Field(
        default=None, description="The MARC21 record as received; null for native UNIMARC."
    )


class RecordVariant(StrEnum):
    """Which form of a record to download."""

    UNIMARC = "unimarc"
    ORIGINAL = "original"
