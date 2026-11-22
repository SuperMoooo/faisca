"""The response cache: what other modules get from cached_responses/public.py."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from faisca.modules.cached_responses.public import (
    make_cache_key,
    purge_expired,
    read_cached,
    store_cached,
)


async def test_stores_and_reads_back(session: AsyncSession) -> None:
    key = make_cache_key("catalogue-search", "loc", '{"title": "lusiadas"}')

    await store_cached(session, key, '{"hit_count": 2}', timedelta(hours=24))
    await session.commit()

    assert await read_cached(session, key) == '{"hit_count": 2}'


async def test_storing_again_replaces_the_payload(session: AsyncSession) -> None:
    key = make_cache_key("k")
    await store_cached(session, key, "old", timedelta(hours=1))
    await store_cached(session, key, "new", timedelta(hours=1))

    assert await read_cached(session, key) == "new"


async def test_expired_entries_are_not_read_and_are_purged(session: AsyncSession) -> None:
    expired_key, fresh_key = make_cache_key("expired"), make_cache_key("fresh")
    await store_cached(session, expired_key, "x", timedelta(seconds=-1))
    await store_cached(session, fresh_key, "y", timedelta(hours=1))

    assert await read_cached(session, expired_key) is None
    assert await purge_expired(session) == 1
    assert await read_cached(session, fresh_key) == "y"


def test_keys_are_fixed_length_and_depend_on_every_part() -> None:
    assert len(make_cache_key("a", "b")) == 64
    assert make_cache_key("a", "b") != make_cache_key("ab")
