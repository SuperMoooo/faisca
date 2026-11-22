"""Searching one target over its protocol, politely and within its time limit."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

import httpx

from faisca.core.politeness import ThrottleRegistry
from faisca.modules.catalogues import z3950
from faisca.modules.catalogues.query_builder import (
    build_cql,
    build_cql_for_control_number,
    build_pqf,
    build_pqf_for_control_number,
)
from faisca.modules.catalogues.schemas import SearchQuery
from faisca.modules.catalogues.sru import search_sru
from faisca.modules.targets.public import CatalogueProtocol, CatalogueTarget

# ZOOM's own timeout covers each network wait; this margin lets it fire
# first, so its clearer error message wins over a bare asyncio timeout.
TIMEOUT_MARGIN_SECONDS = 5


@dataclass(frozen=True)
class RawTargetResult:
    """What a target sent back: the hit count and the fetched records as MARCXML."""

    hit_count: int
    marcxml_records: list[str]


class TargetSearcher(Protocol):
    """Searches one target. The live one goes to the network; tests pass a fake."""

    async def search(
        self, target: CatalogueTarget, query: SearchQuery, max_records: int
    ) -> RawTargetResult:
        """The target's records for [query]."""
        ...

    async def fetch_by_control_number(
        self, target: CatalogueTarget, control_number: str
    ) -> str | None:
        """One record by its 001 as MARCXML, or None if not found or not supported."""
        ...


class LiveTargetSearcher:
    """Searches real targets over Z39.50 (YAZ) or SRU (HTTP)."""

    def __init__(self, http_client: httpx.AsyncClient, throttles: ThrottleRegistry) -> None:
        self.http_client = http_client
        self.throttles = throttles

    async def search(
        self, target: CatalogueTarget, query: SearchQuery, max_records: int
    ) -> RawTargetResult:
        """Searches [target], waiting for its politeness slot, within its timeout."""
        async with self.throttles.for_service(target.id).slot():
            if target.protocol is CatalogueProtocol.Z3950:
                return await self._search_z3950(target, build_pqf(query), max_records)
            result = await search_sru(
                self.http_client, target, build_cql(query, target), max_records
            )
            return RawTargetResult(
                hit_count=result.hit_count, marcxml_records=result.marcxml_records
            )

    async def fetch_by_control_number(
        self, target: CatalogueTarget, control_number: str
    ) -> str | None:
        """Asks [target] for the record with this 001 again."""
        async with self.throttles.for_service(target.id).slot():
            if target.protocol is CatalogueProtocol.Z3950:
                pqf = build_pqf_for_control_number(control_number)
                result = await self._search_z3950(target, pqf, max_records=1)
                return result.marcxml_records[0] if result.marcxml_records else None
            cql = build_cql_for_control_number(target, control_number)
            if cql is None:
                return None
            sru_result = await search_sru(self.http_client, target, cql, max_records=1)
            return sru_result.marcxml_records[0] if sru_result.marcxml_records else None

    async def _search_z3950(
        self, target: CatalogueTarget, pqf: str, max_records: int
    ) -> RawTargetResult:
        request = z3950.Z3950Request(
            host=target.host or "",
            port=target.port or 210,
            database=target.database or "",
            pqf_query=pqf,
            record_syntax=target.record_syntax,
            source_charset=target.charset,
            max_records=max_records,
            timeout_seconds=target.timeout_seconds,
            username=target.username,
            password=target.password,
        )
        # ZOOM blocks, so it runs in a worker thread; the event loop keeps
        # serving the other targets meanwhile.
        result = await asyncio.wait_for(
            asyncio.to_thread(z3950.search_z3950, request),
            timeout=target.timeout_seconds + TIMEOUT_MARGIN_SECONDS,
        )
        return RawTargetResult(hit_count=result.hit_count, marcxml_records=result.marcxml_records)
