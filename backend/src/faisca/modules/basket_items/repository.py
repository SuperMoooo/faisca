"""Database calls for the basket. Add a query here, never in the service."""

from collections.abc import Sequence

from sqlalchemy import delete, select

from faisca.db.repository import BaseRepository
from faisca.modules.basket_items.models import BasketItem

# moarch:repository-imports


class BasketItemRepository(BaseRepository[BasketItem]):
    """Reads and writes the basket_items table."""

    model = BasketItem

    async def list_all(self) -> Sequence[BasketItem]:
        """Every item, in the order they were added."""
        return (await self.session.scalars(select(BasketItem).order_by(BasketItem.id))).all()

    async def find_by_record_id(self, record_id: str) -> BasketItem | None:
        """The item holding this record, if it is already in the basket."""
        query = select(BasketItem).where(BasketItem.record_id == record_id)
        return (await self.session.scalars(query)).first()

    async def delete_all(self) -> None:
        """Empties the basket."""
        await self.session.execute(delete(BasketItem))
        await self.session.flush()


# moarch:module-repositories
