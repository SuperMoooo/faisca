"""Europeana Search API: digitised texts from Europe's libraries and archives.

Needs a free key (EUROPEANA_API_KEY). Docs: https://pro.europeana.eu/page/search
"""

from typing import Any

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import (
    SourceContext,
    SourceSkippedError,
    first_text,
    query_words,
    text_list,
    year_from,
)

MAX_ROWS = 20
# Rights statements that mean "anyone may read it": public domain and the
# Creative Commons licences.
OPEN_RIGHTS_MARKERS = ("publicdomain", "creativecommons.org/licenses")
CLOSED_RIGHTS_MARKERS = ("InC", "NoC-CR")


async def search_europeana(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """Europeana items of type TEXT matching [query]."""
    api_key = context.settings.europeana_api_key
    if not api_key:
        raise SourceSkippedError("Falta EUROPEANA_API_KEY (gratuita em pro.europeana.eu).")
    params = {
        "wskey": api_key,
        "query": _europeana_query(query),
        "rows": str(MAX_ROWS),
        "qf": "TYPE:TEXT",
    }
    if query.year:
        params["qf"] = f"TYPE:TEXT AND YEAR:{query.year}"
    payload = await context.get_json(context.source.url, params)
    return [_copy(context, item) for item in payload.get("items", []) if item.get("guid")]


def _europeana_query(query: SearchQuery) -> str:
    # Europeana's query language is Solr: field:(words) joined with AND.
    clauses: list[str] = []
    if query.title:
        clauses.append("title:(" + " AND ".join(query_words(query.title)) + ")")
    if query.author:
        clauses.append("who:(" + " AND ".join(query_words(query.author)) + ")")
    if query.isbn:
        clauses.append(f'"{query.isbn}"')
    return " AND ".join(clauses)


def _copy(context: SourceContext, item: dict[str, Any]) -> DigitalCopy:
    return DigitalCopy(
        source_id=context.source.id,
        source_name=context.source.name,
        title=first_text(item.get("title")) or "[sem título]",
        authors=[name for name in text_list(item.get("dcCreator")) if not name.startswith("http")],
        year=year_from(item.get("year")),
        access=_access(first_text(item.get("rights")) or ""),
        url=first_text(item.get("edmIsShownAt")) or str(item["guid"]),
        thumbnail_url=first_text(item.get("edmPreview")),
        provider=first_text(item.get("dataProvider")),
    )


def _access(rights_url: str) -> AccessType:
    if any(marker in rights_url for marker in OPEN_RIGHTS_MARKERS):
        return AccessType.FREE
    if any(marker in rights_url for marker in CLOSED_RIGHTS_MARKERS):
        return AccessType.RESTRICTED
    return AccessType.UNKNOWN
