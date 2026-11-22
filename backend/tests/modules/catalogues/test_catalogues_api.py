"""The catalogue search API: parallel targets, partial results, dedup, cache, record views."""

import io
from typing import Any

from httpx import AsyncClient
from pymarc import MARCReader

from faisca.modules.catalogues.searcher import RawTargetResult
from faisca.modules.catalogues.sru import SruError
from faisca.modules.catalogues.z3950 import Z3950Error
from tests.helpers import FakeTargetSearcher, first_fixture_record, read_fixture_records

SEARCH_URL = "/api/v1/catalogues/search"


def canned(filename: str, hit_count: int = 100) -> RawTargetResult:
    return RawTargetResult(hit_count=hit_count, marcxml_records=read_fixture_records(filename))


def outcomes(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {outcome["target_id"]: outcome for outcome in body["targets"]}


async def test_searches_every_enabled_target_and_reports_each_outcome(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    fake_searcher.results = {
        "porbase": canned("z3950_porbase_lusiadas.xml", 1829),
        "bnp": Z3950Error("connect: Timeout [code 10007]"),
        "loc": canned("sru_loc_lusiadas.xml", 2),
        "k10plus": SruError("HTTP 503"),
    }

    response = await client.get(SEARCH_URL, params={"title": "lusiadas"})

    assert response.status_code == 200
    body = response.json()
    by_target = outcomes(body)
    # The disabled DNB target is never asked.
    assert sorted(fake_searcher.searched) == ["bnp", "k10plus", "loc", "porbase"]
    assert by_target["porbase"]["status"] == "ok"
    assert by_target["porbase"]["hit_count"] == 1829
    assert by_target["porbase"]["returned_count"] == 2
    assert by_target["bnp"]["status"] == "timed_out"
    assert by_target["k10plus"]["status"] == "failed"
    assert by_target["k10plus"]["error"] == "HTTP 503"
    assert body["record_count"] == 3


async def test_results_keep_targets_yaml_order_and_mark_the_source_format(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    fake_searcher.results = {
        "porbase": canned("z3950_porbase_lusiadas.xml"),
        "loc": canned("sru_loc_lusiadas.xml"),
    }

    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()
    records = [record for group in body["groups"] for record in group["records"]]

    assert [record["target_id"] for record in records] == ["porbase", "porbase", "loc"]
    assert records[0]["source_format"] == "unimarc"
    assert records[-1]["source_format"] == "marc21"
    assert records[-1]["description"]["isbns"] == ["9780198157823"]


async def test_the_same_book_from_two_targets_is_one_group(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    loc_record = first_fixture_record("sru_loc_lusiadas.xml")
    fake_searcher.results = {
        "loc": RawTargetResult(hit_count=1, marcxml_records=[loc_record]),
        "k10plus": RawTargetResult(hit_count=1, marcxml_records=[loc_record]),
    }

    body = (await client.get(SEARCH_URL, params={"isbn": "0198157827"})).json()

    assert len(body["groups"]) == 1
    assert [record["target_id"] for record in body["groups"][0]["records"]] == ["loc", "k10plus"]


async def test_a_repeated_search_is_served_from_the_cache(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    fake_searcher.results = {
        "loc": canned("sru_loc_lusiadas.xml"),
        "k10plus": SruError("HTTP 503"),
    }
    await client.get(SEARCH_URL, params={"title": "Lusiadas"})
    fake_searcher.searched.clear()

    body = (await client.get(SEARCH_URL, params={"title": "lusiadas "})).json()

    # LoC answered and is cached; K10plus failed and is asked again.
    assert outcomes(body)["loc"]["from_cache"] is True
    assert "loc" not in fake_searcher.searched
    assert "k10plus" in fake_searcher.searched


async def test_targets_can_be_chosen(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    response = await client.get(SEARCH_URL, params={"title": "lusiadas", "targets": ["loc"]})

    assert response.status_code == 200
    assert fake_searcher.searched == ["loc"]


async def test_an_unknown_target_is_a_bad_request(client: AsyncClient) -> None:
    response = await client.get(SEARCH_URL, params={"title": "x", "targets": ["nowhere"]})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unknown_target"


async def test_a_search_needs_a_title_author_or_isbn(client: AsyncClient) -> None:
    assert (await client.get(SEARCH_URL, params={"year": "1981"})).status_code == 422
    assert (await client.get(SEARCH_URL, params={"title": "  "})).status_code == 422
    assert (await client.get(SEARCH_URL, params={"title": "x", "year": "81"})).status_code == 422


async def test_record_detail_shows_unimarc_and_the_marc21_original(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    fake_searcher.results = {"loc": canned("sru_loc_lusiadas.xml")}
    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()
    record_id = body["groups"][0]["records"][0]["id"]

    detail = (await client.get(f"/api/v1/records/{record_id}")).json()

    unimarc_tags = [field["tag"] for field in detail["unimarc"]["fields"]]
    original_tags = [field["tag"] for field in detail["original"]["fields"]]
    assert detail["unimarc"]["format"] == "unimarc"
    assert "200" in unimarc_tags and "245" not in unimarc_tags
    assert detail["original"]["format"] == "marc21"
    assert "245" in original_tags


async def test_native_unimarc_records_have_no_original(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    fake_searcher.results = {"porbase": canned("z3950_porbase_lusiadas.xml")}
    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()
    record_id = body["groups"][0]["records"][0]["id"]

    detail = (await client.get(f"/api/v1/records/{record_id}")).json()

    assert detail["original"] is None


async def test_a_record_downloads_as_iso2709(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    fake_searcher.results = {"loc": canned("sru_loc_lusiadas.xml")}
    body = (await client.get(SEARCH_URL, params={"title": "lusiadas"})).json()
    record_id = body["groups"][0]["records"][0]["id"]

    unimarc = await client.get(f"/api/v1/records/{record_id}/iso2709")
    original = await client.get(
        f"/api/v1/records/{record_id}/iso2709", params={"variant": "original"}
    )

    assert unimarc.headers["content-type"] == "application/marc"
    assert "unimarc.mrc" in unimarc.headers["content-disposition"]
    assert "marc21.mrc" in original.headers["content-disposition"]
    [record] = list(MARCReader(io.BytesIO(unimarc.content), force_utf8=True))
    assert record["200"] is not None


async def test_an_expired_record_is_fetched_again_by_its_control_number(
    client: AsyncClient, fake_searcher: FakeTargetSearcher
) -> None:
    loc_record = first_fixture_record("sru_loc_lusiadas.xml")
    fake_searcher.records_by_control_number = {"2315102": loc_record}
    # "loc.n" + base64url("2315102"): never searched, so not in the cache.
    record_id = "loc.nMjMxNTEwMg"

    response = await client.get(f"/api/v1/records/{record_id}")

    assert response.status_code == 200
    assert response.json()["summary"]["description"]["title"].endswith("Lusiadas")


async def test_unknown_or_malformed_record_ids_are_404(client: AsyncClient) -> None:
    for record_id in ("loc.nMjMxNTEwMg", "nowhere.nMQ", "not-an-id", "loc.hdeadbeef"):
        response = await client.get(f"/api/v1/records/{record_id}")

        assert response.status_code == 404, record_id
        assert response.json()["error"]["code"] == "not_found"
