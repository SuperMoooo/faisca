"""Google Books, limited to free e-books (`filter=free-ebooks`).

Docs: https://developers.google.com/books/docs/v1/using. Without
GOOGLE_BOOKS_API_KEY the requests share Google's anonymous quota, which is
often exhausted (HTTP 429).
"""

from typing import Any

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import SourceContext, query_words, year_from

MAX_RESULTS = 20


async def search_google_books(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """Free Google Books e-books matching [query]."""
    params = {
        "q": _google_query(query),
        "filter": "free-ebooks",
        "maxResults": str(MAX_RESULTS),
        "printType": "books",
    }
    if context.settings.google_books_api_key:
        params["key"] = context.settings.google_books_api_key
    payload = await context.get_json(context.source.url, params)
    copies = [_copy(context, volume) for volume in payload.get("items", [])]
    if query.year:
        copies = [copy for copy in copies if copy.year == query.year]
    return copies


def _google_query(query: SearchQuery) -> str:
    terms: list[str] = []
    if query.title:
        terms += [f"intitle:{word}" for word in query_words(query.title)]
    if query.author:
        terms += [f"inauthor:{word}" for word in query_words(query.author)]
    if query.isbn:
        terms.append(f"isbn:{query.isbn}")
    return " ".join(terms)


def _copy(context: SourceContext, volume: dict[str, Any]) -> DigitalCopy:
    info: dict[str, Any] = volume.get("volumeInfo", {})
    access_info: dict[str, Any] = volume.get("accessInfo", {})
    title = str(info.get("title", "[sem título]"))
    if info.get("subtitle"):
        title = f"{title} : {info['subtitle']}"
    thumbnail = info.get("imageLinks", {}).get("thumbnail")
    return DigitalCopy(
        source_id=context.source.id,
        source_name=context.source.name,
        title=title,
        authors=[str(author) for author in info.get("authors", [])],
        year=year_from(info.get("publishedDate")),
        access=AccessType.FREE,
        url=str(
            access_info.get("webReaderLink") or info.get("previewLink") or info.get("infoLink", "")
        ),
        # Google returns http:// thumbnails; the page is served over https.
        thumbnail_url=str(thumbnail).replace("http://", "https://") if thumbnail else None,
    )
