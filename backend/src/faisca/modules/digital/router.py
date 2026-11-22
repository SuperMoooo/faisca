"""HTTP endpoint for the digital-copy search."""

from typing import Annotated

from fastapi import APIRouter, Query

from faisca.modules.catalogues.public import SearchQuery
from faisca.modules.digital.dependencies import DigitalSearchServiceDep
from faisca.modules.digital.schemas import DigitalSearchResponse

router = APIRouter(prefix="/digital", tags=["Digital copies"])


@router.get("/search")
async def search_digital_copies(
    query: Annotated[SearchQuery, Query()], service: DigitalSearchServiceDep
) -> DigitalSearchResponse:
    """Searches BND, Europeana, Internet Archive, Open Library, Google Books… at once."""
    return await service.search(query)
