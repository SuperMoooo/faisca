"""Federated catalogue search: every target in parallel, partial results, duplicates grouped."""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import timedelta

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from faisca.core.config import Settings
from faisca.core.errors import AppError, NotFoundError
from faisca.modules.cached_responses.public import make_cache_key, read_cached, store_cached
from faisca.modules.catalogues.record_ids import (
    InvalidRecordIdError,
    make_record_id,
    parse_record_id,
)
from faisca.modules.catalogues.schemas import (
    CatalogueSearchResponse,
    RecordDetail,
    RecordGroup,
    RecordSummary,
    RecordVariant,
    SearchQuery,
    TargetOutcome,
    TargetSearchStatus,
)
from faisca.modules.catalogues.searcher import RawTargetResult, TargetSearcher
from faisca.modules.catalogues.sru import SruError
from faisca.modules.catalogues.z3950 import Z3950Error, Z3950UnavailableError
from faisca.modules.records.public import (
    CatalogueRecord,
    MarcFormat,
    MarcXmlError,
    group_duplicates,
    read_catalogue_record,
    work_key,
)
from faisca.modules.targets.public import CatalogueTarget, TargetsConfig

logger = structlog.get_logger(__name__)

# Beyond the target's own timeout: time to wait for a politeness slot.
QUEUE_ALLOWANCE_SECONDS = 10
SEARCH_CACHE_KIND = "catalogue-search"
RECORD_CACHE_KIND = "catalogue-record"


class UnknownTargetError(AppError):
    """The request names a target that is not in targets.yaml."""

    code = "unknown_target"


@dataclass(frozen=True)
class FoundRecord:
    """A record with the target it came from, ready to show or export."""

    record_id: str
    target: CatalogueTarget
    record: CatalogueRecord

    def summary(self) -> RecordSummary:
        """The record as one row of the results."""
        return summarize_record(self.record_id, self.target, self.record)


@dataclass(frozen=True)
class _TargetResult:
    target: CatalogueTarget
    outcome: TargetOutcome
    records: list[tuple[str, CatalogueRecord]]


