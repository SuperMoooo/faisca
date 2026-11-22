"""What other modules may use from cached_responses: a small key → JSON cache with expiry.

Searches stay live: the cache only keeps an answer for a day (CACHE_TTL_HOURS)
so a repeated search, or opening a record from the results, does not query
the external service again. Functions use the caller's session and never
commit: the calling service commits with its own unit of work.
"""

import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from faisca.modules.cached_responses.models import CachedResponse
from faisca.modules.cached_responses.repository import CachedResponseRepository

__all__ = ["make_cache_key", "purge_expired", "read_cached", "store_cached"]


def make_cache_key(*parts: str) -> str:
    """A fixed-length key from any number of parts (kind, target, normalised query…)."""
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


async def read_cached(session: AsyncSession, cache_key: str) -> str | None:
    """The cached JSON for [cache_key], or None if absent or expired."""
    entry = await CachedResponseRepository(session).find_by_key(cache_key)
    if entry is None or _as_utc(entry.expires_at) <= datetime.now(UTC):
        return None
    return entry.payload


async def store_cached(session: AsyncSession, cache_key: str, payload: str, ttl: timedelta) -> None:
    """Saves (or replaces) the JSON for [cache_key], valid for [ttl]."""
    repository = CachedResponseRepository(session)
    expires_at = datetime.now(UTC) + ttl
    entry = await repository.find_by_key(cache_key)
    if entry is None:
        await repository.add(
            CachedResponse(cache_key=cache_key, payload=payload, expires_at=expires_at)
        )
        return
    entry.payload = payload
    entry.expires_at = expires_at
    await repository.save(entry)


async def purge_expired(session: AsyncSession) -> int:
    """Deletes expired entries, so the SQLite file does not grow forever; returns how many."""
    return await CachedResponseRepository(session).delete_expired(datetime.now(UTC))


def _as_utc(moment: datetime) -> datetime:
    # SQLite has no time-zone type and returns naive datetimes; they were
    # written in UTC.
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
