"""The digital-copy search: every source mocked (respx for HTTP, the fake searcher for BND)."""

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx
from httpx import AsyncClient

from faisca.core.config import Settings
from faisca.modules.catalogues.searcher import RawTargetResult
from faisca.modules.catalogues.z3950 import Z3950Error
from tests.helpers import FakeTargetSearcher, first_fixture_record, make_test_settings

SEARCH_URL = "/api/v1/digital/search"
PURL_FIELDS = (
    '<datafield tag="856" ind1="4" ind2="0"><subfield code="u">https://purl.pt/43754</subfield></datafield>'
    '<datafield tag="856" ind1="4" ind2="1"><subfield code="u">'
    "https://purl.pt/43754/service/media/cover/low</subfield></datafield></record>"
)

ARCHIVE_PAYLOAD = {
    "response": {
        "docs": [
            {
                "identifier": "oslusiad00cam",
                "title": "Os lusiadas",
                "creator": "Camões",
                "year": "1880",
            },
            {"identifier": "lent00", "title": "Os Lusíadas", "access-restricted-item": "true"},
        ]
    }
}
OPEN_LIBRARY_PAYLOAD = {
    "docs": [
        {
            "key": "/works/OL1W",
            "title": "Os Lusíadas",
            "ebook_access": "public",
            "ia": ["oslusiad00cam"],
        },
        {"key": "/works/OL2W", "title": "Lusiads", "ebook_access": "borrowable", "cover_i": 42},
        {"key": "/works/OL3W", "title": "No ebook", "ebook_access": "no_ebook"},
    ]
}
GOOGLE_PAYLOAD = {
    "items": [
        {
            "volumeInfo": {
                "title": "Os Lusiadas",
                "subtitle": "poema epico",
                "authors": ["Luís de Camões"],
                "publishedDate": "1878",
                "imageLinks": {"thumbnail": "http://books.google.com/x.jpg"},
            },
            "accessInfo": {"webReaderLink": "https://play.google.com/books/reader?id=abc"},
        }
    ]
}
EUROPEANA_PAYLOAD = {
    "items": [
        {
            "guid": "https://www.europeana.eu/item/1/abc",
            "title": ["Os Lusiadas"],
            "dcCreator": ["http://data.europeana.eu/agent/60782", "Luis de Camoes"],
            "year": ["1613"],
            "rights": ["http://creativecommons.org/publicdomain/mark/1.0/"],
            "edmIsShownAt": ["https://provider.example/item/1"],
            "dataProvider": ["Complutense University of Madrid"],
        }
    ]
}
HATHITRUST_PAYLOAD = {
    "records": {"001": {"titles": ["Os Lusiadas"], "publishDates": ["1981"]}},
    "items": [
        {
            "fromRecord": "001",
            "itemURL": "https://hdl.handle.net/2027/a",
            "usRightsString": "Full view",
        },
        {
            "fromRecord": "001",
            "itemURL": "https://hdl.handle.net/2027/b",
            "usRightsString": "Limited (search-only)",
        },
    ],
}


@pytest.fixture
def settings() -> Settings:
    """Test settings with a Europeana key, so that source runs too."""
    return make_test_settings(europeana_api_key="test-key")


@pytest.fixture
def external_services() -> Iterator[respx.MockRouter]:
    """Every HTTP source answering with a payload shaped like its real API."""
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://archive.example.invalid/").mock(
            return_value=httpx.Response(200, json=ARCHIVE_PAYLOAD)
        )
        router.get(url__startswith="https://openlibrary.example.invalid/").mock(
            return_value=httpx.Response(200, json=OPEN_LIBRARY_PAYLOAD)
        )
        router.get(url__startswith="https://books.example.invalid/").mock(
            return_value=httpx.Response(200, json=GOOGLE_PAYLOAD)
        )
        router.get(url__startswith="https://europeana.example.invalid/").mock(
            return_value=httpx.Response(200, json=EUROPEANA_PAYLOAD)
        )
        router.get(url__startswith="https://hathitrust.example.invalid/").mock(
            return_value=httpx.Response(200, json=HATHITRUST_PAYLOAD)
        )
        yield router


def bnp_record_with_purl() -> str:
    record = first_fixture_record("z3950_porbase_lusiadas.xml")
    return record.replace("</record>", PURL_FIELDS)