class CatalogueService:
    """Searches the catalogues and serves the records it found."""

    def __init__(
        self,
        session: AsyncSession,
        config: TargetsConfig,
        searcher: TargetSearcher,
        settings: Settings,
    ) -> None:
        self.session = session
        self.config = config
        self.searcher = searcher
        self.settings = settings

    async def search(self, query: SearchQuery) -> CatalogueSearchResponse:
        """Searches every chosen target at once and merges what comes back in time."""
        targets = self._chosen_targets(query.targets)
        results: dict[str, _TargetResult] = {}
        live_targets: list[CatalogueTarget] = []
        # Cache reads come before the fan-out and writes after it: the
        # session must not be used by several tasks at once.
        for target in targets:
            cached = await self._read_cached_search(target, query)
            if cached is None:
                live_targets.append(target)
            else:
                results[target.id] = _cached_result(target, cached)

        live_answers = await asyncio.gather(
            *(self._search_live(target, query) for target in live_targets)
        )
        for target, (raw, outcome) in zip(live_targets, live_answers, strict=True):
            records = _parse_records(target, raw.marcxml_records) if raw else []
            if raw is not None:
                await self._cache_search(target, query, raw, records)
            results[target.id] = _TargetResult(
                target=target,
                outcome=outcome.model_copy(update={"returned_count": len(records)}),
                records=records,
            )
        await self.session.commit()
        return _merge(query, [results[target.id] for target in targets])

    async def get_record_detail(self, record_id: str) -> RecordDetail:
        """The record in UNIMARC and, when converted, its MARC21 original."""
        found = await self.find_record(record_id)
        await self.session.commit()
        return RecordDetail(
            summary=found.summary(),
            unimarc=found.record.unimarc_view(),
            original=found.record.original_view(),
        )

    async def get_record_file(self, record_id: str, variant: RecordVariant) -> tuple[str, bytes]:
        """The record as an ISO 2709 file: its name and bytes."""
        found = await self.find_record(record_id)
        await self.session.commit()
        if variant is RecordVariant.ORIGINAL:
            suffix = found.record.source_format.value
            return f"{record_id}-{suffix}.mrc", found.record.original_iso2709()
        return f"{record_id}-unimarc.mrc", found.record.unimarc_iso2709()

    async def find_record(self, record_id: str) -> FoundRecord:
        """The record from the cache or, once expired, from its target again by 001.

        It may cache a refetched record but never commits: the caller (a
        method here, or another module through public.py) owns the transaction.
        """
        try:
            parsed = parse_record_id(record_id)
        except InvalidRecordIdError as error:
            raise NotFoundError(f"O registo {record_id} não existe.") from error
        target = self.config.catalogue(parsed.target_id)
        if target is None:
            raise NotFoundError(f"O catálogo {parsed.target_id} não está configurado.")

        cached = await read_cached(self.session, make_cache_key(RECORD_CACHE_KIND, record_id))
        if cached is not None:
            payload = json.loads(cached)
            record = read_catalogue_record(payload["marcxml"], MarcFormat(payload["format"]))
            return FoundRecord(record_id=record_id, target=target, record=record)
        return await self._fetch_again(record_id, target, parsed.control_number)

    # ── searching ──────────────────────────────────────────────────────────

    def _chosen_targets(self, target_ids: list[str] | None) -> list[CatalogueTarget]:
        enabled = [target for target in self.config.catalogues if target.enabled]
        if not target_ids:
            return enabled
        unknown = [
            target_id for target_id in target_ids if self.config.catalogue(target_id) is None
        ]
        if unknown:
            raise UnknownTargetError(f"Catálogos desconhecidos: {', '.join(unknown)}.")
        return [target for target in enabled if target.id in target_ids]

    async def _search_live(
        self, target: CatalogueTarget, query: SearchQuery
    ) -> tuple[RawTargetResult | None, TargetOutcome]:
        """One target's search; every failure becomes an outcome, never an exception."""
        started = time.monotonic()

        def outcome(
            status: TargetSearchStatus, error: str | None = None, hits: int | None = None
        ) -> TargetOutcome:
            return TargetOutcome(
                target_id=target.id,
                target_name=target.name,
                status=status,
                hit_count=hits,
                elapsed_ms=round((time.monotonic() - started) * 1000),
                error=error,
            )

        try:
            result = await asyncio.wait_for(
                self.searcher.search(target, query, self.settings.max_records_per_target),
                timeout=target.timeout_seconds + QUEUE_ALLOWANCE_SECONDS,
            )
        except TimeoutError:
            return None, outcome(
                TargetSearchStatus.TIMED_OUT, "Sem resposta dentro do tempo limite."
            )
        except Z3950UnavailableError as error:
            return None, outcome(TargetSearchStatus.UNAVAILABLE, str(error))
        except (Z3950Error, SruError, httpx.HTTPError, OSError) as error:
            status = (
                TargetSearchStatus.TIMED_OUT if _is_timeout(error) else TargetSearchStatus.FAILED
            )
            return None, outcome(status, str(error) or type(error).__name__)
        logger.info(
            "catalogue_target_searched",
            target=target.id,
            hits=result.hit_count,
            fetched=len(result.marcxml_records),
            elapsed_ms=round((time.monotonic() - started) * 1000),
        )
        return result, outcome(TargetSearchStatus.OK, hits=result.hit_count)

    # ── cache ──────────────────────────────────────────────────────────────

    def _ttl(self) -> timedelta:
        return timedelta(hours=self.settings.cache_ttl_hours)

    async def _read_cached_search(
        self, target: CatalogueTarget, query: SearchQuery
    ) -> RawTargetResult | None:
        cached = await read_cached(self.session, _search_cache_key(target, query))
        if cached is None:
            return None
        payload = json.loads(cached)
        return RawTargetResult(hit_count=payload["hit_count"], marcxml_records=payload["records"])

    async def _cache_search(
        self,
        target: CatalogueTarget,
        query: SearchQuery,
        raw: RawTargetResult,
        records: list[tuple[str, CatalogueRecord]],
    ) -> None:
        """Keeps a successful answer, and each record so it opens without a new search.

        Failed targets are not cached: they are asked again on the next search.
        """
        payload = json.dumps({"hit_count": raw.hit_count, "records": raw.marcxml_records})
        await store_cached(self.session, _search_cache_key(target, query), payload, self._ttl())
        for record_id, record in records:
            await self._cache_record(record_id, record)

    async def _cache_record(self, record_id: str, record: CatalogueRecord) -> None:
        payload = json.dumps(
            {"format": record.source_format.value, "marcxml": record.original_marcxml()}
        )
        await store_cached(
            self.session, make_cache_key(RECORD_CACHE_KIND, record_id), payload, self._ttl()
        )

    async def _fetch_again(
        self, record_id: str, target: CatalogueTarget, control_number: str | None
    ) -> FoundRecord:
        expired = NotFoundError(
            "O registo já não está em cache e o catálogo não o devolveu. Repita a pesquisa."
        )
        if control_number is None:
            raise expired
        try:
            marcxml = await asyncio.wait_for(
                self.searcher.fetch_by_control_number(target, control_number),
                timeout=target.timeout_seconds + QUEUE_ALLOWANCE_SECONDS,
            )
        except (
            TimeoutError,
            Z3950Error,
            Z3950UnavailableError,
            SruError,
            httpx.HTTPError,
            OSError,
        ) as error:
            raise expired from error
        if marcxml is None:
            raise expired
        record = read_catalogue_record(marcxml, target.format)
        await self._cache_record(record_id, record)
        return FoundRecord(record_id=record_id, target=target, record=record)


