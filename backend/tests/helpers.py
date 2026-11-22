"""Helpers the tests share: fixture records, fixed targets, and a fake catalogue searcher."""

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from faisca.core.config import Environment, Settings
from faisca.modules.catalogues.schemas import SearchQuery
from faisca.modules.catalogues.searcher import RawTargetResult
from faisca.modules.records.marcxml import find_record_element
from faisca.modules.targets.public import CatalogueTarget, TargetsConfig

FIXTURES = Path(__file__).parent / "fixtures"
RECORD_FIXTURES = FIXTURES / "records"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def read_fixture_records(filename: str) -> list[str]:
    """Every MARC record in a fixture file (an SRU response or a Z39.50 dump), as MARCXML."""
    root = etree.parse(str(RECORD_FIXTURES / filename)).getroot()
    records: list[str] = []
    for element in root.iter():
        if not isinstance(element.tag, str) or etree.QName(element.tag).localname != "record":
            continue
        record = find_record_element(element)
        if record is element:
            records.append(etree.tostring(record, encoding="unicode"))
    return records


def first_fixture_record(filename: str) -> str:
    """The first MARC record in a fixture file."""
    return read_fixture_records(filename)[0]


@dataclass
class FakeTargetSearcher:
    """Answers catalogue searches from canned results; an Exception value is raised instead."""

    results: dict[str, RawTargetResult | Exception] = field(default_factory=dict)
    records_by_control_number: dict[str, str] = field(default_factory=dict)
    searched: list[str] = field(default_factory=list)

    async def search(
        self, target: CatalogueTarget, query: SearchQuery, max_records: int
    ) -> RawTargetResult:
        """The canned result for [target], or no records."""
        self.searched.append(target.id)
        result = self.results.get(target.id, RawTargetResult(hit_count=0, marcxml_records=[]))
        if isinstance(result, Exception):
            raise result
        return result

    async def fetch_by_control_number(
        self, target: CatalogueTarget, control_number: str
    ) -> str | None:
        """The canned record with this 001, or None."""
        return self.records_by_control_number.get(control_number)


def build_test_targets() -> TargetsConfig:
    """Four catalogues (two Z39.50 UNIMARC, two SRU MARC21) and every kind of digital source."""
    return TargetsConfig.model_validate(
        {
            "catalogues": [
                {
                    "id": "porbase",
                    "name": "PORBASE",
                    "country": "PT",
                    "protocol": "z3950",
                    "format": "unimarc",
                    "host": "z3950.example.invalid",
                    "port": 210,
                    "database": "porbase",
                    "charset": "iso5426",
                },
                {
                    "id": "bnp",
                    "name": "BNP",
                    "country": "PT",
                    "protocol": "z3950",
                    "format": "unimarc",
                    "host": "z3950.example.invalid",
                    "port": 210,
                    "database": "bn",
                    "password": "secret-password",
                },
                {
                    "id": "loc",
                    "name": "Library of Congress",
                    "country": "US",
                    "protocol": "sru",
                    "format": "marc21",
                    "url": "https://sru.example.invalid/loc",
                    "record_schema": "marcxml",
                    "indexes": {
                        "title": "dc.title",
                        "author": "dc.creator",
                        "isbn": "bath.isbn",
                        "control_number": "rec.id",
                    },
                },
                {
                    "id": "k10plus",
                    "name": "K10plus",
                    "country": "DE",
                    "protocol": "sru",
                    "format": "marc21",
                    "url": "https://sru.example.invalid/k10plus",
                    "record_schema": "marcxml",
                    "indexes": {"title": "pica.tit", "author": "pica.per", "isbn": "pica.isb"},
                },
                {
                    "id": "dnb",
                    "name": "DNB",
                    "country": "DE",
                    "protocol": "sru",
                    "format": "marc21",
                    "url": "https://sru.example.invalid/dnb",
                    "record_schema": "MARC21-xml",
                    "indexes": {"title": "tit", "author": "per", "isbn": "num"},
                    "enabled": False,
                },
            ],
            "digital_sources": [
                {
                    "id": "bnd",
                    "name": "BND",
                    "kind": "bnd",
                    "url": "https://bnd.example.invalid",
                    "check_url": "https://bnd.example.invalid/",
                    "catalogue_target": "bnp",
                },
                {
                    "id": "europeana",
                    "name": "Europeana",
                    "kind": "europeana",
                    "url": "https://europeana.example.invalid/search.json",
                    "check_url": "https://europeana.example.invalid/search.json",
                },
                {
                    "id": "internet-archive",
                    "name": "Internet Archive",
                    "kind": "internet_archive",
                    "url": "https://archive.example.invalid/advancedsearch.php",
                    "check_url": "https://archive.example.invalid/",
                },
                {
                    "id": "open-library",
                    "name": "Open Library",
                    "kind": "open_library",
                    "url": "https://openlibrary.example.invalid/search.json",
                    "check_url": "https://openlibrary.example.invalid/",
                },
                {
                    "id": "google-books",
                    "name": "Google Books",
                    "kind": "google_books",
                    "url": "https://books.example.invalid/volumes",
                    "check_url": "https://books.example.invalid/",
                },
                {
                    "id": "hathitrust",
                    "name": "HathiTrust",
                    "kind": "hathitrust",
                    "url": "https://hathitrust.example.invalid/brief",
                    "check_url": "https://hathitrust.example.invalid/",
                },
                {
                    "id": "gallica",
                    "name": "Gallica",
                    "kind": "gallica",
                    "url": "https://gallica.example.invalid/SRU",
                    "check_url": "https://gallica.example.invalid/SRU",
                    "enabled": False,
                },
            ],
        }
    )


def make_test_settings(**overrides: object) -> Settings:
    """Settings for a test app: in-memory database, no web app, no politeness delay."""
    values: dict[str, object] = {
        "environment": Environment.TEST,
        "database_url": "sqlite+aiosqlite:///:memory:",
        "web_dist_dir": None,
        "min_seconds_between_requests": 0,
    }
    return Settings.model_validate({**values, **overrides})
