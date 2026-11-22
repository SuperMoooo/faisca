"""Grouping the same book from several catalogues: ISBN first, then title + author + year."""

from faisca.modules.records.dedup import group_duplicates, work_key
from faisca.modules.records.schemas import BibliographicDescription


def book(
    title: str, isbns: list[str] | None = None, author: str | None = None, year: str | None = None
) -> BibliographicDescription:
    return BibliographicDescription(
        title=title, isbns=isbns or [], authors=[author] if author else [], year=year
    )


def titles(groups: list[list[BibliographicDescription]]) -> list[list[str]]:
    return [[item.title for item in group] for group in groups]


def group(items: list[BibliographicDescription]) -> list[list[BibliographicDescription]]:
    return group_duplicates(items, lambda item: item)


def test_records_sharing_an_isbn_are_one_book() -> None:
    groups = group(
        [
            book("Os Lusíadas", ["9789720049653"]),
            book("Lusiadas, Os", ["9789720049653", "9780198157823"]),
            book("The Lusiads", ["9780198157823"]),
        ]
    )

    assert titles(groups) == [["Os Lusíadas", "Lusiadas, Os", "The Lusiads"]]


def test_without_isbn_title_author_and_year_decide() -> None:
    groups = group(
        [
            book("Os Lusíadas", author="Camões, Luís de", year="1880"),
            book("OS LUSIADAS.", author="Camoes, Luis de, 1524?-1580", year="1880"),
            book("Os Lusíadas", author="Camões, Luís de", year="1890"),
        ]
    )

    assert titles(groups) == [["Os Lusíadas", "OS LUSIADAS."], ["Os Lusíadas"]]


def test_a_record_without_isbn_joins_the_isbn_group_with_the_same_work() -> None:
    groups = group(
        [
            book("Mensagem", ["9789720049653"], "Pessoa, Fernando", "2001"),
            book("Mensagem", None, "Pessoa, Fernando", "2001"),
        ]
    )

    assert len(groups) == 1


def test_two_different_isbns_stay_apart_even_with_the_same_work() -> None:
    # Two bindings of one edition: a cataloguer wants to see both.
    groups = group(
        [
            book("Mensagem", ["9789720049653"], "Pessoa, Fernando", "2001"),
            book("Mensagem", ["9780198157823"], "Pessoa, Fernando", "2001"),
        ]
    )

    assert len(groups) == 2


def test_work_key_ignores_accents_case_punctuation_and_the_marked_article() -> None:
    marked = BibliographicDescription(
        title="\u0098Os \u009cLusíadas!", authors=["Camões, Luís de"], year="1880"
    )
    plain = BibliographicDescription(title="LUSIADAS", authors=["CAMOES, Luis"], year="1880")

    assert work_key(marked) == work_key(plain) == "lusiadas|camoes|1880"


def test_groups_keep_first_seen_order() -> None:
    groups = group(
        [book("B", ["9780198157823"]), book("A", ["9789720049653"]), book("B2", ["9780198157823"])]
    )

    assert titles(groups) == [["B", "B2"], ["A"]]
