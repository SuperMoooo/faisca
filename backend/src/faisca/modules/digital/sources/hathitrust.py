"""HathiTrust Bibliographic API: copies of a book, by ISBN only.

Docs: https://www.hathitrust.org/member-libraries/resources-for-librarians/data-resources/bibliographic-api/
Its full-text search sits behind Cloudflare and refuses programs, so a
search without an ISBN skips HathiTrust.
"""

from typing import Any

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import (
    SourceContext,
    SourceSkippedError,
    first_text,
    year_from,
)

FULL_VIEW = "Full view"


async def search_hathitrust(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """HathiTrust volumes of the book with [query]'s ISBN."""
    if not query.isbn:
        raise SourceSkippedError("O HathiTrust só pesquisa por ISBN.")
    payload = await context.get_json(f"{context.source.url}/isbn/{query.isbn}.json")
    records: dict[str, Any] = payload.get("records", {})
    return [
        _copy(context, item, records.get(str(item.get("fromRecord")), {}))
        for item in payload.get("items", [])
        if item.get("itemURL")
    ]


def _copy(context: SourceContext, item: dict[str, Any], record: dict[str, Any]) -> DigitalCopy:
    # usRightsString is "Full view" or "Limited (search-only)".
    is_full_view = item.get("usRightsString") == FULL_VIEW
    return DigitalCopy(
        source_id=context.source.id,
        source_name=context.source.name,
        title=first_text(record.get("titles")) or "[sem título]",
        year=year_from(record.get("publishDates")),
        access=AccessType.FREE if is_full_view else AccessType.RESTRICTED,
        url=str(item["itemURL"]),
        provider=str(item.get("orig")) if item.get("orig") else None,
    )
