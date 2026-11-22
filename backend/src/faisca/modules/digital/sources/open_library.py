"""Open Library search, keeping the works that have an e-book.

Docs: https://openlibrary.org/dev/docs/api/search ("ebook_access" says how
the e-book can be read: public, borrowable, printdisabled, no_ebook).
"""

from typing import Any

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import SourceContext, first_text, text_list, year_from

MAX_RESULTS = 20
FIELDS = "key,title,author_name,first_publish_year,ebook_access,ia,cover_i"
ACCESS_BY_EBOOK_STATUS = {
    "public": AccessType.FREE,
    "borrowable": AccessType.RESTRICTED,
    "printdisabled": AccessType.RESTRICTED,
}


async def search_open_library(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """Open Library works matching [query] that can be read or borrowed online."""
    params = {"fields": FIELDS, "limit": str(MAX_RESULTS)}
    if query.title:
        params["title"] = query.title
    if query.author:
        params["author"] = query.author
    if query.isbn:
        params["isbn"] = query.isbn
    payload = await context.get_json(context.source.url, params)
    copies = []
    for document in payload.get("docs", []):
        access = ACCESS_BY_EBOOK_STATUS.get(str(document.get("ebook_access", "")))
        if access is None:
            continue
        if query.year and str(document.get("first_publish_year", "")) != query.year:
            continue
        copies.append(_copy(context, document, access))
    return copies


def _copy(context: SourceContext, document: dict[str, Any], access: AccessType) -> DigitalCopy:
    scans = text_list(document.get("ia"))
    work_url = f"https://openlibrary.org{document.get('key', '')}"
    # A public-domain scan opens straight on archive.org; a lending copy is
    # borrowed from the Open Library page.
    url = (
        f"https://archive.org/details/{scans[0]}"
        if access is AccessType.FREE and scans
        else work_url
    )
    cover_id = document.get("cover_i")
    return DigitalCopy(
        source_id=context.source.id,
        source_name=context.source.name,
        title=first_text(document.get("title")) or "[sem título]",
        authors=text_list(document.get("author_name")),
        year=year_from(document.get("first_publish_year")),
        access=access,
        url=url,
        thumbnail_url=f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None,
    )
