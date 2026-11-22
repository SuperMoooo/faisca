"""Listing targets and checking, live, whether each one answers."""

import asyncio
import time

import httpx

from faisca.modules.targets.schemas import (
    CatalogueProtocol,
    CatalogueTarget,
    DigitalSource,
    Reachability,
    TargetKind,
    TargetList,
    TargetRead,
    TargetsConfig,
    TargetStatus,
    TargetStatusList,
)

# A reachability check only has to tell up from down; it waits less than a search.
CHECK_TIMEOUT_SECONDS = 8.0
REFUSING_STATUS_CODES = {401, 403, 429}


class TargetService:
    """Answers the settings page: which targets exist and which respond right now."""

    def __init__(self, config: TargetsConfig, http_client: httpx.AsyncClient) -> None:
        self.config = config
        self.http_client = http_client

    async def list_targets(self) -> TargetList:
        """Every configured target, as the API shows it."""
        return TargetList(
            catalogues=[_catalogue_read(target) for target in self.config.catalogues],
            digital_sources=[_digital_read(source) for source in self.config.digital_sources],
        )

    async def check_all(self) -> TargetStatusList:
        """Checks every target at once; the slowest one decides how long this takes."""
        checks = [self._check_catalogue(target) for target in self.config.catalogues]
        checks += [self._check_digital(source) for source in self.config.digital_sources]
        return TargetStatusList(statuses=list(await asyncio.gather(*checks)))

    async def _check_catalogue(self, target: CatalogueTarget) -> TargetStatus:
        if not target.enabled:
            return TargetStatus(id=target.id, reachability=Reachability.DISABLED)
        if target.protocol is CatalogueProtocol.Z3950:
            return await _check_tcp(target.id, target.host or "", target.port or 210)
        explain_url = f"{target.url}?operation=explain&version={target.sru_version}"
        return await self._check_http(target.id, explain_url)

    async def _check_digital(self, source: DigitalSource) -> TargetStatus:
        if not source.enabled:
            return TargetStatus(id=source.id, reachability=Reachability.DISABLED)
        return await self._check_http(source.id, source.check_url)

    async def _check_http(self, target_id: str, url: str) -> TargetStatus:
        started = time.monotonic()
        try:
            response = await self.http_client.get(url, timeout=CHECK_TIMEOUT_SECONDS)
        except httpx.HTTPError as error:
            return TargetStatus(
                id=target_id, reachability=Reachability.UNREACHABLE, detail=type(error).__name__
            )
        latency_ms = _elapsed_ms(started)
        if response.status_code in REFUSING_STATUS_CODES:
            return TargetStatus(
                id=target_id,
                reachability=Reachability.BLOCKED,
                latency_ms=latency_ms,
                detail=f"HTTP {response.status_code}",
            )
        if response.status_code >= 500:
            return TargetStatus(
                id=target_id,
                reachability=Reachability.UNREACHABLE,
                latency_ms=latency_ms,
                detail=f"HTTP {response.status_code}",
            )
        return TargetStatus(
            id=target_id, reachability=Reachability.REACHABLE, latency_ms=latency_ms
        )


async def _check_tcp(target_id: str, host: str, port: int) -> TargetStatus:
    # Z39.50 runs over plain TCP; a server that accepts the connection is up.
    # A full Init would also prove the database name, but costs the server a session.
    started = time.monotonic()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), CHECK_TIMEOUT_SECONDS
        )
    except (OSError, TimeoutError) as error:
        detail = (
            "timeout" if isinstance(error, TimeoutError) else str(error) or type(error).__name__
        )
        return TargetStatus(id=target_id, reachability=Reachability.UNREACHABLE, detail=detail)
    writer.close()
    await writer.wait_closed()
    return TargetStatus(
        id=target_id, reachability=Reachability.REACHABLE, latency_ms=_elapsed_ms(started)
    )


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _catalogue_read(target: CatalogueTarget) -> TargetRead:
    return TargetRead(
        id=target.id,
        name=target.name,
        kind=TargetKind.CATALOGUE,
        country=target.country,
        protocol=target.protocol.value,
        format=target.format,
        endpoint=target.endpoint,
        enabled=target.enabled,
        verified_on=target.verified_on,
        notes=target.notes,
    )


def _digital_read(source: DigitalSource) -> TargetRead:
    return TargetRead(
        id=source.id,
        name=source.name,
        kind=TargetKind.DIGITAL,
        country=None,
        protocol=source.kind.value,
        format=None,
        endpoint=source.url,
        enabled=source.enabled,
        verified_on=source.verified_on,
        notes=source.notes,
    )
