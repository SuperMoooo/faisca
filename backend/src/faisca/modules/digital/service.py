"""Digital-copy search: every source in parallel, partial results, one merged list."""

import asyncio
import json
import time
from datetime import timedelta

import httpx
import structlog
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from faisca.core.config import Settings
from faisca.core.politeness import ThrottleRegistry
from faisca.modules.cached_responses.public import make_cache_key, read_cached, store_cached
from faisca.modules.catalogues.public import SearchQuery, TargetSearcher
from faisca.modules.digital.schemas import (
    DigitalCopy,
    DigitalSearchResponse,
    SourceOutcome,
    SourceSearchStatus,
)
from faisca.modules.digital.sources import ADAPTERS
from faisca.modules.digital.sources.common import SourceContext, SourceError, SourceSkippedError
from faisca.modules.targets.public import DigitalSource, TargetsConfig

logger = structlog.get_logger(__name__)

# The BND adapter waits for the BNP catalogue, which can be slow.
QUEUE_ALLOWANCE_SECONDS = 10
CACHE_KIND = "digital-search"
_COPIES = TypeAdapter(list[DigitalCopy])


class DigitalSearchService:
    """Searches every enabled digital-copy source and merges the copies."""

    def __init__(
        self,
        session: AsyncSession,
        config: TargetsConfig,
        http_client: httpx.AsyncClient,
        throttles: ThrottleRegistry,
        catalogue_searcher: TargetSearcher,
        settings: Settings,
    ) -> None:
        self.session = session
        self.config = config
        self.http_client = http_client
        self.throttles = throttles
        self.catalogue_searcher = catalogue_searcher
        self.settings = settings

    async def search(self, query: SearchQuery) -> DigitalSearchResponse:
        """All copies found, in source order, with each source's outcome."""
        sources = self._chosen_sources(query.targets)
        answers: dict[str, tuple[list[DigitalCopy], SourceOutcome]] = {}
        live_sources: list[DigitalSource] = []
        for source in sources:
            cached = await read_cached(self.session, _cache_key(source, query))
            if cached is None:
                live_sources.append(source)
                continue
            copies = _COPIES.validate_json(cached)
            answers[source.id] = (
                copies,
                _outcome(source, SourceSearchStatus.OK, len(copies), from_cache=True),
            )

        live_answers = await asyncio.gather(
            *(self._search_live(source, query) for source in live_sources)
        )
        for source, (copies, outcome) in zip(live_sources, live_answers, strict=True):
            answers[source.id] = (copies, outcome)
            if outcome.status is SourceSearchStatus.OK:
                payload = json.dumps([copy.model_dump(mode="json") for copy in copies])
                ttl = timedelta(hours=self.settings.cache_ttl_hours)
                await store_cached(self.session, _cache_key(source, query), payload, ttl)
        await self.session.commit()

        return DigitalSearchResponse(
            query=query,
            copies=_without_repeated_urls(
                [copy for source in sources for copy in answers[source.id][0]]
            ),
            sources=[answers[source.id][1] for source in sources],
        )

    def _chosen_sources(self, source_ids: list[str] | None) -> list[DigitalSource]:
        enabled = [source for source in self.config.digital_sources if source.enabled]
        if not source_ids:
            return enabled
        return [source for source in enabled if source.id in source_ids]

    async def _search_live(
        self, source: DigitalSource, query: SearchQuery
    ) -> tuple[list[DigitalCopy], SourceOutcome]:
        """One source's search; every failure becomes an outcome, never an exception."""
        started = time.monotonic()
        context = SourceContext(
            source=source,
            http_client=self.http_client,
            throttle=self.throttles.for_service(source.id),
            settings=self.settings,
            targets=self.config,
            catalogue_searcher=self.catalogue_searcher,
        )
        adapter = ADAPTERS[source.kind]
        try:
            copies = await asyncio.wait_for(
                adapter(context, query), source.timeout_seconds + QUEUE_ALLOWANCE_SECONDS
            )
        except SourceSkippedError as reason:
            return [], _outcome(
                source, SourceSearchStatus.SKIPPED, error=str(reason), started=started
            )
        except (TimeoutError, httpx.TimeoutException):
            return [], _outcome(
                source,
                SourceSearchStatus.TIMED_OUT,
                error="Sem resposta dentro do tempo limite.",
                started=started,
            )
        # Adapters parse other people's JSON and XML; any surprise there is
        # that source's failure, not the whole search's.
        except (
            SourceError,
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
            OSError,
            RuntimeError,
        ) as error:
            logger.warning("digital_source_failed", source=source.id, error=str(error))
            return [], _outcome(
                source,
                SourceSearchStatus.FAILED,
                error=str(error) or type(error).__name__,
                started=started,
            )
        logger.info("digital_source_searched", source=source.id, found=len(copies))
        return copies, _outcome(source, SourceSearchStatus.OK, len(copies), started=started)


def _outcome(
    source: DigitalSource,
    status: SourceSearchStatus,
    found_count: int = 0,
    *,
    error: str | None = None,
    started: float | None = None,
    from_cache: bool = False,
) -> SourceOutcome:
    elapsed_ms = round((time.monotonic() - started) * 1000) if started is not None else None
    return SourceOutcome(
        source_id=source.id,
        source_name=source.name,
        status=status,
        found_count=found_count,
        elapsed_ms=elapsed_ms,
        from_cache=from_cache,
        error=error,
    )


def _cache_key(source: DigitalSource, query: SearchQuery) -> str:
    return make_cache_key(CACHE_KIND, source.id, query.cache_fragment())


def _without_repeated_urls(copies: list[DigitalCopy]) -> list[DigitalCopy]:
    # Open Library and the Internet Archive often point to the same scan.
    seen: set[str] = set()
    unique: list[DigitalCopy] = []
    for copy in copies:
        if copy.url in seen:
            continue
        seen.add(copy.url)
        unique.append(copy)
    return unique
