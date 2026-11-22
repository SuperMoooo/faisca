"""MARC21 → UNIMARC conversion for bibliographic records.

No maintained converter exists for this direction: USEMARCON (last change
2020) ships no MARC21→UNIMARC rules, and the published XSLTs and the Library
of Congress specification go the other way (UNIMARC→MARC21). This follows
the LoC tables in reverse and the IFLA UNIMARC manual.

Covered: leader, 001/005, identifiers (010, 011, 020, 035, 07X), coded data
(100, 101, 102, 105), title and responsibility (200), edition (205),
publication (210), physical description (215), series (225, 410), notes
(3XX), linking entries (4XX), uniform and variant titles (500, 51X), subjects
(60X), classification (675, 676, 680, 686), names (700-712), source (801)
and electronic location (856). Any other field is left out; the original
MARC21 record is always kept next to the converted one, for comparison.

ISBD punctuation that MARC21 stores at the end of a subfield ("Lisboa :") is
removed, because UNIMARC systems generate it from the subfield codes.
"""

from datetime import UTC, datetime

from pymarc import Field, Leader, Record

from faisca.modules.records import marc21_unimarc_tables as tables
from faisca.modules.records.isbn import split_isbn_qualifier
from faisca.modules.records.text_cleanup import (
    convert_bracketed_non_sort,
    mark_non_sort_prefix,
    strip_isbd_punctuation,
)
from faisca.modules.records.unimarc import (
    UNICODE_CHARACTER_SET,
    make_control_field,
    make_data_field,
)

Subfields = list[tuple[str, str]]

# Subfields that only carry linkage or local processing data in MARC21
# ($6 linkage to 880, $8 field link, $5 holding institution, $0 authority URI).
_LINKAGE_CODES = {"0", "1", "5", "6", "8"}

# MARC21 subject thesaurus (6XX second indicator) → UNIMARC $2 source code.
_SUBJECT_SOURCES = {
    "0": "lcsh",
    "1": "lcshac",
    "2": "mesh",
    "3": "nal",
    "5": "cash",
    "6": "rvm",
}


def convert_marc21_to_unimarc(source: Record) -> Record:
    """A new UNIMARC record with the same description as the MARC21 [source]."""
    fields: list[Field] = []
    fields += _control_fields(source)
    fields += _identifier_fields(source)
    fields += _coded_data_fields(source)
    fields += _title_field(source)
    fields += _edition_field(source)
    fields += _publication_field(source)
    fields += _physical_description_field(source)
    fields += _series_fields(source)
    fields += _note_fields(source)
    fields += _linking_fields(source)
    fields += _uniform_and_variant_title_fields(source)
    fields += _subject_fields(source)
    fields += _classification_fields(source)
    fields += _name_fields(source)
    fields += _source_fields(source)
    fields += _electronic_location_fields(source)

    target = Record()
    # A source field with only unmapped subfields (a 035 with just $9) would
    # become an empty field, which ISO 2709 importers reject.
    kept_fields = [field for field in fields if field.is_control_field() or field.subfields]
    # Stable sort: fields with the same tag keep the order they had in MARC21.
    for field in sorted(kept_fields, key=lambda field: field.tag):
        target.fields.append(field)
    # After the fields: Record() would overwrite positions 20-23 otherwise.
    target.leader = Leader(_unimarc_leader(str(source.leader)))
    return target


# ── leader and control fields ──────────────────────────────────────────────


def _unimarc_leader(marc21_leader: str) -> str:
    leader = marc21_leader.ljust(24)
    status = {"a": "c", "p": "p", "c": "c", "d": "d", "n": "n"}.get(leader[5], "n")
    record_type = tables.RECORD_TYPES.get(leader[6], "a")
    bibliographic_level = {
        "a": "a",
        "b": "a",
        "c": "c",
        "d": "m",
        "i": "i",
        "m": "m",
        "s": "s",
    }.get(leader[7], "m")
    encoding_level = tables.ENCODING_LEVELS.get(leader[17], "3")
    # 18: blank = full ISBD; MARC21 "a" (AACR2), "c" and "i" are ISBD-based.
    cataloguing_form = " " if leader[18] in {"a", "c", "i"} else "n"
    # Lengths (0-4, 12-16) are filled in when the record is written.
    return (
        f"00000{status}{record_type}{bibliographic_level}  22"
        f"00000{encoding_level}{cataloguing_form} 450 "
    )


