"""Grouping the same book found in several catalogues.

Rule, in order:
1. Records sharing any ISBN (compared as ISBN-13) are the same book.
2. A record without ISBN joins the group with the same work key, the
   normalised title + first author's entry element + year, or starts one.

ISBN comes first because it is exact; the work key only fills in for older
books and records that lack one. Two ISBN records are never merged through
the work key alone: different ISBNs with the same title, author and year are
usually two bindings or printings, which a cataloguer wants to see apart.
"""

from collections.abc import Callable, Sequence

from faisca.modules.records.schemas import BibliographicDescription
from faisca.modules.records.text_cleanup import fold_for_matching

# Only so many characters of the title count: catalogues truncate long
# subtitles differently, but agree on how a title starts.
TITLE_KEY_LENGTH = 60


def work_key(description: BibliographicDescription) -> str:
    """Normalised title + first author's entry element + year: "lusiadas|camoes|1572"."""
    title = fold_for_matching(description.title)[:TITLE_KEY_LENGTH]
    author = ""
    if description.authors:
        # The entry element is what comes before the first comma: the surname
        # in "Camões, Luís de", the whole name for a corporate body.
        author = fold_for_matching(description.authors[0].split(",")[0])
    return f"{title}|{author}|{description.year or ''}"


def group_duplicates[Item](
    items: Sequence[Item], describe: Callable[[Item], BibliographicDescription]
) -> list[list[Item]]:
    """[items] in groups of the same book, groups and members in first-seen order."""
    groups: list[list[Item]] = []
    group_by_isbn: dict[str, int] = {}
    group_by_work_key: dict[str, int] = {}

    for item in items:
        description = describe(item)
        key = work_key(description)
        group_index = _find_group(description, key, group_by_isbn, group_by_work_key)
        if group_index is None:
            group_index = len(groups)
            groups.append([])
        groups[group_index].append(item)
        for isbn in description.isbns:
            group_by_isbn.setdefault(isbn, group_index)
        group_by_work_key.setdefault(key, group_index)
    return groups


def _find_group(
    description: BibliographicDescription,
    key: str,
    group_by_isbn: dict[str, int],
    group_by_work_key: dict[str, int],
) -> int | None:
    for isbn in description.isbns:
        if isbn in group_by_isbn:
            return group_by_isbn[isbn]
    if description.isbns:
        return None
    return group_by_work_key.get(key)
