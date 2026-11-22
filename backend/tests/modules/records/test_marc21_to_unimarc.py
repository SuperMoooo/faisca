"""MARC21 → UNIMARC on real records from the Library of Congress, BNE and K10plus."""

from pymarc import Field, Record

from faisca.modules.records.marc21_to_unimarc import convert_marc21_to_unimarc
from faisca.modules.records.marcxml import parse_marcxml
from faisca.modules.records.schemas import MarcFormat
from faisca.modules.records.text_cleanup import NON_SORT_END, NON_SORT_START
from faisca.modules.records.unimarc import describe, detect_format, make_data_field
from tests.helpers import first_fixture_record


def subfields(record: Record, tag: str) -> list[list[tuple[str, str]]]:
    """Every [tag] field's subfields as (code, value) pairs."""
    return [[(sub.code, sub.value) for sub in field.subfields] for field in record.get_fields(tag)]


def converted(filename: str) -> Record:
    return convert_marc21_to_unimarc(parse_marcxml(first_fixture_record(filename)))


def test_library_of_congress_record() -> None:
    record = converted("sru_loc_lusiadas.xml")

    assert detect_format(record) is MarcFormat.UNIMARC
    assert subfields(record, "010") == [
        [("a", "0198157827"), ("b", "pbk."), ("d", "$7.95 (U.S.)")],
        [("a", "9780198157823")],
    ]
    assert subfields(record, "200") == [
        [
            # LoC's 245 has 3 non-filing characters ("Os "): they become markers.
            ("a", f"{NON_SORT_START}Os {NON_SORT_END}Lusiadas"),
            ("f", "Luís de Camões"),
            ("g", "edited with an introduction and notes by Frank Pierce"),
        ]
    ]
    assert subfields(record, "210") == [
        [
            ("a", "Oxford"),
            ("c", "Clarendon Press"),
            ("a", "New York"),
            ("c", "Oxford University Press"),
            ("d", "1981"),
        ]
    ]
    assert subfields(record, "215") == [[("a", "xlv, 271 p."), ("d", "22 cm")]]
    assert subfields(record, "320") == [[("a", "Bibliography: p. xli-xliv.")]]
    assert subfields(record, "700") == [
        [("a", "Camões"), ("b", "Luís de"), ("f", "1524?-1580"), ("4", "070")]
    ]
    assert subfields(record, "701") == [
        [("a", "Pierce"), ("b", "Frank"), ("f", "1915-"), ("4", "070")]
    ]
    assert subfields(record, "676") == [[("a", "869.1/2"), ("v", "19")]]
    assert subfields(record, "680") == [[("a", "PQ9198"), ("b", ".A2 1981")]]
    assert subfields(record, "102") == [[("a", "GB")]]


def test_coded_data_field_100_has_36_positions_and_declares_unicode() -> None:
    coded_data = subfields(converted("sru_loc_lusiadas.xml"), "100")[0][0][1]

    assert len(coded_data) == 36
    assert coded_data[0:8] == "19810911"  # date entered, 008/00-05 with its century
    assert coded_data[8] == "e"  # 008/06 "r" (reprint) → "e" (reproduction)
    assert coded_data[9:17] == "19811973"
    assert coded_data[22:25] == "eng"  # language of cataloguing (040 $b, default English)
    assert coded_data[26:30] == "50  "  # ISO 10646: the record is Unicode
    assert coded_data[34:36] == "ba"  # Latin script


def test_languages_go_to_101_and_the_leader_is_unimarc() -> None:
    record = converted("sru_loc_lusiadas.xml")
    leader = str(record.leader)

    assert subfields(record, "101") == [[("a", "por"), ("a", "eng")]]
    assert leader[6:8] == "am"
    assert leader[20:24] == "450 "


def test_k10plus_record_edition_relators_and_electronic_location() -> None:
    record = converted("sru_k10plus_lusiaden.xml")

    assert subfields(record, "010") == [[("a", "9789720038814")]]
    assert subfields(record, "205")[0][0][0] == "a"
    assert subfields(record, "210") == [
        [("a", "[Porto]"), ("c", "Porto Editora"), ("d", "setembro de 2024")]
    ]
    # The illustrator becomes a secondary responsibility (702) with code 440.
    assert subfields(record, "702") == [
        [("a", "Mãe"), ("b", "Valter Hugo"), ("f", "1971-"), ("4", "440")]
    ]
    assert subfields(record, "856")[0][0] == (
        "u",
        "https://www.gbv.de/dms/sub-hamburg/1904182607.pdf",
    )
    assert ("2", "rvk") in subfields(record, "686")[1]


def test_bne_record_subjects_swap_geographic_and_chronological_codes() -> None:
    record = converted("sru_bne_lusiadas.xml")

    # MARC21 650/655 $z is geographic and $y chronological; UNIMARC swaps them.
    assert subfields(record, "608") == [
        [("a", "Positivos papel gelatina"), ("y", "España"), ("z", "S.XX"), ("2", "tgfbne")]
    ]
    assert subfields(record, "710") == [[("a", "Crismakolor (Estudio fotográfico)")]]
    assert subfields(record, "801")[0] == [("a", "ES"), ("b", "SpMaBN")]


