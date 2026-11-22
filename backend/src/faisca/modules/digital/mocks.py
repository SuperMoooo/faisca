"""Sample digital copies for `MOCK_RESPONSES=true`: no network, no database."""

from faisca.core.config import Settings
from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.schemas import (
    AccessType,
    DigitalCopy,
    DigitalSearchResponse,
    SourceOutcome,
    SourceSearchStatus,
)
from faisca.modules.digital.service import DigitalSearchService
from faisca.modules.targets.public import TargetsConfig


def sample_copies() -> list[DigitalCopy]:
    """A free BND copy, a free Internet Archive scan, and an Open Library loan."""
    return [
        DigitalCopy(
            source_id="bnd",
            source_name="Biblioteca Nacional Digital (BNP)",
            title="Os Lusíadas",
            authors=["Camões, Luís de, 1524?-1580"],
            year="1572",
            access=AccessType.FREE,
            url="https://purl.pt/1",
            thumbnail_url="https://purl.pt/1/service/media/cover/low",
            provider="Biblioteca Nacional de Portugal",
        ),
        DigitalCopy(
            source_id="internet-archive",
            source_name="Internet Archive",
            title="Os Lusiadas : poema epico",
            authors=["Camões, Luís de"],
            year="1880",
            access=AccessType.FREE,
            url="https://archive.org/details/oslusiadaspoemae00camo_0",
            thumbnail_url="https://archive.org/services/img/oslusiadaspoemae00camo_0",
        ),
        DigitalCopy(
            source_id="open-library",
            source_name="Open Library",
            title="Os Lusíadas",
            authors=["Luís de Camões"],
            year="1981",
            access=AccessType.RESTRICTED,
            url="https://openlibrary.org/works/OL1W",
        ),
    ]


class DigitalSearchMockService(DigitalSearchService):
    """Answers like DigitalSearchService from the samples; Europeana is skipped (no key)."""

    def __init__(self, config: TargetsConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings

    async def search(self, query: SearchQuery) -> DigitalSearchResponse:
        """The three samples and one skipped source."""
        copies = sample_copies()
        counts = {copy.source_id: 0 for copy in copies}
        for copy in copies:
            counts[copy.source_id] += 1
        names = {copy.source_id: copy.source_name for copy in copies}
        sources = [
            SourceOutcome(
                source_id=source_id,
                source_name=names[source_id],
                status=SourceSearchStatus.OK,
                found_count=count,
                elapsed_ms=600,
            )
            for source_id, count in counts.items()
        ]
        sources.append(
            SourceOutcome(
                source_id="europeana",
                source_name="Europeana",
                status=SourceSearchStatus.SKIPPED,
                error="Falta EUROPEANA_API_KEY (gratuita em pro.europeana.eu).",
            )
        )
        return DigitalSearchResponse(query=query, copies=copies, sources=sources)
