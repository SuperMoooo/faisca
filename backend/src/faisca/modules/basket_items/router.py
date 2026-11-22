"""HTTP endpoints for the export basket."""

from fastapi import APIRouter, Response, status

from faisca.modules.basket_items.dependencies import BasketServiceDep
from faisca.modules.basket_items.schemas import BasketItemCreate, BasketItemRead, BasketRead

router = APIRouter(prefix="/basket", tags=["Basket"])

MARC_MEDIA_TYPE = "application/marc"


@router.get("")
async def get_basket(service: BasketServiceDep) -> BasketRead:
    """Every record in the basket, oldest first."""
    return await service.get_basket()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "The record was already in the basket."}},
)
async def add_to_basket(
    data: BasketItemCreate, service: BasketServiceDep, response: Response
) -> BasketItemRead:
    """Adds a record from a search; 201 if new, 200 if it was already there."""
    item, is_new = await service.add(data.record_id)
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_basket(item_id: int, service: BasketServiceDep) -> None:
    """Takes one record out of the basket."""
    await service.remove(item_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_basket(service: BasketServiceDep) -> None:
    """Empties the basket."""
    await service.clear()


@router.get(
    "/export",
    response_class=Response,
    responses={
        200: {"content": {MARC_MEDIA_TYPE: {}}, "description": "One ISO 2709 file, UNIMARC, UTF-8."}
    },
)
async def export_basket(service: BasketServiceDep) -> Response:
    """Every record in the basket as one UNIMARC ISO 2709 file (UTF-8), for BIBLIO.NET."""
    filename, content = await service.export()
    return Response(
        content=content,
        media_type=MARC_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
