"""PQF and CQL queries, ISBN variants, record ids and SRU response parsing."""

import pytest

from faisca.modules.catalogues.query_builder import (
    build_cql,
    build_cql_for_control_number,
    build_pqf,
    isbn_variants,
    search_words,
)
from faisca.modules.catalogues.record_ids import (
    InvalidRecordIdError,
    make_record_id,
    parse_record_id,
)
from faisca.modules.catalogues.schemas import SearchQuery
from faisca.modules.catalogues.sru import SruError, parse_search_response
from tests.helpers import RECORD_FIXTURES, build_test_targets


def test_pqf_ands_every_word_with_its_bib1_attribute() -> None:
    query = SearchQuery(title="Os Lusíadas", author="Camões", year="1880")

    assert build_pqf(query) == (
        '@and @and @attr 1=4 "Lusíadas" @attr 1=1003 "Camões" @attr 1=31 "1880"'
    )


def test_pqf_isbn_sends_both_forms() -> None:
    assert build_pqf(SearchQuery(isbn="0198157827")) == (
        '@or @attr 1=7 "0198157827" @attr 1=7 "9780198157823"'
    )


def test_cql_uses_the_targets_index_names() -> None:
    loc = build_test_targets().catalogue("loc")
    assert loc is not None

    cql = build_cql(SearchQuery(title="lusiadas", author="camoes", isbn="9780198157823"), loc)

    assert cql == (
        'dc.title = "lusiadas" and dc.creator = "camoes"'
        ' and (bath.isbn = "9780198157823" or bath.isbn = "0198157827")'
    )
    assert build_cql_for_control_number(loc, "2315102") == 'rec.id = "2315102"'


def test_cql_skips_year_when_the_target_has_no_year_index() -> None:
    loc = build_test_targets().catalogue("loc")
    assert loc is not None

    assert build_cql(SearchQuery(title="lusiadas", year="1981"), loc) == 'dc.title = "lusiadas"'


def test_short_words_are_dropped_unless_nothing_else_is_left() -> None:
    assert search_words('Os "Lusíadas" de Camões') == ["Lusíadas", "Camões"]
    assert search_words("Os") == ["Os"]


@pytest.mark.parametrize(
    ("isbn", "variants"),
    [
        ("9789720038814", ["9789720038814", "9720038810"]),
        ("9720038810", ["9720038810", "9789720038814"]),
        ("9791234567896", ["9791234567896"]),
    ],
)
def test_isbn_variants(isbn: str, variants: list[str]) -> None:
    assert isbn_variants(isbn) == variants


def test_query_cleans_isbn_and_blank_fields() -> None:
    query = SearchQuery(title="", isbn="978-972-0-03881-4")

    assert query.title is None
    assert query.isbn == "9789720038814"


def test_record_ids_round_trip() -> None:
    record_id = make_record_id("porbase", "1234567", "<record/>")

    parsed = parse_record_id(record_id)

    assert record_id == "porbase.nMTIzNDU2Nw"
    assert (parsed.target_id, parsed.control_number) == ("porbase", "1234567")


def test_records_without_001_get_a_content_hash_id() -> None:
    record_id = make_record_id("loc", None, "<record/>")

    assert record_id.startswith("loc.h")
    assert parse_record_id(record_id).control_number is None


@pytest.mark.parametrize("record_id", ["porbase", "porbase.", ".nMQ", "porbase.x1", "porbase.n%%"])
def test_malformed_record_ids_are_rejected(record_id: str) -> None:
    with pytest.raises(InvalidRecordIdError):
        parse_record_id(record_id)


def test_sru_response_gives_hit_count_and_records() -> None:
    result = parse_search_response((RECORD_FIXTURES / "sru_bne_lusiadas.xml").read_bytes())

    assert result.hit_count == 199
    assert len(result.marcxml_records) == 2
    assert result.marcxml_records[0].lstrip().startswith("<record")


def test_sru_diagnostic_without_records_is_an_error() -> None:
    response = b"""<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
      <numberOfRecords>0</numberOfRecords>
      <diagnostics><diagnostic xmlns="http://www.loc.gov/zing/srw/diagnostic/">
        <uri>info:srw/diagnostic/1/16</uri>
        <message>Unsupported index</message><details>tit</details>
      </diagnostic></diagnostics></searchRetrieveResponse>"""

    with pytest.raises(SruError, match="Unsupported index: tit"):
        parse_search_response(response)


def test_sru_zero_hits_without_diagnostic_is_an_empty_result() -> None:
    response = b"""<searchRetrieveResponse xmlns="http://www.loc.gov/zing/srw/">
      <numberOfRecords>0</numberOfRecords></searchRetrieveResponse>"""

    result = parse_search_response(response)

    assert (result.hit_count, result.marcxml_records) == (0, [])