def _control_fields(source: Record) -> list[Field]:
    fields = []
    for tag in ("001", "005"):
        for field in source.get_fields(tag):
            fields.append(make_control_field(tag, field.data or ""))
    return fields


# ── identifiers ────────────────────────────────────────────────────────────


def _identifier_fields(source: Record) -> list[Field]:
    fields: list[Field] = []
    for isbn_field in source.get_fields("020"):
        fields.append(make_data_field("010", _isbn_subfields(isbn_field)))
    for issn_field in source.get_fields("022"):
        subfields = [(code, value) for code, value in _pairs(issn_field) if code in "ayz"]
        fields.append(make_data_field("011", subfields))
    for lccn in _values(source, "010", "a"):
        # 020: national bibliography number; LC control numbers are the US one.
        fields.append(make_data_field("020", [("a", "US"), ("b", lccn.strip())]))
    for standard_number in source.get_fields("024"):
        fields.append(_standard_number_field(standard_number))
    for system_number in source.get_fields("035"):
        fields.append(make_data_field("035", [p for p in _pairs(system_number) if p[0] in "az"]))
    return fields


def _isbn_subfields(field: Field) -> Subfields:
    subfields: Subfields = []
    for code, value in _pairs(field):
        if code == "a":
            isbn, qualifier = split_isbn_qualifier(value)
            subfields.append(("a", isbn))
            if qualifier:
                subfields.append(("b", strip_isbd_punctuation(qualifier)))
        elif code == "q":
            subfields.append(("b", strip_isbd_punctuation(value.strip("()"))))
        elif code == "c":
            subfields.append(("d", strip_isbd_punctuation(value)))
        elif code == "z":
            subfields.append(("z", split_isbn_qualifier(value)[0]))
    return subfields


def _standard_number_field(field: Field) -> Field:
    # 024 first indicator: 0 ISRC → 016, 3 EAN → 073, anything else → 017.
    tag = {"0": "016", "3": "073"}.get(field.indicator1, "017")
    subfields = [(code, value) for code, value in _pairs(field) if code in "az"]
    source_code = _first_value(field, "2")
    if tag == "017" and source_code:
        subfields.append(("2", source_code))
    return make_data_field(tag, subfields)


# ── coded data: 100, 101, 102, 105 ─────────────────────────────────────────


def _coded_data_fields(source: Record) -> list[Field]:
    fixed = _fixed_length_data(source)
    fields = [make_data_field("100", [("a", _general_processing_data(source, fixed))])]
    fields.append(_language_field(source, fixed))
    country = _country_code(fixed[15:18])
    if country:
        fields.append(make_data_field("102", [("a", country)]))
    if str(source.leader).ljust(24)[6] in {"a", "t"}:
        fields.append(make_data_field("105", [("a", _textual_material_data(fixed))]))
    return fields


def _fixed_length_data(source: Record) -> str:
    fields = source.get_fields("008")
    data = (fields[0].data or "") if fields else ""
    return data.ljust(40)


def _general_processing_data(source: Record, fixed: str) -> str:
    """UNIMARC 100 $a: 36 positions describing dates, audience, languages and scripts."""
    date_entered = _full_date(fixed[0:6])
    date_type = tables.PUBLICATION_DATE_TYPES.get(fixed[6], "d")
    first_date = _date_digits(fixed[7:11])
    second_date = _date_digits(fixed[11:15])
    audience = tables.TARGET_AUDIENCES.get(fixed[22], "u")
    government = tables.GOVERNMENT_PUBLICATIONS.get(fixed[28], "y")
    cataloguing_language = (_values(source, "040", "b") or ["eng"])[0][:3].lower().ljust(3)
    return (
        f"{date_entered}{date_type}{first_date}{second_date}"
        f"{audience}  {government}0{cataloguing_language}y{UNICODE_CHARACTER_SET}    ba"
    )


