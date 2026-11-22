"""Text clean-up and ISBN normalisation, the small rules the conversion and dedup rely on."""

import pytest

from faisca.modules.records.isbn import (
    extract_isbn,
    normalize_isbn,
    split_isbn_qualifier,
    to_isbn13,
)
from faisca.modules.records.text_cleanup import (
    NON_SORT_END,
    NON_SORT_START,
    mark_non_sort_prefix,
    normalize_text,
    remove_non_sort_markers,
    strip_isbd_punctuation,
)


@pytest.mark.parametrize(
    ("marc21_value", "expected"),
    [
        ("Lisboa :", "Lisboa"),
        ("Os Lusiadas /", "Os Lusiadas"),
        ("Porto Editora,", "Porto Editora"),
        ("1981.", "1981"),
        ("547 p. ;", "547 p."),
        ("22 cm.", "22 cm"),
        ("3ª ed.", "3ª ed."),
        ("[s.l.]", "[s.l.]"),
        ("Camões, Luís de, 1524?-1580.", "Camões, Luís de, 1524?-1580"),
        ("Pessoa, F.", "Pessoa, F."),
        ("E depois...", "E depois..."),
    ],
)
def test_strip_isbd_punctuation(marc21_value: str, expected: str) -> None:
    assert strip_isbd_punctuation(marc21_value) == expected


def test_normalize_text_composes_accents_and_standardises_markers() -> None:
    decomposed = "Lusíadas"
    legacy_markers = "\u0088Os \u0089Lusiadas"

    assert normalize_text(decomposed) == "Lusíadas"
    assert normalize_text(legacy_markers) == f"{NON_SORT_START}Os {NON_SORT_END}Lusiadas"


def test_non_sort_prefix_is_marked_and_removed_for_display() -> None:
    marked = mark_non_sort_prefix("Os Lusíadas", 3)

    assert marked == f"{NON_SORT_START}Os {NON_SORT_END}Lusíadas"
    assert remove_non_sort_markers(marked) == "Os Lusíadas"
    assert mark_non_sort_prefix("Lusíadas", 0) == "Lusíadas"


@pytest.mark.parametrize(
    ("value", "isbn13"),
    [
        ("0-19-815782-7 (pbk.)", "9780198157823"),
        ("0198157827", "9780198157823"),
        ("978-0-19-815782-3", "9780198157823"),
        ("ISBN 9789720038814 : 12 EUR", "9789720038814"),
    ],
)
def test_normalize_isbn(value: str, isbn13: str) -> None:
    assert normalize_isbn(value) == isbn13


def test_extract_isbn_returns_none_without_one() -> None:
    assert extract_isbn("sem número") is None
    assert to_isbn13("9789720038814") == "9789720038814"


def test_split_isbn_qualifier() -> None:
    assert split_isbn_qualifier("9780198157823 (pbk.)") == ("9780198157823", "pbk.")
    assert split_isbn_qualifier("9780198157823") == ("9780198157823", None)
