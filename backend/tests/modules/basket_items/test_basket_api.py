"""The export basket: add records from searches, remove, empty, export one ISO 2709 file."""

import io

from httpx import AsyncClient
from pymarc import MARCReader
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from faisca.modules.cached_responses.models import CachedResponse
from faisca.modules.catalogues.searcher import RawTargetResult
from tests.helpers import FakeTargetSearcher, read_fixture_records

BASKET_URL = "/api/v1/basket"


async def search_record_ids(client: AsyncClient, fake_searcher: FakeTargetSearcher) -> list[str]:
    """Runs a search with one UNIMARC and one MARC21 target; the ids of what came back."""
    fake_searcher.results = {
        "porbase": RawTargetResult(1, read_fixture_records("z3950_porbase_lusiadas.xml")),
        "loc": RawTargetResult(1, read_fixture_records("sru_loc_lusiadas.xml")),
    }
    body = (await client.get("/api/v1/catalogues/search", params={"title": "lusiadas"})).json()
    return [record["id"] for group in body["groups"] for record in group["records"]]


async def test_an_empty_basket(client: AsyncClient) -> None:
    response = await client.get(BASKET_URL)

    assert response.json() == {"items": [], "count": 0}


async def test_adding_a_record_stores_its_description(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    record_ids = await search_record_ids(client, fake_searcher)

    response = await client.post(BASKET_URL, json={"record_id": record_ids[-1]})

    item = response.json()
    assert response.status_code == 201
    assert item["record_id"] == record_ids[-1]
    assert item["source_format"] == "marc21"
    assert item["target_name"] == "Library of Congress"
    assert item["authors"][0].startswith("Camões")


async def test_adding_the_same_record_twice_keeps_one(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    record_id = (await search_record_ids(client, fake_searcher))[0]

    first = await client.post(BASKET_URL, json={"record_id": record_id})
    second = await client.post(BASKET_URL, json={"record_id": record_id})

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert (await client.get(BASKET_URL)).json()["count"] == 1


async def test_adding_an_unknown_record_is_404(client: AsyncClient) -> None:
    response = await client.post(BASKET_URL, json={"record_id": "loc.nOTk5OTk"})

    assert response.status_code == 404


async def test_export_is_one_utf8_unimarc_file_in_basket_order(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    record_ids = await search_record_ids(client, fake_searcher)
    for record_id in record_ids:
        await client.post(BASKET_URL, json={"record_id": record_id})

    response = await client.get(f"{BASKET_URL}/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/marc"
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="faisca-unimarc-'
    )
    records = list(MARCReader(io.BytesIO(response.content), force_utf8=True))
    assert len(records) == len(record_ids)
    # Every record is UNIMARC (200 title), the MARC21 one converted.
    assert all(record.get_fields("200") for record in records)
    assert not any(record.get_fields("245") for record in records)
    assert "Baião".encode() in response.content


async def test_exporting_an_empty_basket_is_404(client: AsyncClient) -> None:
    assert (await client.get(f"{BASKET_URL}/export")).status_code == 404


async def test_removing_and_emptying(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    record_ids = await search_record_ids(client, fake_searcher)
    items = [(await client.post(BASKET_URL, json={"record_id": rid})).json() for rid in record_ids]

    removed = await client.delete(f"{BASKET_URL}/{items[0]['id']}")
    removed_again = await client.delete(f"{BASKET_URL}/{items[0]['id']}")
    assert (removed.status_code, removed_again.status_code) == (204, 404)
    assert (await client.get(BASKET_URL)).json()["count"] == len(record_ids) - 1

    assert (await client.delete(BASKET_URL)).status_code == 204
    assert (await client.get(BASKET_URL)).json()["count"] == 0


async def test_the_basket_outlives_the_search_cache(
    client: AsyncClient, fake_searcher: FakeTargetSearcher, session: AsyncSession
) -> None:
    record_id = (await search_record_ids(client, fake_searcher))[0]
    await client.post(BASKET_URL, json={"record_id": record_id})
    # Empty the cache, as a day later: the basket keeps its own copy of each record.
    await session.execute(delete(CachedResponse))
    await session.commit()

    response = await client.get(f"{BASKET_URL}/export")

    assert response.status_code == 200
    assert len(list(MARCReader(io.BytesIO(response.content), force_utf8=True))) == 1


async def test_mock_basket(mock_client: AsyncClient) -> None:
    basket = (await mock_client.get(BASKET_URL)).json()
    export = await mock_client.get(f"{BASKET_URL}/export")

    assert basket["count"] == 1
    assert len(list(MARCReader(io.BytesIO(export.content), force_utf8=True))) == 1
    assert (await mock_client.delete(f"{BASKET_URL}/999")).status_code == 404