def _full_date(yymmdd: str) -> str:
    """008/00-05 is a two-digit-year date; UNIMARC 100 needs four digits."""
    if not yymmdd.isdigit():
        return datetime.now(UTC).strftime("%Y%m%d")
    current_year = datetime.now(UTC).year % 100
    century = "20" if int(yymmdd[:2]) <= current_year else "19"
    return century + yymmdd


def _date_digits(value: str) -> str:
    # Unknown digits are "u" (or "|") in MARC21 and blanks in UNIMARC 100.
    return "".join(char if char.isdigit() else " " for char in value.ljust(4)[:4])


def _language_field(source: Record, fixed: str) -> Field:
    language_codes = _languages_from_041(source, "a") or [fixed[35:38].strip()]
    original_codes = _languages_from_041(source, "h")
    is_translation = bool(original_codes) or any(
        field.indicator1 == "1" for field in source.get_fields("041")
    )
    subfields = [("a", code) for code in language_codes if code]
    subfields += [("c", code) for code in original_codes]
    return make_data_field("101", subfields, indicator1="1" if is_translation else "0")


def _languages_from_041(source: Record, code: str) -> list[str]:
    codes: list[str] = []
    for value in _values(source, "041", code):
        # Older records pack several codes into one subfield: "porspa".
        codes += [value[index : index + 3] for index in range(0, len(value), 3)]
    return [language.lower() for language in codes if len(language) == 3]


def _country_code(marc_country: str) -> str | None:
    code = marc_country.strip()
    if code in tables.COUNTRY_CODES:
        return tables.COUNTRY_CODES[code]
    # US states and Canadian provinces carry the country as their last letter.
    if len(code) == 3 and code.endswith("u"):
        return "US"
    if len(code) == 3 and code.endswith("c"):
        return "CA"
    return None


def _textual_material_data(fixed: str) -> str:
    """UNIMARC 105 $a: illustrations, contents, conference, festschrift, index, form, biography."""
    illustrations = "".join(
        tables.ILLUSTRATION_CODES[char]
        for char in fixed[18:22]
        if char in tables.ILLUSTRATION_CODES
    )
    contents = "".join(
        tables.CONTENT_CODES[char] for char in fixed[24:28] if char in tables.CONTENT_CODES
    )
    return (
        f"{(illustrations or 'y')[:4]:<4}{contents[:4]:<4}"
        f"{_flag(fixed[29])}{_flag(fixed[30])}{_flag(fixed[31])}"
        f"{tables.LITERARY_FORMS.get(fixed[33], 'y')}{tables.BIOGRAPHY_CODES.get(fixed[34], 'y')}"
    )


def _flag(value: str) -> str:
    return "1" if value == "1" else "0"


# ── 200 title and statement of responsibility ──────────────────────────────


def _title_field(source: Record) -> list[Field]:
    title_fields = source.get_fields("245")
    if not title_fields:
        return []
    title = title_fields[0]
    non_filing = int(title.indicator2) if title.indicator2.isdigit() else 0
    subfields: Subfields = []
    previous_value = ""
    for code, value in _pairs(title):
        subfields += _title_subfields(code, value, previous_value, non_filing, subfields)
        previous_value = value
    return [make_data_field("200", subfields, indicator1="1")]


def _title_subfields(
    code: str, value: str, previous_value: str, non_filing: int, so_far: Subfields
) -> Subfields:
    clean = strip_isbd_punctuation(value)
    if code == "a":
        is_first_title = not any(existing_code == "a" for existing_code, _ in so_far)
        return [("a", mark_non_sort_prefix(clean, non_filing) if is_first_title else clean)]
    if code == "b":
        # "=" before $b introduces a parallel title (200 $d); ":" other title
        # information (200 $e).
        return [("d" if previous_value.rstrip().endswith("=") else "e", clean)]
    if code == "c":
        statements = [strip_isbd_punctuation(part) for part in value.split(" ; ") if part.strip()]
        return [("f", statements[0]), *[("g", statement) for statement in statements[1:]]]
    if code == "h":
        return [("b", clean.strip("[]"))]
    if code == "n":
        return [("h", clean)]
    if code == "p":
        return [("i", clean)]
    return []


