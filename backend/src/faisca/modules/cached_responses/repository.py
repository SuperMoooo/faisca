"""Database calls for cached_responses. Add a query here, never in public.py."""

from datetime import datetime

from sqlalchemy import delete, select

from faisca.db.repository import BaseRepository
from faisca.modules.cached_responses.models import CachedResponse

# moarch:repository-imports


class CachedResponseRepository(BaseRepository[CachedResponse]):
    """Reads and writes the cached_responses table."""

    model = CachedResponse

    async def find_by_key(self, cache_key: str) -> CachedResponse | None:
        """The entry with this key, expired or not."""
        query = select(CachedResponse).where(CachedResponse.cache_key == cache_key)
        return (await self.session.scalars(query)).first()

    async def delete_expired(self, now: datetime) -> int:
        """Removes every entry past its expiry; returns how many."""
        result = await self.session.execute(
            delete(CachedResponse).where(CachedResponse.expires_at < now)
        )
        await self.session.flush()
        return int(getattr(result, "rowcount", 0) or 0)


# moarch:module-repositories
