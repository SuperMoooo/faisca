"""targets.yaml validation, the target list, and the live reachability check (mocked)."""

from pathlib import Path

import httpx
import pytest
import respx
from httpx import AsyncClient

from faisca.modules.targets.public import TargetsFileError, load_targets


def test_the_repository_targets_file_is_valid(repository_targets_file: Path) -> None:
    config = load_targets(repository_targets_file)

    catalogue_ids = [target.id for target in config.catalogues]
    assert catalogue_ids[:2] == ["porbase", "bnp"]  # Portuguese first: they lead every group
    assert {"bnf", "loc", "bne", "sbn"} <= set(catalogue_ids)
    assert config.catalogue("dnb") is not None and not config.catalogue("dnb").enabled  # type: ignore[union-attr]
    bnd = next(source for source in config.digital_sources if source.id == "bnd")
    assert config.catalogue(bnd.catalogue_target or "") is not None


def test_a_missing_file_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(TargetsFileError, match="not found"):
        load_targets(tmp_path / "targets.yaml")


def test_a_z3950_target_without_host_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "targets.yaml"
    path.write_text(
        "catalogues:\n"
        "  - {id: x, name: X, country: PT, protocol: z3950, format: unimarc}\n"
        "digital_sources: []\n",
        encoding="utf-8",
    )

    with pytest.raises(TargetsFileError, match="needs host, port, database"):
        load_targets(path)


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    target = (
        "{id: x, name: X, country: PT, protocol: z3950, format: unimarc,"
        " host: h, port: 1, database: d}"
    )
    path = tmp_path / "targets.yaml"
    path.write_text(
        f"catalogues:\n  - {target}\n  - {target}\ndigital_sources: []\n", encoding="utf-8"
    )

    with pytest.raises(TargetsFileError, match="Duplicate target ids"):
        load_targets(path)


async def test_the_list_shows_every_target_but_never_a_password(client: AsyncClient) -> None:
    response = await client.get("/api/v1/targets")

    body = response.json()
    assert response.status_code == 200
    assert [target["id"] for target in body["catalogues"]] == [
        "porbase",
        "bnp",
        "loc",
        "k10plus",
        "dnb",
    ]
    assert body["catalogues"][0]["endpoint"] == "z3950.example.invalid:210/porbase"
    assert "secret-password" not in response.text
    assert {target["kind"] for target in body["digital_sources"]} == {"digital"}


async def test_status_reports_reachable_blocked_unreachable_and_disabled(
    client: AsyncClient,
) -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://sru.example.invalid/loc").mock(
            return_value=httpx.Response(200)
        )
        router.get(url__startswith="https://sru.example.invalid/k10plus").mock(
            return_value=httpx.Response(403)
        )
        router.get(url__startswith="https://archive.example.invalid/").mock(
            side_effect=httpx.ConnectError("down")
        )
        router.get(url__regex=r"https://.*").mock(return_value=httpx.Response(200))

        response = await client.get("/api/v1/targets/status")

    statuses = {status["id"]: status for status in response.json()["statuses"]}
    assert statuses["loc"]["reachability"] == "reachable"
    assert statuses["k10plus"]["reachability"] == "blocked"
    assert statuses["k10plus"]["detail"] == "HTTP 403"
    assert statuses["internet-archive"]["reachability"] == "unreachable"
    assert statuses["dnb"]["reachability"] == "disabled"
    assert statuses["gallica"]["reachability"] == "disabled"
    # z3950.example.invalid does not resolve: the TCP check reports it down.
    assert statuses["porbase"]["reachability"] == "unreachable"


async def test_mock_status_marks_enabled_targets_reachable(mock_client: AsyncClient) -> None:
    statuses = (await mock_client.get("/api/v1/targets/status")).json()["statuses"]

    assert {status["reachability"] for status in statuses} == {"reachable", "disabled"}