# ── 205 edition, 210 publication, 215 physical description ─────────────────


def _edition_field(source: Record) -> list[Field]:
    fields = []
    for edition in source.get_fields("250"):
        subfields = []
        for code, value in _pairs(edition):
            if code == "a":
                subfields.append(("a", strip_isbd_punctuation(value)))
            elif code == "b":
                # 250 $b is usually the responsibility for this edition.
                subfields.append(("f", strip_isbd_punctuation(value.lstrip("/ "))))
        fields.append(make_data_field("205", subfields))
    return fields


def _publication_field(source: Record) -> list[Field]:
    publication = source.get_fields("260") or [
        field for field in source.get_fields("264") if field.indicator2 == "1"
    ]
    if not publication:
        publication = source.get_fields("264")[:1]
    if not publication:
        return []
    code_map = {"a": "a", "b": "c", "c": "d", "e": "e", "f": "g", "g": "h"}
    subfields = [
        (code_map[code], strip_isbd_punctuation(value))
        for code, value in _pairs(publication[0])
        if code in code_map
    ]
    has_date = any(code == "d" for code, _ in subfields)
    copyright_date = _copyright_date(source)
    if not has_date and copyright_date:
        subfields.append(("d", copyright_date))
    return [make_data_field("210", subfields)]


def _copyright_date(source: Record) -> str | None:
    for field in source.get_fields("264"):
        if field.indicator2 != "4":
            continue
        date = _first_value(field, "c")
        if date:
            # UNIMARC practice writes the copyright symbol as "cop.".
            return "cop. " + strip_isbd_punctuation(date).lstrip("©℗c ").strip()
    return None


def _physical_description_field(source: Record) -> list[Field]:
    code_map = {"a": "a", "b": "c", "c": "d", "e": "e"}
    fields = []
    for description in source.get_fields("300"):
        subfields = [
            (code_map[code], strip_isbd_punctuation(value).lstrip("+ ").strip())
            for code, value in _pairs(description)
            if code in code_map
        ]
        fields.append(make_data_field("215", subfields))
    return fields


# ── 225 / 410 series ───────────────────────────────────────────────────────


def _series_fields(source: Record) -> list[Field]:
    fields: list[Field] = []
    for statement in source.get_fields("490"):
        # 490 ind1 1: traced differently in an 8XX (UNIMARC 225 ind1 0, form
        # differs from the authorised one); 0: not traced (ind1 1).
        indicator = "0" if statement.indicator1 == "1" else "1"
        fields.append(
            make_data_field("225", _series_statement_subfields(statement), indicator1=indicator)
        )
    for traced in source.get_fields("440"):
        fields.append(make_data_field("225", _series_statement_subfields(traced), indicator1="2"))
        fields.append(_series_link(traced, title_code="a"))
    for tag in ("800", "810", "811", "830"):
        for series_entry in source.get_fields(tag):
            fields.append(_series_link(series_entry, title_code="a" if tag == "830" else "t"))
    return fields


def _series_statement_subfields(field: Field) -> Subfields:
    code_map = {"a": "a", "v": "v", "x": "x", "n": "h", "p": "i"}
    return [
        (code_map[code], strip_isbd_punctuation(value))
        for code, value in _pairs(field)
        if code in code_map
    ]


def _series_link(field: Field, title_code: str) -> Field:
    subfields: Subfields = []
    for code, value in _pairs(field):
        if code == title_code:
            subfields.append(("t", strip_isbd_punctuation(value)))
        elif code in {"v", "x"}:
            subfields.append((code, strip_isbd_punctuation(value)))
    return make_data_field("410", subfields, indicator2="0")


# ── 3XX notes ──────────────────────────────────────────────────────────────


def _note_fields(source: Record) -> list[Field]:
    fields = []
    for field in source.fields:
        if not field.tag.startswith("5") or field.is_control_field():
            continue
        text = _note_text(field)
        if not text:
            continue
        tag = tables.NOTE_TAGS.get(field.tag, "300")
        fields.append(make_data_field(tag, [("a", text)], indicator1=_note_indicator(field)))
    return fields


