"""Internet Archive advanced search: scanned books ("texts").

Docs: https://archive.org/advancedsearch.php (Solr syntax).
"""

from typing import Any

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import (
    SourceContext,
    first_text,
    query_words,
    text_list,
    year_from,
)

MAX_ROWS = 20
FIELDS = ("identifier", "title", "creator", "year", "date", "access-restricted-item")


async def search_internet_archive(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """Texts on archive.org matching [query]; lending-only ones are marked restricted."""
    params = {"q": _archive_query(query), "rows": str(MAX_ROWS), "output": "json"}
    # The API takes the field list as repeated fl[] parameters.
    field_params = "&".join(f"fl[]={field}" for field in FIELDS)
    payload = await context.get_json(f"{context.source.url}?{field_params}", params)
    documents = payload.get("response", {}).get("docs", [])
    return [_copy(context, document) for document in documents if document.get("identifier")]


def _archive_query(query: SearchQuery) -> str:
    clauses = ["mediatype:texts"]
    if query.title:
        clauses.append("title:(" + " AND ".join(query_words(query.title)) + ")")
    if query.author:
        clauses.append("creator:(" + " AND ".join(query_words(query.author)) + ")")
    if query.isbn:
        clauses.append(f"isbn:{query.isbn}")
    if query.year:
        clauses.append(f"year:{query.year}")
    return " AND ".join(clauses)


def _copy(context: SourceContext, document: dict[str, Any]) -> DigitalCopy:
    identifier = str(document["identifier"])
    # "access-restricted-item" marks books lent one reader at a time.
    is_lending_only = str(document.get("access-restricted-item", "false")).lower() == "true"
    return DigitalCopy(
        source_id=context.source.id,
        source_name=context.source.name,
        title=first_text(document.get("title")) or identifier,
        authors=text_list(document.get("creator")),
        year=year_from(document.get("year")) or year_from(document.get("date")),
        access=AccessType.RESTRICTED if is_lending_only else AccessType.FREE,
        url=f"https://archive.org/details/{identifier}",
        thumbnail_url=f"https://archive.org/services/img/{identifier}",
    )
