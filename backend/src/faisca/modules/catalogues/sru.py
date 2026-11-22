"""An SRU client: searchRetrieve over HTTP, returning MARCXML records as text."""

from dataclasses import dataclass

import httpx
from lxml import etree

from faisca.modules.targets.public import CatalogueTarget

_PARSER = etree.XMLParser(recover=True, no_network=True, resolve_entities=False, huge_tree=True)


class SruError(RuntimeError):
    """The SRU server answered with an HTTP error or a diagnostic instead of records."""


@dataclass(frozen=True)
class SruResult:
    """How many records matched, and the fetched ones as MARCXML strings."""

    hit_count: int
    marcxml_records: list[str]


async def search_sru(
    client: httpx.AsyncClient, target: CatalogueTarget, cql: str, max_records: int
) -> SruResult:
    """Runs one searchRetrieve on [target] and returns its records."""
    params = {
        "operation": "searchRetrieve",
        "version": target.sru_version,
        "query": cql,
        "maximumRecords": str(max_records),
        "startRecord": "1",
        "recordSchema": target.record_schema or "marcxml",
        "recordPacking": "xml",
    }
    response = await client.get(target.url or "", params=params, timeout=target.timeout_seconds)
    if response.status_code >= 400:
        raise SruError(f"HTTP {response.status_code}")
    return parse_search_response(response.content)


def parse_search_response(content: bytes) -> SruResult:
    """Reads numberOfRecords and every recordData out of a searchRetrieveResponse."""
    root = etree.fromstring(content, _PARSER)
    if root is None:
        raise SruError("The response is not XML.")
    hit_count = _number_of_records(root)
    records = [
        record for record in (_record_xml(data) for data in _elements(root, "recordData")) if record
    ]
    if not records and hit_count == 0:
        diagnostic = _diagnostic_message(root)
        if diagnostic:
            raise SruError(diagnostic)
    return SruResult(hit_count=hit_count, marcxml_records=records)


def _elements(root: etree._Element, local_name: str) -> list[etree._Element]:
    return [element for element in root.iter() if _local_name(element) == local_name]


def _local_name(element: etree._Element) -> str:
    return etree.QName(element.tag).localname if isinstance(element.tag, str) else ""


def _number_of_records(root: etree._Element) -> int:
    for element in _elements(root, "numberOfRecords"):
        text = (element.text or "").strip()
        if text.isdigit():
            return int(text)
    return 0


def _record_xml(record_data: etree._Element) -> str | None:
    children = [child for child in record_data if isinstance(child.tag, str)]
    if children:
        return etree.tostring(children[0], encoding="unicode")
    # recordPacking=string: the record is escaped XML inside the element's text.
    text = (record_data.text or "").strip()
    return text or None


def _diagnostic_message(root: etree._Element) -> str | None:
    for diagnostic in _elements(root, "diagnostic"):
        parts = [
            (child.text or "").strip()
            for child in diagnostic
            if _local_name(child) in {"message", "details"} and (child.text or "").strip()
        ]
        if parts:
            return ": ".join(parts)
    return None