def _note_text(field: Field) -> str:
    parts = [value.strip() for code, value in _pairs(field) if code not in {"2", "3", "u"}]
    separator = " -- " if field.tag == "505" else " "
    return separator.join(part for part in parts if part)


def _note_indicator(field: Field) -> str:
    if field.tag == "505":
        # Contents: MARC21 0 complete / 1 incomplete / 2 partial →
        # UNIMARC 327 ind1 1 complete / 0 incomplete / 2 partial.
        return {"0": "1", "1": "0", "2": "2"}.get(field.indicator1, "1")
    if field.tag in {"506", "540"}:
        return "0" if field.tag == "506" else "1"
    return " "


# ── 4XX linking entries ────────────────────────────────────────────────────


def _linking_fields(source: Record) -> list[Field]:
    fields = []
    code_map = {"a": "a", "t": "t", "b": "e", "x": "x", "z": "y", "d": "c"}
    for marc_tag, unimarc_tag in tables.LINKING_TAGS.items():
        for link in source.get_fields(marc_tag):
            subfields = [
                (code_map[code], strip_isbd_punctuation(value))
                for code, value in _pairs(link)
                if code in code_map
            ]
            if subfields:
                fields.append(make_data_field(unimarc_tag, subfields, indicator2="1"))
    return fields


# ── 500 uniform title, 51X variant titles ──────────────────────────────────


def _uniform_and_variant_title_fields(source: Record) -> list[Field]:
    fields = []
    code_map = {"a": "a", "n": "h", "p": "i", "l": "m", "f": "k", "k": "l", "s": "q"}
    for tag, is_primary_entry in (("130", "1"), ("240", "0")):
        for uniform in source.get_fields(tag):
            subfields = [
                (code_map[code], strip_isbd_punctuation(value))
                for code, value in _pairs(uniform)
                if code in code_map
            ]
            fields.append(
                make_data_field("500", subfields, indicator1="1", indicator2=is_primary_entry)
            )
    for variant in source.get_fields("246"):
        tag = tables.VARIANT_TITLE_TAGS.get(variant.indicator2, "517")
        fields.append(make_data_field(tag, _variant_title_subfields(variant), indicator1="1"))
    for added_title in source.get_fields("740"):
        fields.append(make_data_field("517", _variant_title_subfields(added_title), indicator1="1"))
    return fields


def _variant_title_subfields(field: Field) -> Subfields:
    code_map = {"a": "a", "b": "e", "n": "h", "p": "i"}
    return [
        (code_map[code], strip_isbd_punctuation(value))
        for code, value in _pairs(field)
        if code in code_map
    ]


# ── 60X subjects ───────────────────────────────────────────────────────────


def _subject_fields(source: Record) -> list[Field]:
    fields = []
    for field in source.fields:
        if field.is_control_field():
            continue
        converted = _subject_field(field)
        if converted is not None:
            fields.append(converted)
    return fields


def _subject_field(field: Field) -> Field | None:
    subdivisions = _subject_subdivisions(field)
    if field.tag == "600":
        tag, indicators, name = _personal_name_tag("600", field)
        return make_data_field(tag, name + subdivisions, *indicators)
    if field.tag in {"610", "611"}:
        name = _corporate_name_subfields(field, is_meeting=field.tag == "611")
        indicator1 = "1" if field.tag == "611" else "0"
        return make_data_field(
            "601", name + subdivisions, indicator1, _corporate_entry_indicator(field)
        )
    if field.tag == "630":
        title_codes = {"a": "a", "n": "h", "p": "i", "l": "m", "f": "k"}
        title = [
            (title_codes[code], strip_isbd_punctuation(value))
            for code, value in _pairs(field)
            if code in title_codes
        ]
        return make_data_field("605", title + subdivisions)
    topical_tags = {"650": "606", "651": "607", "655": "608"}
    if field.tag in topical_tags:
        main = [("a", strip_isbd_punctuation(value)) for value in _field_values(field, "a")]
        return make_data_field(topical_tags[field.tag], main + subdivisions)
    if field.tag == "653":
        terms = [("a", strip_isbd_punctuation(value)) for value in _field_values(field, "a")]
        return make_data_field("610", terms, indicator1="0")
    return None


