"""ISO 2709 files: what BIBLIO.NET imports. pymarc reads them back to prove they are well formed."""

import io

from pymarc import MARCReader

from faisca.modules.records.iso2709 import (
    FIELD_TERMINATOR,
    RECORD_TERMINATOR,
    record_to_iso2709,
    records_to_iso2709,
)
from faisca.modules.records.public import read_catalogue_record
from tests.helpers import first_fixture_record, read_fixture_records


def read_back(content: bytes) -> list[object]:
    # force_utf8: pymarc would otherwise decode as MARC-8 because UNIMARC
    # leaves leader/09 blank; the bytes are UTF-8.
    return list(MARCReader(io.BytesIO(content), to_unicode=True, force_utf8=True))


def test_record_length_and_base_address_match_the_bytes() -> None:
    record = read_catalogue_record(first_fixture_record("z3950_porbase_lusiadas.xml"))

    content = record.unimarc_iso2709()

    assert int(content[0:5]) == len(content)
    base_address = int(content[12:17])
    assert content[base_address - 1 : base_address] == FIELD_TERMINATOR
    assert content.endswith(RECORD_TERMINATOR)


def test_leader_keeps_unimarc_positions() -> None:
    content = read_catalogue_record(
        first_fixture_record("z3950_porbase_lusiadas.xml")
    ).unimarc_iso2709()
    leader = content[:24].decode("ascii")

    # 09 stays blank (MARC21 would put "a"); 10-11 and 20-23 are fixed by ISO 2709.
    assert leader[9] == " "
    assert leader[10:12] == "22"
    assert leader[20:24] == "450 "


def test_text_is_utf8_and_reads_back_identically() -> None:
    record = read_catalogue_record(first_fixture_record("z3950_porbase_lusiadas.xml"))

    content = record.unimarc_iso2709()
    [read] = read_back(content)

    assert "Baião".encode() in content
    assert read["200"]["a"] == record.unimarc["200"]["a"]  # type: ignore[index]
    assert len(read.fields) == len(record.unimarc.fields)  # type: ignore[attr-defined]


def test_converted_marc21_records_write_and_read_back() -> None:
    for filename in ("sru_loc_lusiadas.xml", "sru_bne_lusiadas.xml", "sru_k10plus_lusiaden.xml"):
        record = read_catalogue_record(first_fixture_record(filename))

        [read] = read_back(record.unimarc_iso2709())

        assert read["200"] is not None  # type: ignore[index]


def test_several_records_make_one_file() -> None:
    records = [
        read_catalogue_record(marcxml).unimarc
        for marcxml in read_fixture_records("z3950_porbase_lusiadas.xml")
    ]

    content = records_to_iso2709(records)

    assert content.count(RECORD_TERMINATOR) == len(records)
    assert len(read_back(content)) == len(records)
    assert content == b"".join(record_to_iso2709(record) for record in records)
