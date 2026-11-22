"""The rules for the export basket: add a record once, remove, empty, export as one file."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from faisca.core.config import Settings
from faisca.core.errors import NotFoundError
from faisca.modules.basket_items.models import AUTHOR_SEPARATOR, BasketItem
from faisca.modules.basket_items.repository import BasketItemRepository
from faisca.modules.basket_items.schemas import BasketItemRead, BasketRead
from faisca.modules.catalogues.public import TargetSearcher, find_record_for_export
from faisca.modules.records.public import MarcFormat
from faisca.modules.targets.public import TargetsConfig


class BasketService:
    """Each public method is one unit of work: it commits when it succeeds."""

    def __init__(
        self,
        session: AsyncSession,
        repository: BasketItemRepository,
        config: TargetsConfig,
        searcher: TargetSearcher,
        settings: Settings,
    ) -> None:
        self.session = session
        self.repository = repository
        self.config = config
        self.searcher = searcher
        self.settings = settings

    async def get_basket(self) -> BasketRead:
        """Every record in the basket."""
        items = [_read(item) for item in await self.repository.list_all()]
        return BasketRead(items=items, count=len(items))

    async def add(self, record_id: str) -> tuple[BasketItemRead, bool]:
        """Adds the record (once); returns the item and whether it is new.

        Adding a record that is already there is not an error: the cataloguer
        may press "add" again from another search.
        """
        existing = await self.repository.find_by_record_id(record_id)
        if existing is not None:
            return _read(existing), False
        record = await find_record_for_export(
            self.session, self.config, self.searcher, self.settings, record_id
        )
        description = record.summary.description
        item = await self.repository.add(
            BasketItem(
                record_id=record_id,
                title=description.title,
                authors=AUTHOR_SEPARATOR.join(description.authors),
                year=description.year,
                target_name=record.summary.target_name,
                source_format=record.summary.source_format.value,
                unimarc_iso2709=record.unimarc_iso2709,
            )
        )
        await self.session.commit()
        return _read(item), True

    async def remove(self, item_id: int) -> None:
        """Takes one record out, or NotFoundError if it is not there."""
        item = await self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError(f"O cesto não tem o item {item_id}.")
        await self.repository.delete(item)
        await self.session.commit()

    async def clear(self) -> None:
        """Empties the basket."""
        await self.repository.delete_all()
        await self.session.commit()

    async def export(self) -> tuple[str, bytes]:
        """Every record as one ISO 2709 file (UTF-8 UNIMARC), and its file name."""
        items = await self.repository.list_all()
        if not items:
            raise NotFoundError("O cesto está vazio.")
        # ISO 2709 records are self-delimiting, so a file of many records is
        # the records written one after another.
        content = b"".join(item.unimarc_iso2709 for item in items)
        return export_file_name(datetime.now(UTC)), content


def export_file_name(moment: datetime) -> str:
    """ "faisca-unimarc-20261121-1530.mrc": sortable, and says what is inside."""
    return f"faisca-unimarc-{moment:%Y%m%d-%H%M}.mrc"


def _read(item: BasketItem) -> BasketItemRead:
    return BasketItemRead(
        id=item.id,
        record_id=item.record_id,
        title=item.title,
        authors=[author for author in item.authors.split(AUTHOR_SEPARATOR) if author],
        year=item.year,
        target_name=item.target_name,
        source_format=MarcFormat(item.source_format),
        created_at=item.created_at,
    )
