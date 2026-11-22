"""Gallica (BnF) SRU: digitised documents, described in Dublin Core.

Docs: https://api.bnf.fr/fr/api-gallica-de-recherche. Disabled in
targets.yaml while Cloudflare blocks the development network.
"""

from lxml import etree

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import SourceContext, query_words, year_from

MAX_RECORDS = 20
_PARSER = etree.XMLParser(recover=True, no_network=True, resolve_entities=False)


async def search_gallica(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """Gallica documents matching [query]."""
    params = {
        "operation": "searchRetrieve",
        "version": "1.2",
        "query": _gallica_query(query),
        "maximumRecords": str(MAX_RECORDS),
    }
    content = await context.get_bytes(context.source.url, params)
    return parse_gallica_response(context, content)


def _gallica_query(query: SearchQuery) -> str:
    clauses: list[str] = []
    if query.title:
        clauses.append('dc.title all "' + " ".join(query_words(query.title)) + '"')
    if query.author:
        clauses.append('dc.creator all "' + " ".join(query_words(query.author)) + '"')
    if query.isbn:
        clauses.append(f'dc.identifier all "{query.isbn}"')
    if query.year:
        clauses.append(f'gallicapublication_date="{query.year}"')
    return " and ".join(clauses)


def parse_gallica_response(context: SourceContext, content: bytes) -> list[DigitalCopy]:
    """One copy per Dublin Core record that has a Gallica ark: URL."""
    root = etree.fromstring(content, _PARSER)
    if root is None:
        return []
    copies = []
    for record in root.iter("{*}dc"):
        identifiers = [
            text for text in _texts(record, "identifier") if "gallica.bnf.fr/ark:" in text
        ]
        if not identifiers:
            continue
        titles = _texts(record, "title")
        copies.append(
            DigitalCopy(
                source_id=context.source.id,
                source_name=context.source.name,
                title=titles[0] if titles else "[sans titre]",
                authors=_texts(record, "creator"),
                year=year_from(_texts(record, "date")),
                access=AccessType.FREE,
                url=identifiers[0],
                thumbnail_url=f"{identifiers[0]}.thumbnail",
                provider="Bibliothèque nationale de France",
            )
        )
    return copies


def _texts(record: etree._Element, local_name: str) -> list[str]:
    return [
        (element.text or "").strip()
        for element in record.iter(f"{{*}}{local_name}")
        if (element.text or "").strip()
    ]
