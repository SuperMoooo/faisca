"""The shapes a bibliographic record takes in the API: a readable description and a tag view."""

from enum import StrEnum

from pydantic import BaseModel, Field


class MarcFormat(StrEnum):
    """The MARC format a record is encoded in."""

    UNIMARC = "unimarc"
    MARC21 = "marc21"


class MarcSubfieldView(BaseModel):
    """One subfield: its code and value (`$a Os Lusíadas`)."""

    code: str
    value: str


class MarcFieldView(BaseModel):
    """One field as a cataloguer reads it: tag, indicators, subfields (or data for 00X)."""

    tag: str
    indicator1: str | None = Field(default=None, description="Null for control fields.")
    indicator2: str | None = Field(default=None, description="Null for control fields.")
    data: str | None = Field(default=None, description="Control fields (001-009) only.")
    subfields: list[MarcSubfieldView] = []


class MarcRecordView(BaseModel):
    """A whole record as tag / indicators / subfields, in the format named by `format`."""

    format: MarcFormat
    leader: str
    fields: list[MarcFieldView]


class BibliographicDescription(BaseModel):
    """What the results table and compare view show, read from the UNIMARC record."""

    title: str
    other_title_information: str | None = None
    responsibility: str | None = None
    authors: list[str] = []
    edition: str | None = None
    place_of_publication: str | None = None
    publisher: str | None = None
    year: str | None = Field(default=None, description="Four digits when known.")
    physical_description: str | None = None
    series: str | None = None
    isbns: list[str] = Field(default=[], description="Normalised to ISBN-13.")
    languages: list[str] = []
    subjects: list[str] = []
    notes: list[str] = []
    digital_links: list[str] = Field(default=[], description="URLs from 856 $u.")
