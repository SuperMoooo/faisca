"""Reading and building UNIMARC records.

pymarc reads and writes any ISO 2709 record, but its convenience properties
(`record.title`, `record.isbn`, `record.author`) read MARC21 tags (245, 020,
100), which hold other things in UNIMARC. These helpers read the UNIMARC
tags instead: 010 ISBN, 200 title and responsibility, 205 edition,
210/214 publication, 215 physical description, 225 series, 3XX notes,
6XX subjects, 70X/71X names, 856 electronic location.
"""

import re

from pymarc import Field, Indicators, Leader, Record, Subfield

from faisca.modules.records.isbn import normalize_isbn
from faisca.modules.records.schemas import (
    BibliographicDescription,
    MarcFieldView,
    MarcFormat,
    MarcRecordView,
    MarcSubfieldView,
)
from faisca.modules.records.text_cleanup import remove_non_sort_markers

# Field 100 $a is 36 fixed positions; 26-29 name the character sets
# ("50" = ISO 10646, i.e. Unicode). See UNIMARC Bibliographic, field 100.
CODED_DATA_LENGTH = 36
UNICODE_CHARACTER_SET = "50  "

PERSONAL_NAME_TAGS = ("700", "701", "702")
CORPORATE_NAME_TAGS = ("710", "711", "712")
PERSONAL_SUBJECT_TAGS = ("600", "602")
SUBJECT_TAGS = ("600", "601", "602", "604", "605", "606", "607", "608", "610")
FOUR_DIGIT_YEAR = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")


def make_data_field(
    tag: str, subfields: list[tuple[str, str]], indicator1: str = " ", indicator2: str = " "
) -> Field:
    """A data field from (code, value) pairs, skipping empty values."""
    return Field(
        tag=tag,
        indicators=Indicators(indicator1, indicator2),
        subfields=[Subfield(code=code, value=value) for code, value in subfields if value],
    )


def make_control_field(tag: str, data: str) -> Field:
    """A control field (001-009): data, no indicators or subfields."""
    return Field(tag=tag, data=data)


def subfield_values(record: Record, tag: str, code: str) -> list[str]:
    """Every [code] subfield of every [tag] field, in record order."""
    return [
        sub.value
        for field in record.get_fields(tag)
        if not field.is_control_field()
        for sub in field.subfields
        if sub.code == code and sub.value.strip()
    ]


def first_subfield(record: Record, tag: str, code: str) -> str | None:
    """The first [code] subfield of the first [tag] field that has one."""
    values = subfield_values(record, tag, code)
    return values[0] if values else None


def isbns(record: Record) -> list[str]:
    """010 $a, normalised to ISBN-13, without duplicates, in record order."""
    found: list[str] = []
    for value in subfield_values(record, "010", "a"):
        isbn = normalize_isbn(value)
        if isbn and isbn not in found:
            found.append(isbn)
    return found


def title(record: Record) -> str:
    """200 $a (all of them, for a record with several titles by one author), markers removed."""
    titles = [remove_non_sort_markers(value) for value in subfield_values(record, "200", "a")]
    return " ; ".join(titles) if titles else "[sem título]"


def other_title_information(record: Record) -> str | None:
    """200 $e: the subtitle."""
    values = subfield_values(record, "200", "e")
    return " : ".join(values) if values else None


def statement_of_responsibility(record: Record) -> str | None:
    """200 $f (first statement) and $g (subsequent), joined with ISBD's " ; "."""
    field = _first_field(record, "200")
    if field is None:
        return None
    statements = [sub.value for sub in field.subfields if sub.code in {"f", "g"}]
    return " ; ".join(statements) if statements else None


def edition(record: Record) -> str | None:
    """205 $a: the edition statement."""
    return first_subfield(record, "205", "a")


def trim_for_display(value: str) -> str:
    """Drops the ISBD punctuation older records keep inside subfields ("Torres," → "Torres").

    Only for what the screen shows; the record itself is never changed.
    """
    return value.strip().rstrip(" ,;:/=").strip()