def _subject_subdivisions(field: Field) -> Subfields:
    # MARC21 $y is chronological and $z geographic; UNIMARC swaps the codes
    # ($z chronological, $y geographic). $v form → $j.
    code_map = {"x": "x", "y": "z", "z": "y", "v": "j"}
    subdivisions = [
        (code_map[code], strip_isbd_punctuation(value))
        for code, value in _pairs(field)
        if code in code_map
    ]
    source_code = _SUBJECT_SOURCES.get(field.indicator2) or _first_value(field, "2")
    if source_code:
        subdivisions.append(("2", source_code))
    return subdivisions


# ── 67X/68X classification ─────────────────────────────────────────────────


def _classification_fields(source: Record) -> list[Field]:
    fields = []
    for udc in source.get_fields("080"):
        fields.append(make_data_field("675", _classification_subfields(udc, edition_code="v")))
    for dewey in source.get_fields("082"):
        fields.append(make_data_field("676", _classification_subfields(dewey, edition_code="v")))
    for library_of_congress in source.get_fields("050"):
        subfields = [(code, value) for code, value in _pairs(library_of_congress) if code in "ab"]
        fields.append(make_data_field("680", subfields))
    for other in source.get_fields("084"):
        fields.append(make_data_field("686", _classification_subfields(other, edition_code="2")))
    return fields


def _classification_subfields(field: Field, edition_code: str) -> Subfields:
    subfields: Subfields = [("a", value.strip()) for value in _field_values(field, "a")]
    edition = _first_value(field, "2")
    if edition:
        subfields.append((edition_code, edition))
    return subfields


# ── 70X/71X names ──────────────────────────────────────────────────────────


def _name_fields(source: Record) -> list[Field]:
    fields: list[Field] = []
    for main_entry in source.get_fields("100"):
        tag, indicators, name = _personal_name_tag("700", main_entry)
        fields.append(make_data_field(tag, [*name, ("4", _relator(main_entry))], *indicators))
    for added_entry in source.get_fields("700"):
        relator = _relator(added_entry, default="")
        responsibility = "701" if relator in tables.AUTHOR_RELATORS or not relator else "702"
        tag, indicators, name = _personal_name_tag(responsibility, added_entry)
        fields.append(
            make_data_field(
                tag, [*name, ("4", relator or tables.DEFAULT_PRIMARY_RELATOR)], *indicators
            )
        )
    for tag, unimarc_tag in (("110", "710"), ("111", "710"), ("710", "711"), ("711", "711")):
        for corporate in source.get_fields(tag):
            fields.append(_corporate_name_field(corporate, unimarc_tag))
    return fields


def _personal_name_tag(base_tag: str, field: Field) -> tuple[str, tuple[str, str], Subfields]:
    """UNIMARC tag, indicators and name subfields for a MARC21 personal name.

    First indicator 3 is a family name, which UNIMARC keeps in 72X; 0 is a
    forename-only name and 1 a surname, which UNIMARC says in indicator 2.
    """
    is_family = field.indicator1 == "3"
    family_tags = {"600": "602", "700": "720", "701": "721", "702": "722"}
    tag = family_tags[base_tag] if is_family else base_tag
    form_of_name = "0" if field.indicator1 == "0" else "1"
    indicators = (" ", form_of_name) if not is_family else (" ", " ")
    return tag, indicators, _personal_name_subfields(field, split_forename=form_of_name == "1")


def _personal_name_subfields(field: Field, split_forename: bool) -> Subfields:
    subfields: Subfields = []
    code_map = {"b": "d", "c": "c", "d": "f", "q": "g", "t": "t"}
    for code, value in _pairs(field):
        if code == "a":
            subfields += _split_name(strip_isbd_punctuation(value), split_forename)
        elif code in code_map:
            subfields.append((code_map[code], strip_isbd_punctuation(value)))
    return subfields