def test_non_filing_characters_become_non_sort_markers() -> None:
    source = Record()
    source.fields.append(Field(tag="008", data=" " * 40))
    source.fields.append(
        make_data_field("245", [("a", "Os Lusíadas /"), ("c", "Luís de Camões.")], "1", "3")
    )

    title = subfields(convert_marc21_to_unimarc(source), "200")[0]

    assert title[0] == ("a", f"{NON_SORT_START}Os {NON_SORT_END}Lusíadas")
    assert title[1] == ("f", "Luís de Camões")


def test_subtitle_parallel_title_and_series() -> None:
    source = Record()
    source.fields.append(Field(tag="008", data=" " * 40))
    source.fields.append(
        make_data_field(
            "245",
            [
                ("a", "Mensagem :"),
                ("b", "poemas esotéricos ="),
                ("b", "Message /"),
                ("c", "Fernando Pessoa."),
            ],
            "1",
            "0",
        )
    )
    source.fields.append(
        make_data_field("490", [("a", "Obras de Fernando Pessoa ;"), ("v", "5")], "1")
    )
    source.fields.append(
        make_data_field("830", [("a", "Obras de Fernando Pessoa ;"), ("v", "5.")], " ", "0")
    )

    record = convert_marc21_to_unimarc(source)

    assert subfields(record, "200") == [
        [("a", "Mensagem"), ("e", "poemas esotéricos"), ("d", "Message"), ("f", "Fernando Pessoa")]
    ]
    assert subfields(record, "225") == [[("a", "Obras de Fernando Pessoa"), ("v", "5")]]
    assert record.get_fields("225")[0].indicator1 == "0"
    assert subfields(record, "410") == [[("t", "Obras de Fernando Pessoa"), ("v", "5")]]


def test_corporate_and_meeting_names() -> None:
    source = Record()
    source.fields.append(Field(tag="008", data=" " * 40))
    source.fields.append(make_data_field("245", [("a", "Actas.")], "0", "0"))
    source.fields.append(
        make_data_field(
            "111",
            [
                ("a", "Reunião Internacional de Camonistas"),
                ("n", "(4ª :"),
                ("d", "1983 :"),
                ("c", "Ponta Delgada)"),
            ],
            "2",
        )
    )
    source.fields.append(
        make_data_field("710", [("a", "Universidade dos Açores."), ("e", "editor.")], "2")
    )

    record = convert_marc21_to_unimarc(source)

    meeting = record.get_fields("710")[0]
    assert meeting.indicator1 == "1"
    assert [sub.code for sub in meeting.subfields] == ["a", "d", "f", "e"]
    secondary = record.get_fields("711")[0]
    assert secondary.indicator1 == "0"
    assert ("4", "340") in [(sub.code, sub.value) for sub in secondary.subfields]


def test_notes_map_to_specific_3xx_tags() -> None:
    source = Record()
    source.fields.append(Field(tag="008", data=" " * 40))
    source.fields.append(make_data_field("245", [("a", "Tese.")], "0", "0"))
    source.fields.append(
        make_data_field("502", [("a", "Tese (doutoramento) - Universidade de Lisboa, 1999.")])
    )
    source.fields.append(make_data_field("505", [("a", "Canto I -- Canto II.")], "0"))
    source.fields.append(make_data_field("520", [("a", "Resumo.")]))
    source.fields.append(make_data_field("546", [("a", "Texto em português.")]))
    source.fields.append(make_data_field("590", [("a", "Nota local.")]))

    record = convert_marc21_to_unimarc(source)

    assert {field.tag for field in record.fields if field.tag.startswith("3")} == {
        "300",
        "302",
        "327",
        "328",
        "330",
    }
    assert record.get_fields("327")[0].indicator1 == "1"


def test_describe_reads_the_converted_record() -> None:
    description = describe(converted("sru_loc_lusiadas.xml"))

    assert description.title == "Os Lusiadas"
    assert description.isbns == ["9780198157823"]
    assert description.authors == ["Camões, Luís de, 1524?-1580", "Pierce, Frank, 1915-"]


def test_fields_without_mapped_subfields_are_dropped() -> None:
    source = Record()
    source.fields.append(Field(tag="008", data=" " * 40))
    source.fields.append(make_data_field("245", [("a", "Título.")], "0", "0"))
    source.fields.append(make_data_field("035", [("9", "local-only")]))

    assert convert_marc21_to_unimarc(source).get_fields("035") == []


def test_alma_bracketed_articles_become_non_sort_markers() -> None:
    source = Record()
    source.fields.append(Field(tag="008", data=" " * 40))
    source.fields.append(
        make_data_field("245", [("a", "<<Os>> Lusíadas /"), ("c", "Camões.")], "1", "0")
    )
    source.fields.append(
        make_data_field("100", [("a", "Camões, Luiz <<de>>"), ("d", "1524-1580")], "1")
    )

    record = convert_marc21_to_unimarc(source)

    assert subfields(record, "200")[0][0] == ("a", f"{NON_SORT_START}Os {NON_SORT_END}Lusíadas")
    assert describe(record).title == "Os Lusíadas"
    assert "<<" not in str(record)