def _cached_result(target: CatalogueTarget, cached: RawTargetResult) -> _TargetResult:
    records = _parse_records(target, cached.marcxml_records)
    outcome = TargetOutcome(
        target_id=target.id,
        target_name=target.name,
        status=TargetSearchStatus.OK,
        hit_count=cached.hit_count,
        returned_count=len(records),
        from_cache=True,
    )
    return _TargetResult(target=target, outcome=outcome, records=records)


def _search_cache_key(target: CatalogueTarget, query: SearchQuery) -> str:
    return make_cache_key(SEARCH_CACHE_KIND, target.id, query.cache_fragment())


def _is_timeout(error: Exception) -> bool:
    return isinstance(error, httpx.TimeoutException) or "timeout" in str(error).lower()


def _parse_records(
    target: CatalogueTarget, marcxml_records: list[str]
) -> list[tuple[str, CatalogueRecord]]:
    """Each MARCXML string as a record with its id; unreadable ones are logged and skipped."""
    parsed: list[tuple[str, CatalogueRecord]] = []
    for marcxml in marcxml_records:
        try:
            record = read_catalogue_record(marcxml, target.format)
        except MarcXmlError as error:
            logger.warning("unreadable_record", target=target.id, error=str(error))
            continue
        parsed.append((make_record_id(target.id, record.control_number, marcxml), record))
    return parsed


def summarize_record(
    record_id: str, target: CatalogueTarget, record: CatalogueRecord
) -> RecordSummary:
    """One row of the results: the record's description and where it came from."""
    description = record.description
    return RecordSummary(
        id=record_id,
        target_id=target.id,
        target_name=target.name,
        country=target.country,
        source_format=record.source_format,
        description=description,
        has_digital_copy=bool(description.digital_links),
    )


def _merge(query: SearchQuery, results: list[_TargetResult]) -> CatalogueSearchResponse:
    """Every target's records as groups of the same book, in targets.yaml order.

    Targets are listed Portuguese first in targets.yaml, so within a group
    the PORBASE/BNP record (native UNIMARC, the cataloguer's reference) comes
    first, and converted MARC21 records follow.
    """
    summaries = [
        summarize_record(record_id, result.target, record)
        for result in results
        for record_id, record in result.records
    ]
    groups = group_duplicates(summaries, lambda summary: summary.description)
    return CatalogueSearchResponse(
        query=query,
        groups=[RecordGroup(key=work_key(group[0].description), records=group) for group in groups],
        record_count=len(summaries),
        targets=[result.outcome for result in results],
    )