def _split_name(name: str, split_forename: bool) -> Subfields:
    # "Camões, Luís de" → $a Camões $b Luís de (entry element / rest of name).
    if not split_forename or "," not in name:
        return [("a", name)]
    surname, forename = name.split(",", 1)
    return [("a", surname.strip()), ("b", forename.strip())]


def _corporate_name_field(field: Field, unimarc_tag: str) -> Field:
    is_meeting = field.tag in {"111", "711"}
    subfields = _corporate_name_subfields(field, is_meeting)
    relator = _relator(field, default="")
    if relator:
        subfields.append(("4", relator))
    return make_data_field(
        unimarc_tag, subfields, "1" if is_meeting else "0", _corporate_entry_indicator(field)
    )


def _corporate_name_subfields(field: Field, is_meeting: bool) -> Subfields:
    if is_meeting:
        code_map = {"a": "a", "e": "b", "n": "d", "d": "f", "c": "e"}
    else:
        code_map = {"a": "a", "b": "b", "n": "d", "d": "f", "c": "e", "g": "c"}
    return [
        (code_map[code], strip_isbd_punctuation(value))
        for code, value in _pairs(field)
        if code in code_map
    ]


def _corporate_entry_indicator(field: Field) -> str:
    # MARC21 ind1 0 inverted / 1 jurisdiction / 2 direct order is exactly
    # UNIMARC 71X ind2.
    return field.indicator1 if field.indicator1 in {"0", "1", "2"} else "2"


def _relator(field: Field, default: str = tables.DEFAULT_PRIMARY_RELATOR) -> str:
    for code_value in _field_values(field, "4"):
        relator = tables.RELATOR_CODES.get(code_value.strip().lower())
        if relator:
            return relator
    for term in _field_values(field, "e"):
        relator = tables.RELATOR_CODES.get(strip_isbd_punctuation(term).lower())
        if relator:
            return relator
    return default


# ── 801 source, 856 electronic location ────────────────────────────────────


def _source_fields(source: Record) -> list[Field]:
    fields = []
    for cataloguing_source in source.get_fields("040"):
        for code, function in (("a", "0"), ("c", "1"), ("d", "2")):
            for agency in _field_values(cataloguing_source, code):
                subfields = [("a", _agency_country(agency) or ""), ("b", agency.strip())]
                fields.append(make_data_field("801", subfields, indicator2=function))
    return fields


def _agency_country(agency: str) -> str | None:
    # MARC organization codes: "DLC" and other US codes have no prefix;
    # others start with a country prefix ("SpMaBN", "DE-101", "Sz…").
    if agency.startswith(("DLC", "DNLM", "NjP", "MH", "CtY")):
        return "US"
    prefixes = {
        "Sp": "ES",
        "DE-": "DE",
        "Gy": "DE",
        "Sz": "CH",
        "CH-": "CH",
        "Po": "PT",
        "Fr": "FR",
    }
    for prefix, country in prefixes.items():
        if agency.startswith(prefix):
            return country
    return None


def _electronic_location_fields(source: Record) -> list[Field]:
    return [
        make_data_field(
            "856",
            [(code, value) for code, value in _pairs(field) if code in "uzyq"],
            field.indicator1,
            field.indicator2,
        )
        for field in source.get_fields("856")
    ]


# ── small readers ──────────────────────────────────────────────────────────


def _pairs(field: Field) -> Subfields:
    """(code, value) for every subfield except linkage ones ($0, $5, $6, $8…).

    Every value read for conversion passes here, so this is also where
    "<<Os>>" non-sorting brackets become UNIMARC's markers.
    """
    return [
        (sub.code, convert_bracketed_non_sort(sub.value))
        for sub in field.subfields
        if sub.code not in _LINKAGE_CODES
    ]


def _field_values(field: Field, code: str) -> list[str]:
    return [sub.value for sub in field.subfields if sub.code == code and sub.value.strip()]


def _first_value(field: Field, code: str) -> str | None:
    values = _field_values(field, code)
    return values[0] if values else None


def _values(source: Record, tag: str, code: str) -> list[str]:
    return [value for field in source.get_fields(tag) for value in _field_values(field, code)]
