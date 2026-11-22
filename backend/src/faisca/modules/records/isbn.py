"""ISBN clean-up, so the same book matches whatever form each catalogue writes it in."""

import re

# An ISBN inside a subfield that may also hold hyphens, spaces and a
# qualifier: "972-0-04965-X (broch.)", "9789720049657 : 12 EUR".
_ISBN_CANDIDATE = re.compile(r"(?:97[89][\s-]?)?(?:\d[\s-]?){9}[\dXx]")


def extract_isbn(value: str) -> str | None:
    """The ISBN in [value] as bare digits (ISBN-10 or 13), or None."""
    match = _ISBN_CANDIDATE.search(value)
    if match is None:
        return None
    return re.sub(r"[\s-]", "", match.group()).upper()


def to_isbn13(isbn: str) -> str:
    """The 13-digit form of an ISBN-10, so both editions of a number compare equal."""
    if len(isbn) != 10:
        return isbn
    body = "978" + isbn[:9]
    return body + _isbn13_check_digit(body)


def _isbn13_check_digit(first_twelve_digits: str) -> str:
    # ISBN-13 check digit: weights alternate 1 and 3; the digit brings the
    # weighted sum to a multiple of 10.
    total = sum(
        int(digit) * (3 if index % 2 else 1) for index, digit in enumerate(first_twelve_digits)
    )
    return str((10 - total % 10) % 10)


def normalize_isbn(value: str) -> str | None:
    """The ISBN-13 found in [value], or None; the key used to deduplicate."""
    isbn = extract_isbn(value)
    return to_isbn13(isbn) if isbn else None


def split_isbn_qualifier(value: str) -> tuple[str, str | None]:
    """Splits "9780198157823 (pbk.)" into ISBN and qualifier, as UNIMARC 010 $a / $b keep them."""
    match = re.match(r"^\s*([\dXx-]+)\s*(?:\((.*)\))?", value)
    if match is None:
        return value.strip(), None
    qualifier = match.group(2).strip() if match.group(2) else None
    return match.group(1), qualifier
