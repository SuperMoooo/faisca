"""What other modules may use from records: the MARC/UNIMARC toolkit.

This module has no tables and no endpoints. It turns MARCXML from any target
into one UNIMARC record (converting MARC21 on the way), describes it, groups
duplicates and writes ISO 2709 files.
"""

from dataclasses import dataclass
from functools import cached_property

from pymarc import Record

from faisca.modules.records.dedup import group_duplicates, work_key
from faisca.modules.records.iso2709 import record_to_iso2709, records_to_iso2709
from faisca.modules.records.marc21_to_unimarc import convert_marc21_to_unimarc
from faisca.modules.records.marcxml import MarcXmlError, parse_marcxml, to_marcxml
from faisca.modules.records.schemas import (
    BibliographicDescription,
    MarcFieldView,
    MarcFormat,
    MarcRecordView,
    MarcSubfieldView,
)
from faisca.modules.records.unimarc import (
    control_number,
    declare_unicode,
    describe,
    detect_format,
    record_view,
)

__all__ = [
    "BibliographicDescription",
    "CatalogueRecord",
    "MarcFieldView",
    "MarcFormat",
    "MarcRecordView",
    "MarcSubfieldView",
    "MarcXmlError",
    "group_duplicates",
    "read_catalogue_record",
    "record_from_marcxml",
    "records_to_iso2709",
    "work_key",
]


@dataclass(frozen=True)
class CatalogueRecord:
    """One record as a target sent it, and its UNIMARC form (the same object if it was UNIMARC)."""

    source_format: MarcFormat
    original: Record
    unimarc: Record

    # cached_property writes to the instance __dict__ directly, so it works on
    # a frozen dataclass; dedup and the summaries read it several times.
    @cached_property
    def description(self) -> BibliographicDescription:
        """Title, authors, ISBNs…, read from the UNIMARC form."""
        return describe(self.unimarc)

    @property
    def control_number(self) -> str | None:
        """001 of the original record, its id in the source catalogue."""
        return control_number(self.original)

    def unimarc_view(self) -> MarcRecordView:
        """The UNIMARC record as tag / indicators / subfields."""
        return record_view(self.unimarc, MarcFormat.UNIMARC)

    def original_view(self) -> MarcRecordView | None:
        """The MARC21 record it was converted from, or None for a native UNIMARC record."""
        if self.source_format is MarcFormat.UNIMARC:
            return None
        return record_view(self.original, self.source_format)

    def unimarc_iso2709(self) -> bytes:
        """The UNIMARC record as an ISO 2709 file, in UTF-8."""
        return record_to_iso2709(self.unimarc)

    def original_iso2709(self) -> bytes:
        """The record as the target sent it, as an ISO 2709 file, in UTF-8."""
        return record_to_iso2709(self.original)

    def original_marcxml(self) -> str:
        """The original record as MARCXML; how it is cached."""
        return to_marcxml(self.original)


def read_catalogue_record(
    marcxml: str | bytes, declared_format: MarcFormat | None = None
) -> CatalogueRecord:
    """Parses a target's MARCXML and makes the UNIMARC form, converting MARC21 when needed.

    The format is read from the record itself; [declared_format] (from the
    target's config) only decides when the record gives no clear sign.
    """
    original = parse_marcxml(marcxml)
    source_format = _resolve_format(original, declared_format)
    if source_format is MarcFormat.MARC21:
        unimarc = convert_marc21_to_unimarc(original)
    else:
        unimarc = parse_marcxml(to_marcxml(original))  # a copy, so the original stays untouched
        declare_unicode(unimarc)
    return CatalogueRecord(source_format=source_format, original=original, unimarc=unimarc)


def record_from_marcxml(marcxml: str | bytes) -> Record:
    """A pymarc Record from MARCXML, for code that only needs the raw record."""
    return parse_marcxml(marcxml)


def _resolve_format(record: Record, declared_format: MarcFormat | None) -> MarcFormat:
    detected = detect_format(record)
    has_title_tag = bool(record.get_fields("200") or record.get_fields("245"))
    if has_title_tag or declared_format is None:
        return detected
    return declared_format
