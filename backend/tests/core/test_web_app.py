"""Serving the exported Next.js app: pages, 404 page, and client-navigation payloads."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from faisca.core.web_app import nested_payload_path
from faisca.main import create_app
from tests.helpers import build_test_targets, make_test_settings


@pytest.mark.parametrize(
    ("requested", "on_disk"),
    [
        ("cesto/__next.cesto.__PAGE__.txt", "cesto/__next.cesto/__PAGE__.txt"),
        ("a/b/__next.a.b.__PAGE__.txt", "a/b/__next.a/b/__PAGE__.txt"),
        ("__next.__PAGE__.txt", None),
        ("cesto/index.txt", None),
        ("_next/static/app.js", None),
    ],
)
def test_nested_payload_path(requested: str, on_disk: str | None) -> None:
    assert nested_payload_path(requested) == on_disk


@pytest.fixture
def exported_site(tmp_path: Path) -> Path:
    (tmp_path / "index.html").write_text("<h1>Pesquisa</h1>", encoding="utf-8")
    (tmp_path / "404.html").write_text("<h1>Não existe</h1>", encoding="utf-8")
    (tmp_path / "cesto" / "__next.cesto").mkdir(parents=True)
    (tmp_path / "cesto" / "index.html").write_text("<h1>Cesto</h1>", encoding="utf-8")
    (tmp_path / "cesto" / "__next.cesto" / "__PAGE__.txt").write_text("payload", encoding="utf-8")
    return tmp_path


async def test_the_app_serves_the_export_after_the_api(exported_site: Path) -> None:
    app = create_app(make_test_settings(web_dist_dir=exported_site), targets=build_test_targets())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        home = await client.get("/")
        basket_page = await client.get("/cesto/")
        payload = await client.get("/cesto/__next.cesto.__PAGE__.txt?_rsc=abc")
        missing = await client.get("/nada/")
        health = await client.get("/health")

    assert "Pesquisa" in home.text
    assert "Cesto" in basket_page.text
    assert payload.text == "payload"
    assert missing.status_code == 404 and "Não existe" in missing.text
    assert health.json() == {"status": "ok"}
    await app.state.http_client.aclose()
