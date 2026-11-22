"""HTTP endpoints for catalogue search and for the records it finds."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from faisca.modules.catalogues.dependencies import CatalogueServiceDep
from faisca.modules.catalogues.schemas import (
    CatalogueSearchResponse,
    RecordDetail,
    RecordVariant,
    SearchQuery,
)

router = APIRouter(tags=["Catalogues"])

# The registered media type for MARC records in ISO 2709 (RFC 2220).
MARC_MEDIA_TYPE = "application/marc"


@router.get("/catalogues/search")
async def search_catalogues(
    query: Annotated[SearchQuery, Query()], service: CatalogueServiceDep
) -> CatalogueSearchResponse:
    """Searches every enabled catalogue (or `targets`) at once; partial results if some fail."""
    return await service.search(query)


@router.get("/records/{record_id}")
async def get_record(record_id: str, service: CatalogueServiceDep) -> RecordDetail:
    """One record from a search, in UNIMARC, with the MARC21 original when converted."""
    return await service.get_record_detail(record_id)


@router.get(
    "/records/{record_id}/iso2709",
    response_class=Response,
    responses={200: {"content": {MARC_MEDIA_TYPE: {}}, "description": "An ISO 2709 file, UTF-8."}},
)
async def download_record(
    record_id: str, service: CatalogueServiceDep, variant: RecordVariant = RecordVariant.UNIMARC
) -> Response:
    """One record as an ISO 2709 file: UNIMARC (default) or the original as received."""
    filename, content = await service.get_record_file(record_id, variant)
    return Response(
        content=content,
        media_type=MARC_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