def _display_or_none(value: str | None) -> str | None:
    return trim_for_display(value) or None if value else None


def place_of_publication(record: Record) -> str | None:
    """210 $a, or 214 $a in records that use the newer publication field."""
    return _display_or_none(
        first_subfield(record, "210", "a") or first_subfield(record, "214", "a")
    )


def publisher(record: Record) -> str | None:
    """210 $c, or 214 $c."""
    return _display_or_none(
        first_subfield(record, "210", "c") or first_subfield(record, "214", "c")
    )


def publication_year(record: Record) -> str | None:
    """A four-digit year: 210/214 $d first, then the date in 100 $a positions 9-12."""
    for tag in ("210", "214"):
        for value in subfield_values(record, tag, "d"):
            match = FOUR_DIGIT_YEAR.search(value)
            if match:
                return match.group()
    coded_data = first_subfield(record, "100", "a") or ""
    date_one = coded_data[9:13]
    return date_one if FOUR_DIGIT_YEAR.fullmatch(date_one) else None


def physical_description(record: Record) -> str | None:
    """215 in ISBD order: extent : other details ; dimensions + accompanying material."""
    field = _first_field(record, "215")
    if field is None:
        return None
    separators = {"a": "", "c": " : ", "d": " ; ", "e": " + "}
    text = "".join(
        f"{separators.get(sub.code, ' ')}{sub.value}" for sub in field.subfields if sub.value
    )
    return text.strip(" :;+") or None


def series(record: Record) -> str | None:
    """225 $a with its volume ($v): "Clássicos ; 12"."""
    field = _first_field(record, "225")
    if field is None:
        return None
    titles = [sub.value for sub in field.subfields if sub.code == "a"]
    volumes = [sub.value for sub in field.subfields if sub.code == "v"]
    if not titles:
        return None
    return " ; ".join([titles[0], *volumes])


def notes(record: Record) -> list[str]:
    """Every 3XX $a, the general and specific notes."""
    return [
        sub.value
        for field in record.fields
        if field.tag.startswith("3") and not field.is_control_field()
        for sub in field.subfields
        if sub.code == "a"
    ]


def subjects(record: Record) -> list[str]:
    """6XX headings as "Heading -- subdivision -- subdivision".

    A person as subject (600/602) is written as a name ("Camões, Luís de,
    1524?-1580"), not one part per subfield.
    """
    headings: list[str] = []
    for field in record.fields:
        if field.tag not in SUBJECT_TAGS:
            continue
        if field.tag in PERSONAL_SUBJECT_TAGS:
            heading = [personal_name(field)]
            heading += [sub.value for sub in field.subfields if sub.code in "tjxyz" and sub.value]
        else:
            heading = [
                sub.value for sub in field.subfields if sub.code in "abcdfjtxyz" and sub.value
            ]
        parts = [trim_for_display(part) for part in heading if trim_for_display(part)]
        if parts:
            headings.append(" -- ".join(parts))
    return headings


def personal_name(field: Field) -> str:
    """A 70X name as "Camões, Luís de, 1524?-1580": entry element, rest of name, dates."""
    entry = " ".join(sub.value for sub in field.subfields if sub.code == "a")
    rest = " ".join(sub.value for sub in field.subfields if sub.code == "b")
    dates = " ".join(sub.value for sub in field.subfields if sub.code == "f")
    parts = (trim_for_display(part) for part in (entry, rest, dates))
    return ", ".join(part for part in parts if part)


def corporate_name(field: Field) -> str:
    """A 71X name with its subdivisions: "Biblioteca Nacional (Portugal). Serviço X"."""
    names = [trim_for_display(sub.value) for sub in field.subfields if sub.code in {"a", "b"}]
    qualifiers = [trim_for_display(sub.value) for sub in field.subfields if sub.code == "c"]
    text = ". ".join(names)
    return f"{text} ({', '.join(qualifiers)})" if qualifiers else text


