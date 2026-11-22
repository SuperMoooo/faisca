"""The UNIMARC readers, on real records: PORBASE (Z39.50, ISO 5426) and BnF (SRU MarcXchange)."""

from pymarc import Record

from faisca.modules.records.marcxml import parse_marcxml, to_marcxml
from faisca.modules.records.schemas import MarcFormat
from faisca.modules.records.text_cleanup import NON_SORT_END, NON_SORT_START
from faisca.modules.records.unimarc import (
    authors,
    declare_unicode,
    describe,
    detect_format,
    first_subfield,
    isbns,
    make_data_field,
    notes,
    physical_description,
    place_of_publication,
    publication_year,
    publisher,
    record_view,
    series,
    statement_of_responsibility,
    subjects,
    title,
)
from tests.helpers import first_fixture_record, read_fixture_records


def porbase_record() -> Record:
    return parse_marcxml(first_fixture_record("z3950_porbase_lusiadas.xml"))


def test_reads_the_title_and_responsibility_from_200() -> None:
    record = porbase_record()

    assert title(record) == 'André Baião, tradutor latino de "Os Lusíadas"'
    assert statement_of_responsibility(record) == "Amadeu Rodrigues Torres"


def test_iso5426_accents_arrive_composed() -> None:
    # YAZ decodes ISO 5426 into base letter + combining accent; NFC joins them,
    # so "ã" is one character, as BIBLIO.NET and search comparisons expect.
    assert "Baião" in title(porbase_record())
    assert "̃" not in title(porbase_record())


def test_reads_publication_without_the_old_isbd_commas() -> None:
    record = porbase_record()

    assert place_of_publication(record) == "Ponta Delgada"
    assert publisher(record) == "Univ. Açores"
    assert publication_year(record) == "1984"


def test_reads_names_from_70x_as_surname_forename_dates() -> None:
    assert authors(porbase_record()) == ["Torres, Amadeu, 1924-2012"]


def test_reads_physical_description_in_isbd_order() -> None:
    assert physical_description(porbase_record()) == "p. 659-705 ; 25 cm"


def test_reads_notes_from_3xx() -> None:
    assert notes(porbase_record()) == ["Sep. Actas - IV Reuniäo Intern. de Camonistas"]


def test_reads_the_bnf_marcxchange_record() -> None:
    record = parse_marcxml(first_fixture_record("sru_bnf_lusiadas.xml"))

    description = describe(record)

    assert detect_format(record) is MarcFormat.UNIMARC
    assert "Lusiadas" in description.title
    assert description.authors
    assert description.year is not None


def test_isbns_are_normalised_to_isbn13_without_duplicates() -> None:
    record = Record()
    record.fields.append(make_data_field("010", [("a", "0-19-815782-7"), ("b", "pbk.")]))
    record.fields.append(make_data_field("010", [("a", "9780198157823")]))

    assert isbns(record) == ["9780198157823"]


def test_title_drops_the_non_sort_markers_but_keeps_the_article() -> None:
    record = Record()
    record.fields.append(
        make_data_field("200", [("a", f"{NON_SORT_START}Os {NON_SORT_END}Lusíadas")], "1")
    )

    assert title(record) == "Os Lusíadas"


def test_series_includes_the_volume() -> None:
    record = Record()
    record.fields.append(make_data_field("225", [("a", "Clássicos"), ("v", "12")], "2"))

    assert series(record) == "Clássicos ; 12"


def test_personal_subjects_read_as_names() -> None:
    record = Record()
    record.fields.append(
        make_data_field(
            "600",
            [
                ("a", "Camões"),
                ("b", "Luís de"),
                ("f", "1524?-1580"),
                ("x", "Crítica e interpretação"),
            ],
            indicator2="1",
        )
    )

    assert subjects(record) == ["Camões, Luís de, 1524?-1580 -- Crítica e interpretação"]


def test_declare_unicode_sets_positions_26_to_29_of_100a() -> None:
    record = porbase_record()

    declare_unicode(record)

    coded_data = first_subfield(record, "100", "a") or ""
    assert len(coded_data) == 36
    assert coded_data[26:30] == "50  "


def test_record_view_lists_tag_indicators_and_subfields() -> None:
    view = record_view(porbase_record(), MarcFormat.UNIMARC)
    title_field = next(field for field in view.fields if field.tag == "200")
    control_field = next(field for field in view.fields if field.tag == "001")

    assert title_field.indicator1 == "1"
    assert title_field.subfields[0].code == "a"
    assert control_field.data and control_field.subfields == []


def test_marcxml_round_trip_keeps_every_field() -> None:
    for marcxml in read_fixture_records("z3950_porbase_lusiadas.xml"):
        record = parse_marcxml(marcxml)

        again = parse_marcxml(to_marcxml(record))

        assert [str(field) for field in again.fields] == [str(field) for field in record.fields]
        assert str(again.leader) == str(record.leader)
