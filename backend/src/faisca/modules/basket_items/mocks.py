"""A sample basket for `MOCK_RESPONSES=true`: one record, nothing stored.

When you add a column to the model or a method to the service, update this too.
"""

from datetime import UTC, datetime
from pathlib import Path

from faisca.core.errors import NotFoundError
from faisca.modules.basket_items.schemas import BasketItemRead, BasketRead
from faisca.modules.basket_items.service import BasketService, export_file_name
from faisca.modules.records.public import MarcFormat, record_from_marcxml, records_to_iso2709

# A fixed time, so responses never change between runs.
SAMPLE_TIME = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
SAMPLE_ITEM_ID = 1

SAMPLES_DIR = Path(__file__).parent / "samples"


def _read_sample(filename: str) -> str:
    """A sample MARCXML record shipped next to this module."""
    return (SAMPLES_DIR / filename).read_text(encoding="utf-8")


SAMPLE_RECORD = _read_sample("sample_unimarc.xml")


def sample_item() -> BasketItemRead:
    """The one record the sample basket holds."""
    return BasketItemRead(
        id=SAMPLE_ITEM_ID,
        record_id="porbase.nMTIzNDU2Nw",
        title="Os Lusíadas",
        authors=["Camões, Luís de"],
        year="2001",
        target_name="PORBASE — Base Nacional de Dados Bibliográficos",
        source_format=MarcFormat.UNIMARC,
        created_at=SAMPLE_TIME,
    )


class BasketMockService(BasketService):
    """Answers like BasketService from one sample record; changes are not kept."""

    def __init__(self) -> None:
        # No session and no repository: nothing here touches the database.
        pass

    async def get_basket(self) -> BasketRead:
        """The sample basket."""
        return BasketRead(items=[sample_item()], count=1)

    async def add(self, record_id: str) -> tuple[BasketItemRead, bool]:
        """The sample item, as if [record_id] had been added."""
        item = sample_item().model_copy(update={"id": SAMPLE_ITEM_ID + 1, "record_id": record_id})
        return item, True

    async def remove(self, item_id: int) -> None:
        """Succeeds for the sample's id and 404s for any other."""
        if item_id != SAMPLE_ITEM_ID:
            raise NotFoundError(f"O cesto não tem o item {item_id}.")

    async def clear(self) -> None:
        """Pretends to empty the basket."""

    async def export(self) -> tuple[str, bytes]:
        """The sample record as a real ISO 2709 file."""
        return export_file_name(SAMPLE_TIME), records_to_iso2709(
            [record_from_marcxml(SAMPLE_RECORD)]
        )
