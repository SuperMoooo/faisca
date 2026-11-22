"""One adapter per kind of digital-copy source; `ADAPTERS` is how the service finds them.

A new kind of source is a module here with an `async def search_x(context,
query) -> list[DigitalCopy]`, an entry below, and a `DigitalSourceKind` value.
"""

from faisca.modules.digital.sources.bnd import search_bnd
from faisca.modules.digital.sources.common import SourceAdapter
from faisca.modules.digital.sources.europeana import search_europeana
from faisca.modules.digital.sources.gallica import search_gallica
from faisca.modules.digital.sources.google_books import search_google_books
from faisca.modules.digital.sources.hathitrust import search_hathitrust
from faisca.modules.digital.sources.internet_archive import search_internet_archive
from faisca.modules.digital.sources.open_library import search_open_library
from faisca.modules.targets.public import DigitalSourceKind

ADAPTERS: dict[DigitalSourceKind, SourceAdapter] = {
    DigitalSourceKind.BND: search_bnd,
    DigitalSourceKind.EUROPEANA: search_europeana,
    DigitalSourceKind.INTERNET_ARCHIVE: search_internet_archive,
    DigitalSourceKind.OPEN_LIBRARY: search_open_library,
    DigitalSourceKind.GOOGLE_BOOKS: search_google_books,
    DigitalSourceKind.HATHITRUST: search_hathitrust,
    DigitalSourceKind.GALLICA: search_gallica,
}
