"""What every digital-copy adapter shares: its context, its errors, query helpers."""

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from faisca.core.config import Settings
from faisca.core.politeness import RequestThrottle
from faisca.modules.catalogues.public import SearchQuery, TargetSearcher
from faisca.modules.digital.schemas import DigitalCopy
from faisca.modules.targets.public import DigitalSource, TargetsConfig


@dataclass(frozen=True)
class SourceContext:
    """Everything an adapter may use: the source's config, the HTTP client, its throttle."""

    source: DigitalSource
    http_client: httpx.AsyncClient
    throttle: RequestThrottle
    settings: Settings
    targets: TargetsConfig
    catalogue_searcher: TargetSearcher

    async def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        """GET [url] within the source's politeness slot and timeout; the parsed JSON."""
        async with self.throttle.slot():
            response = await self.http_client.get(
                url, params=params, timeout=self.source.timeout_seconds
            )
        _raise_for_status(response)
        return response.json()

    async def get_bytes(self, url: str, params: dict[str, str] | None = None) -> bytes:
        """GET [url] within the source's politeness slot and timeout; the raw body."""
        async with self.throttle.slot():
            response = await self.http_client.get(
                url, params=params, timeout=self.source.timeout_seconds
            )
        _raise_for_status(response)
        return response.content


class SourceError(RuntimeError):
    """The source answered with an error."""


class SourceSkippedError(RuntimeError):
    """The source cannot run this search (missing key, or a query it does not support)."""


SourceAdapter = Callable[[SourceContext, SearchQuery], Awaitable[list[DigitalCopy]]]


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 429:
        raise SourceError("Quota de pedidos esgotada (HTTP 429).")
    if response.status_code >= 400:
        raise SourceError(f"HTTP {response.status_code}")


def query_words(text: str) -> list[str]:
    """The words of [text], without characters that are syntax in Solr or CQL."""
    return re.findall(r"[\w'-]+", text)


def first_text(value: object) -> str | None:
    """The first string of a JSON value that may be a string, a list or missing."""
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item:
                return item
    return None


def text_list(value: object) -> list[str]:
    """A JSON value that may be a string or a list, as a list of strings."""
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def year_from(value: object) -> str | None:
    """The first four-digit year in a date string ("1981-05-01", "c1981")."""
    text = first_text(value) if not isinstance(value, int) else str(value)
    if not text:
        return None
    match = re.search(r"\b(1[0-9]{3}|20[0-9]{2})\b", text)
    return match.group() if match else None
