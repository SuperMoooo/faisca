"""MOCK_RESPONSES: the catalogue endpoints answer from samples with no network or tables."""

from httpx import AsyncClient


async def test_mock_search_returns_samples_and_a_timed_out_target(mock_client: AsyncClient) -> None:
    response = await mock_client.get("/api/v1/catalogues/search", params={"title": "anything"})

    body = response.json()
    assert response.status_code == 200
    assert response.headers["X-Mock-Response"] == "true"
    assert len(body["groups"]) == 1
    assert {outcome["status"] for outcome in body["targets"]} == {"ok", "timed_out"}


async def test_mock_records_open_and_download(mock_client: AsyncClient) -> None:
    body = (await mock_client.get("/api/v1/catalogues/search", params={"title": "x"})).json()
    marc21_sample = body["groups"][0]["records"][1]

    detail = await mock_client.get(f"/api/v1/records/{marc21_sample['id']}")
    download = await mock_client.get(f"/api/v1/records/{marc21_sample['id']}/iso2709")

    assert detail.status_code == 200
    assert detail.json()["original"]["format"] == "marc21"
    assert download.content.endswith(b"\x1d")


async def test_mock_unknown_record_is_404(mock_client: AsyncClient) -> None:
    assert (await mock_client.get("/api/v1/records/loc.nOTk5")).status_code == 404
