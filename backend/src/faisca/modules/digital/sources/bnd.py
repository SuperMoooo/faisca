"""Biblioteca Nacional Digital (BNP), searched live through the BNP catalogue.

BND has no search API: OAI-PMH (set "bndlivre") only serves bulk harvesting,
and the portal (bndigital.bnportugal.gov.pt) returns HTML. Its digitised
books are, however, catalogued in the BNP catalogue with an 856 $u pointing
to purl.pt (856 4 0 the copy, 856 4 1 its cover). So the catalogue is
searched over Z39.50 and the records with a purl.pt link are the BND copies.
"""

from faisca.modules.catalogues.public import SearchQuery, search_catalogue_target
from faisca.modules.digital.schemas import AccessType, DigitalCopy
from faisca.modules.digital.sources.common import SourceContext, SourceSkippedError

# More records than a normal catalogue search: only some of them are digitised.
RECORDS_TO_SCAN = 50
PURL_HOST = "purl.pt/"
COVER_PATH = "/service/media/cover/"


async def search_bnd(context: SourceContext, query: SearchQuery) -> list[DigitalCopy]:
    """BNP catalogue records for [query] that link to a BND copy on purl.pt."""
    target_id = context.source.catalogue_target
    target = context.targets.catalogue(target_id) if target_id else None
    if target is None:
        raise SourceSkippedError("Falta `catalogue_target` (o catálogo da BNP) em targets.yaml.")
    summaries = await search_catalogue_target(
        context.catalogue_searcher, target, query, RECORDS_TO_SCAN
    )

    copies: list[DigitalCopy] = []
    for summary in summaries:
        purl_links = [link for link in summary.description.digital_links if PURL_HOST in link]
        copy_links = [link for link in purl_links if COVER_PATH not in link]
        if not copy_links:
            continue
        cover = next((link for link in purl_links if COVER_PATH in link), None)
        copies.append(
            DigitalCopy(
                source_id=context.source.id,
                source_name=context.source.name,
                title=summary.description.title,
                authors=summary.description.authors,
                year=summary.description.year,
                # BND copies are open to everyone online.
                access=AccessType.FREE,
                url=copy_links[0],
                thumbnail_url=cover,
                provider="Biblioteca Nacional de Portugal",
                catalogue_record_id=summary.id,
            )
        )
    return copies
