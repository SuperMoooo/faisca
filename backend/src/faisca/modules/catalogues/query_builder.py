"""Turning a search form into each protocol's query language: PQF (Z39.50) and CQL (SRU).

Both search word by word, every word required ("os lusiadas camoes" finds
records with all three words), which is what library OPACs do and what every
tested server supports. A phrase search depends on each server's indexing.
"""

import re

from faisca.modules.catalogues.schemas import SearchQuery
from faisca.modules.targets.public import CatalogueTarget, SruIndexes

# Bib-1 "use" attributes, the Z39.50 equivalent of index names.
BIB1_TITLE = 4
BIB1_AUTHOR = 1003
BIB1_ISBN = 7
BIB1_LOCAL_NUMBER = 12
BIB1_DATE_OF_PUBLICATION = 31

# Articles and particles ("os", "de", "la") are stop words on most servers:
# one in an AND query can make it match nothing. Words this short are dropped
# unless nothing else is left.
MIN_WORD_LENGTH = 3


def search_words(text: str) -> list[str]:
    """The words of [text] worth sending, without quotes or query syntax characters."""
    words = re.findall(r"[^\s\"\\()=<>/,;:.!?]+", text)
    long_words = [word for word in words if len(word) >= MIN_WORD_LENGTH]
    return long_words or words


def isbn_variants(isbn: str) -> list[str]:
    """The ISBN as typed plus its other form (10 ↔ 13 digits).

    Some catalogues (BnF) match only the form the book was catalogued with,
    so both are sent, joined with OR.
    """
    variants = [isbn]
    if len(isbn) == 13 and isbn.startswith("978"):
        variants.append(_isbn10_from_isbn13(isbn))
    elif len(isbn) == 10:
        variants.append(_isbn13_from_isbn10(isbn))
    return variants


def _isbn10_from_isbn13(isbn13: str) -> str:
    body = isbn13[3:12]
    # ISBN-10 check digit: weights 10 down to 2; remainder 10 is written "X".
    total = sum(int(digit) * weight for digit, weight in zip(body, range(10, 1, -1), strict=True))
    check = (11 - total % 11) % 11
    return body + ("X" if check == 10 else str(check))


def _isbn13_from_isbn10(isbn10: str) -> str:
    body = "978" + isbn10[:9]
    total = sum(int(digit) * (3 if index % 2 else 1) for index, digit in enumerate(body))
    return body + str((10 - total % 10) % 10)


# ── PQF (Z39.50) ───────────────────────────────────────────────────────────


def build_pqf(query: SearchQuery) -> str:
    """The query in Prefix Query Format: '@and @attr 1=4 "lusiadas" @attr 1=1003 "camoes"'."""
    clauses: list[str] = []
    if query.title:
        clauses += [_pqf_term(BIB1_TITLE, word) for word in search_words(query.title)]
    if query.author:
        clauses += [_pqf_term(BIB1_AUTHOR, word) for word in search_words(query.author)]
    if query.isbn:
        clauses.append(
            _pqf_or([_pqf_term(BIB1_ISBN, variant) for variant in isbn_variants(query.isbn)])
        )
    if query.year:
        clauses.append(_pqf_term(BIB1_DATE_OF_PUBLICATION, query.year))
    return _pqf_and(clauses)


def build_pqf_for_control_number(control_number: str) -> str:
    """Finds one record by its 001 (Bib-1 "local number")."""
    return _pqf_term(BIB1_LOCAL_NUMBER, control_number)


def _pqf_term(use_attribute: int, term: str) -> str:
    clean = term.replace('"', "").replace("\\", "")
    return f'@attr 1={use_attribute} "{clean}"'


def _pqf_and(clauses: list[str]) -> str:
    # PQF is prefix notation: n clauses need n-1 "@and" operators in front.
    return " ".join(["@and"] * (len(clauses) - 1) + clauses)


def _pqf_or(clauses: list[str]) -> str:
    return " ".join(["@or"] * (len(clauses) - 1) + clauses)


# ── CQL (SRU) ──────────────────────────────────────────────────────────────


def build_cql(query: SearchQuery, target: CatalogueTarget) -> str:
    """The query in CQL with this target's index names: 'alma.title="lusiadas" and …'."""
    indexes = _indexes(target)
    relation = target.relation
    clauses: list[str] = []
    if query.title:
        clauses += [_cql_term(indexes.title, relation, word) for word in search_words(query.title)]
    if query.author:
        clauses += [
            _cql_term(indexes.author, relation, word) for word in search_words(query.author)
        ]
    if query.isbn:
        variants = [_cql_term(indexes.isbn, relation, isbn) for isbn in isbn_variants(query.isbn)]
        clauses.append("(" + " or ".join(variants) + ")")
    if query.year and indexes.year:
        clauses.append(_cql_term(indexes.year, relation, query.year))
    return " and ".join(clauses)


def build_cql_for_control_number(target: CatalogueTarget, control_number: str) -> str | None:
    """Finds one record by its 001, or None when the target has no such index."""
    index = _indexes(target).control_number
    if index is None:
        return None
    return _cql_term(index, target.relation, control_number)


def _cql_term(index: str, relation: str, term: str) -> str:
    clean = term.replace('"', "").replace("\\", "")
    return f'{index} {relation} "{clean}"'


def _indexes(target: CatalogueTarget) -> SruIndexes:
    if target.indexes is None:
        raise ValueError(f"SRU target {target.id} has no indexes configured.")
    return target.indexes
