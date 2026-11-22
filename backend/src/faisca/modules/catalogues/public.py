"""What other modules may use from catalogues.

- `SearchQuery`: the search form, shared with the digital-copy search.
- `search_catalogue_target`: one target's records for a query, uncached
  (the BND adapter searches the BNP catalogue for purl.pt links with it).
- `find_record_for_export`: a record found by a search, ready for the basket.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from faisca.core.config import Settings
from faisca.modules.catalogues.dependencies import TargetSearcherDep
from faisca.modules.catalogues.record_ids import make_record_id
from faisca.modules.catalogues.schemas import RecordSummary, SearchQuery
from faisca.modules.catalogues.searcher import TargetSearcher
from faisca.modules.catalogues.service import CatalogueService, FoundRecord, summarize_record
from faisca.modules.records.public import read_catalogue_record
from faisca.modules.targets.public import CatalogueTarget, TargetsConfig

__all__ = [
    "ExportableRecord",
    "RecordSummary",
    "SearchQuery",
    "TargetSearcher",
    "TargetSearcherDep",
    "find_record_for_export",
    "search_catalogue_target",
]


@dataclass(frozen=True)
class ExportableRecord:
    """A record's summary and its UNIMARC form as MARCXML and ISO 2709."""

    summary: RecordSummary
    unimarc_iso2709: bytes


async def search_catalogue_target(
    searcher: TargetSearcher, target: CatalogueTarget, query: SearchQuery, max_records: int
) -> list[RecordSummary]:
    """[target]'s records for [query], as summaries. Raises what the protocol raises."""
    result = await searcher.search(target, query, max_records)
    summaries: list[RecordSummary] = []
    for marcxml in result.marcxml_records:
        record = read_catalogue_record(marcxml, target.format)
        record_id = make_record_id(target.id, record.control_number, marcxml)
        summaries.append(summarize_record(record_id, target, record))
    return summaries


async def find_record_for_export(
    session: AsyncSession,
    config: TargetsConfig,
    searcher: TargetSearcher,
    settings: Settings,
    record_id: str,
) -> ExportableRecord:
    """The record with this id (cache, else its target), or NotFoundError. Never commits."""
    found: FoundRecord = await CatalogueService(session, config, searcher, settings).find_record(
        record_id
    )
    return ExportableRecord(summary=found.summary(), unimarc_iso2709=found.record.unimarc_iso2709())