def by_source(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {outcome["source_id"]: outcome for outcome in body["sources"]}


async def test_every_enabled_source_is_searched_and_merged(
    client: AsyncClient, fake_searcher: FakeTargetSearcher, external_services: respx.MockRouter
) -> None:
    fake_searcher.results = {
        "bnp": RawTargetResult(
            hit_count=2,
            marcxml_records=[
                bnp_record_with_purl(),
                first_fixture_record("z3950_porbase_lusiadas.xml"),
            ],
        )
    }

    response = await client.get(SEARCH_URL, params={"title": "lusiadas"})

    body = response.json()
    sources = by_source(body)
    assert response.status_code == 200
    assert sources["bnd"]["found_count"] == 1
    assert sources["internet-archive"]["found_count"] == 2
    assert sources["open-library"]["found_count"] == 2
    assert sources["google-books"]["found_count"] == 1
    assert sources["europeana"]["found_count"] == 1
    assert sources["hathitrust"]["status"] == "skipped"  # no ISBN in the query
    assert "gallica" not in sources  # disabled in targets
    # Open Library's public scan is the same archive.org URL: listed once.
    urls = [copy["url"] for copy in body["copies"]]
    assert urls.count("https://archive.org/details/oslusiad00cam") == 1


async def test_bnd_copies_come_from_bnp_records_with_purl_links(
    client: AsyncClient, fake_searcher: FakeTargetSearcher, external_services: respx.MockRouter
) -> None:
    fake_searcher.results = {
        "bnp": RawTargetResult(hit_count=1, marcxml_records=[bnp_record_with_purl()])
    }

    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()
    [bnd_copy] = [copy for copy in body["copies"] if copy["source_id"] == "bnd"]

    assert bnd_copy["url"] == "https://purl.pt/43754"
    assert bnd_copy["thumbnail_url"] == "https://purl.pt/43754/service/media/cover/low"
    assert bnd_copy["access"] == "free"
    assert bnd_copy["catalogue_record_id"].startswith("bnp.")


async def test_access_is_free_or_restricted_per_source(
    client: AsyncClient, external_services: respx.MockRouter
) -> None:
    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()
    access = {(copy["source_id"], copy["title"]): copy["access"] for copy in body["copies"]}

    assert access[("internet-archive", "Os lusiadas")] == "free"
    assert access[("internet-archive", "Os Lusíadas")] == "restricted"  # lending only
    assert access[("open-library", "Lusiads")] == "restricted"
    assert access[("europeana", "Os Lusiadas")] == "free"
    google = next(copy for copy in body["copies"] if copy["source_id"] == "google-books")
    assert google["title"] == "Os Lusiadas : poema epico"
    assert google["thumbnail_url"].startswith("https://")


async def test_hathitrust_runs_with_an_isbn(
    client: AsyncClient, external_services: respx.MockRouter
) -> None:
    body = (await client.get(SEARCH_URL, params={"isbn": "0198157827"})).json()
    hathi = [copy for copy in body["copies"] if copy["source_id"] == "hathitrust"]

    assert [copy["access"] for copy in hathi] == ["free", "restricted"]


async def test_a_failing_source_does_not_fail_the_search(
    client: AsyncClient, fake_searcher: FakeTargetSearcher, external_services: respx.MockRouter
) -> None:
    fake_searcher.results = {"bnp": Z3950Error("connect: Timeout")}
    external_services.get(url__startswith="https://books.example.invalid/").mock(
        return_value=httpx.Response(429, json={"error": {"code": 429}})
    )

    response = await client.get(SEARCH_URL, params={"title": "lusiadas"})

    sources = by_source(response.json())
    assert response.status_code == 200
    assert sources["bnd"]["status"] == "failed"
    assert sources["google-books"]["status"] == "failed"
    assert "429" in str(sources["google-books"]["error"])
    assert sources["internet-archive"]["status"] == "ok"


async def test_results_are_cached(client: AsyncClient, external_services: respx.MockRouter) -> None:
    await client.get(SEARCH_URL, params={"title": "lusiadas"})
    calls_after_first_search = external_services.calls.call_count

    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()

    assert external_services.calls.call_count == calls_after_first_search
    assert by_source(body)["internet-archive"]["from_cache"] is True


async def test_mock_mode_answers_with_samples(mock_client: AsyncClient) -> None:
    body = (await mock_client.get(SEARCH_URL, params={"title": "x"})).json()

    assert {copy["access"] for copy in body["copies"]} == {"free", "restricted"}
    assert by_source(body)["europeana"]["status"] == "skipped"