def authors(record: Record) -> list[str]:
    """Every person and body responsible: 700/701/702, then 710/711/712."""
    names = [personal_name(field) for tag in PERSONAL_NAME_TAGS for field in record.get_fields(tag)]
    names += [
        corporate_name(field) for tag in CORPORATE_NAME_TAGS for field in record.get_fields(tag)
    ]
    return [name for name in names if name]


def languages(record: Record) -> list[str]:
    """101 $a: the language codes of the text (ISO 639-2, such as "por")."""
    return subfield_values(record, "101", "a")


def digital_links(record: Record) -> list[str]:
    """856 $u: links to an online copy or a related resource."""
    return subfield_values(record, "856", "u")


def describe(record: Record) -> BibliographicDescription:
    """Everything the results table and the compare view show, read from UNIMARC tags."""
    return BibliographicDescription(
        title=title(record),
        other_title_information=other_title_information(record),
        responsibility=statement_of_responsibility(record),
        authors=authors(record),
        edition=edition(record),
        place_of_publication=place_of_publication(record),
        publisher=publisher(record),
        year=publication_year(record),
        physical_description=physical_description(record),
        series=series(record),
        isbns=isbns(record),
        languages=languages(record),
        subjects=subjects(record),
        notes=notes(record),
        digital_links=digital_links(record),
    )


def declare_unicode(record: Record) -> None:
    """Sets 100 $a positions 26-29 to "50  ", as the record's text is now UTF-8.

    A record that came from an ISO 5426 server still says so in field 100;
    BIBLIO.NET would then decode the UTF-8 bytes as ISO 5426 and garble every
    accented letter.

    It also blanks leader/09: YAZ sets it to "a" when it recodes a record to
    UTF-8, which is MARC21's Unicode flag; in UNIMARC the position is undefined.
    """
    leader = str(record.leader).ljust(24)
    record.leader = Leader(leader[:9] + " " + leader[10:])
    field = _first_field(record, "100")
    if field is None:
        return
    for index, sub in enumerate(field.subfields):
        if sub.code != "a":
            continue
        coded = sub.value.ljust(CODED_DATA_LENGTH)
        coded = coded[:26] + UNICODE_CHARACTER_SET + coded[30:]
        field.subfields[index] = Subfield(code="a", value=coded)
        return


def detect_format(record: Record) -> MarcFormat:
    """UNIMARC or MARC21, from the tags present.

    245 (MARC21 title) and 200 (UNIMARC title) are each mandatory in their own
    format and unused in the other, which makes the title tag the most
    reliable sign. Without either, a 36-character 100 $a means UNIMARC.
    """
    if record.get_fields("200") and not record.get_fields("245"):
        return MarcFormat.UNIMARC
    if record.get_fields("245"):
        return MarcFormat.MARC21
    coded_data = first_subfield(record, "100", "a") or ""
    return MarcFormat.UNIMARC if len(coded_data) >= 30 else MarcFormat.MARC21


def record_view(record: Record, marc_format: MarcFormat) -> MarcRecordView:
    """The record as tag / indicators / subfields, for the record and compare screens."""
    fields: list[MarcFieldView] = []
    for field in record.fields:
        if field.is_control_field():
            fields.append(MarcFieldView(tag=field.tag, data=field.data or ""))
            continue
        fields.append(
            MarcFieldView(
                tag=field.tag,
                indicator1=field.indicator1,
                indicator2=field.indicator2,
                subfields=[
                    MarcSubfieldView(code=sub.code, value=sub.value) for sub in field.subfields
                ],
            )
        )
    return MarcRecordView(format=marc_format, leader=str(record.leader), fields=fields)


def control_number(record: Record) -> str | None:
    """001, the record's identifier in its own catalogue."""
    fields = record.get_fields("001")
    if not fields:
        return None
    return (fields[0].data or "").strip() or None


def _first_field(record: Record, tag: str) -> Field | None:
    fields = record.get_fields(tag)
    return fields[0] if fields else None
