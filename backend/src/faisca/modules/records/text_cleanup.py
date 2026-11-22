"""Text clean-up shared by every record: Unicode form, non-sorting markers, ISBD punctuation."""

import re
import unicodedata

# UNIMARC marks the part of a title that is ignored when sorting ("Os " in
# "Os Lusíadas") with NSB/NSE control characters. In Unicode records the
# UNIMARC manual uses U+0098 (START OF STRING) and U+009C (STRING TERMINATOR);
# some servers send the ISO 6630 code points U+0088/U+0089 instead.
NON_SORT_START = "\u0098"
NON_SORT_END = "\u009c"
_LEGACY_NON_SORT = {"\u0088": NON_SORT_START, "\u0089": NON_SORT_END}

# MARC21 keeps the ISBD punctuation that precedes the next subfield at the end
# of the current one ("Lisboa :", "Os Lusiadas /"). UNIMARC does not store it:
# the system generates it from the subfield codes.
_TRAILING_ISBD_PUNCTUATION = re.compile(r"[\s]*[/:;=,+]+\s*$")
# A final period is kept after an abbreviation or an initial ("ed.", "J.",
# "[s.l.]"), where it belongs to the word, not to the punctuation. A short
# word must start with a letter: "5." is a number followed by punctuation.
_ABBREVIATION_BEFORE_PERIOD = re.compile(r"(\b[^\W\d]\w{0,2}|\b[A-ZÀ-Ý]|\.\w+|\])\.$")
_UNIT_WITH_PERIOD = re.compile(r"\b(\d+\s*(?:cm|mm))\.$")


def normalize_text(value: str) -> str:
    """NFC and standard non-sorting markers.

    YAZ decodes ISO 5426 into a base letter plus combining accents
    ("e" + U+0301); NFC joins them into "é", which is what search, comparison
    and BIBLIO.NET expect.
    """
    for legacy, standard in _LEGACY_NON_SORT.items():
        value = value.replace(legacy, standard)
    return unicodedata.normalize("NFC", value)


# Alma and the German-speaking catalogues mark the non-sorting article inside
# the MARC21 text as "<<Os>> Lusíadas" instead of using 245's indicator.
_BRACKETED_NON_SORT = re.compile(r"<<(.*?)>>(\s?)")


def convert_bracketed_non_sort(value: str) -> str:
    """Turns "<<Os>> Lusíadas" into the same words with UNIMARC's markers, space inside."""
    return _BRACKETED_NON_SORT.sub(
        lambda match: f"{NON_SORT_START}{match.group(1)}{match.group(2)}{NON_SORT_END}", value
    )


def remove_non_sort_markers(value: str) -> str:
    """The title as people read it: "Os Lusíadas", markers removed, words kept."""
    return value.replace(NON_SORT_START, "").replace(NON_SORT_END, "")


def remove_non_sort_part(value: str) -> str:
    """The title as it is sorted: "Lusíadas", the marked article dropped."""
    return re.sub(f"{NON_SORT_START}.*?{NON_SORT_END}", "", value).strip()


def mark_non_sort_prefix(value: str, prefix_length: int) -> str:
    """Wraps the first [prefix_length] characters (MARC21's non-filing count) in markers."""
    if prefix_length <= 0 or prefix_length >= len(value):
        return value
    return f"{NON_SORT_START}{value[:prefix_length]}{NON_SORT_END}{value[prefix_length:]}"


def strip_isbd_punctuation(value: str) -> str:
    """Drops the punctuation MARC21 leaves at the end of a subfield ("Lisboa :" → "Lisboa")."""
    value = _TRAILING_ISBD_PUNCTUATION.sub("", value.strip())
    if value.endswith(".") and not value.endswith("...") and not _is_abbreviation_end(value):
        value = value[:-1]
    # ISBD treats "cm" and "mm" as symbols, written without a period.
    value = _UNIT_WITH_PERIOD.sub(r"\1", value)
    return value.strip()


def _is_abbreviation_end(value: str) -> bool:
    return bool(_ABBREVIATION_BEFORE_PERIOD.search(value))


def fold_for_matching(value: str) -> str:
    """Lowercase, no accents, no punctuation: the form two catalogues' titles are compared in."""
    decomposed = unicodedata.normalize("NFKD", remove_non_sort_part(value))
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    words = re.findall(r"[a-z0-9]+", without_accents.lower())
    return " ".join(words)
