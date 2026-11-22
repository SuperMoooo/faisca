"""A Z39.50 client on YAZ's ZOOM C API, called through `ctypes`.

Why ctypes: the Python Z39.50 packages (PyZ3950, PyZ3950-ng) are unmaintained
and some need a compiler. YAZ's ZOOM API is small, stable since 2001, and
shipped by every Linux distribution as `libyaz5` (Debian/Ubuntu:
`apt install libyaz5`), so nothing has to be built.

ZOOM calls block, so `search_z3950` runs them in a worker thread; ZOOM's own
`timeout` option makes sure a dead server releases that thread.
"""

import ctypes
import ctypes.util
import os
import threading
from dataclasses import dataclass

# The names the library goes by on Debian/Ubuntu, Alpine/Fedora and macOS.
LIBRARY_CANDIDATES = ("libyaz.so.5", "libyaz.so", "libyaz.5.dylib", "libyaz.dylib")


class Z3950UnavailableError(RuntimeError):
    """libyaz is not installed, so no Z39.50 target can be searched."""


class Z3950Error(RuntimeError):
    """The target refused the connection, the search or the record request."""


@dataclass(frozen=True)
class Z3950Request:
    """Everything one search needs: where, what, and how records come back."""

    host: str
    port: int
    database: str
    pqf_query: str
    record_syntax: str
    # The charset the server sends MARC records in (iso5426, marc8, utf-8).
    # YAZ recodes it to UTF-8 while turning the record into MARCXML.
    source_charset: str
    max_records: int
    timeout_seconds: int
    username: str | None = None
    password: str | None = None


@dataclass(frozen=True)
class Z3950Result:
    """How many records matched, and the first `max_records` of them as MARCXML."""

    hit_count: int
    marcxml_records: list[str]


_library: ctypes.CDLL | None = None
_library_lock = threading.Lock()


def _load_library() -> ctypes.CDLL:
    """Loads libyaz once and declares the signatures of the ZOOM calls used here."""
    global _library
    with _library_lock:
        if _library is not None:
            return _library
        library = _open_first_available_library()
        _declare_signatures(library)
        _library = library
        return library


def _open_first_available_library() -> ctypes.CDLL:
    explicit_path = os.environ.get("YAZ_LIBRARY_PATH")
    candidates = [explicit_path] if explicit_path else []
    found = ctypes.util.find_library("yaz")
    if found:
        candidates.append(found)
    candidates.extend(LIBRARY_CANDIDATES)
    for candidate in candidates:
        try:
            return ctypes.CDLL(candidate)
        except OSError:
            continue
    raise Z3950UnavailableError(
        "libyaz was not found. Install it (Debian/Ubuntu: apt install libyaz5) "
        "or set YAZ_LIBRARY_PATH."
    )


def _declare_signatures(library: ctypes.CDLL) -> None:
    # Without these declarations ctypes assumes int return values, which
    # truncates 64-bit pointers and crashes on the first call.
    pointer = ctypes.c_void_p
    text = ctypes.c_char_p
    library.ZOOM_options_create.restype = pointer
    library.ZOOM_options_set.argtypes = [pointer, text, text]
    library.ZOOM_options_destroy.argtypes = [pointer]
    library.ZOOM_connection_create.restype = pointer
    library.ZOOM_connection_create.argtypes = [pointer]
    library.ZOOM_connection_connect.argtypes = [pointer, text, ctypes.c_int]
    library.ZOOM_connection_error.restype = ctypes.c_int
    library.ZOOM_connection_error.argtypes = [
        pointer,
        ctypes.POINTER(text),
        ctypes.POINTER(text),
    ]
    library.ZOOM_connection_search_pqf.restype = pointer
    library.ZOOM_connection_search_pqf.argtypes = [pointer, text]
    library.ZOOM_connection_destroy.argtypes = [pointer]
    library.ZOOM_resultset_size.restype = ctypes.c_size_t
    library.ZOOM_resultset_size.argtypes = [pointer]
    library.ZOOM_resultset_record.restype = pointer
    library.ZOOM_resultset_record.argtypes = [pointer, ctypes.c_size_t]
    library.ZOOM_resultset_destroy.argtypes = [pointer]
    library.ZOOM_record_get.restype = ctypes.c_void_p
    library.ZOOM_record_get.argtypes = [pointer, text, ctypes.POINTER(ctypes.c_int)]


def is_z3950_available() -> bool:
    """True when libyaz can be loaded on this machine."""
    try:
        _load_library()
    except Z3950UnavailableError:
        return False
    return True


def search_z3950(request: Z3950Request) -> Z3950Result:
    """Connects, searches and fetches records. Blocking: call it from a worker thread."""
    library = _load_library()
    options = library.ZOOM_options_create()
    connection = None
    result_set = None
    try:
        _set_connection_options(library, options, request)
        connection = library.ZOOM_connection_create(options)
        library.ZOOM_connection_connect(connection, request.host.encode(), request.port)
        _raise_on_error(library, connection, "connect")
        result_set = library.ZOOM_connection_search_pqf(connection, request.pqf_query.encode())
        _raise_on_error(library, connection, "search")
        hit_count = int(library.ZOOM_resultset_size(result_set))
        records = _read_records(library, result_set, min(hit_count, request.max_records), request)
        _raise_on_error(library, connection, "present")
        return Z3950Result(hit_count=hit_count, marcxml_records=records)
    finally:
        # Destroy in reverse order of creation; the result set holds a
        # reference to the connection.
        if result_set:
            library.ZOOM_resultset_destroy(result_set)
        if connection:
            library.ZOOM_connection_destroy(connection)
        library.ZOOM_options_destroy(options)


def _set_connection_options(library: ctypes.CDLL, options: int, request: Z3950Request) -> None:
    values = {
        "databaseName": request.database,
        "preferredRecordSyntax": request.record_syntax,
        "timeout": str(request.timeout_seconds),
        # Fetch the first page of records together with the search, in one
        # round trip, instead of one present request per record.
        "count": str(request.max_records),
        "presentChunk": str(request.max_records),
        "elementSetName": "F",
        "implementationName": "Faisca",
    }
    if request.username:
        values["user"] = request.username
    if request.password:
        values["password"] = request.password
    for key, value in values.items():
        library.ZOOM_options_set(options, key.encode(), value.encode())


def _read_records(
    library: ctypes.CDLL, result_set: int, count: int, request: Z3950Request
) -> list[str]:
    # "xml; charset=<from>,utf-8" asks YAZ to decode the ISO 2709 record,
    # recode its text to UTF-8 and return MARCXML, which every target then
    # shares with the SRU path.
    record_type = f"xml; charset={request.source_charset},utf-8".encode()
    records: list[str] = []
    for position in range(count):
        record = library.ZOOM_resultset_record(result_set, position)
        if not record:
            continue
        length = ctypes.c_int(0)
        data = library.ZOOM_record_get(record, record_type, ctypes.byref(length))
        if not data or length.value <= 0:
            continue
        records.append(ctypes.string_at(data, length.value).decode("utf-8", errors="replace"))
    return records


def _raise_on_error(library: ctypes.CDLL, connection: int, stage: str) -> None:
    message = ctypes.c_char_p()
    additional_info = ctypes.c_char_p()
    code = library.ZOOM_connection_error(
        connection, ctypes.byref(message), ctypes.byref(additional_info)
    )
    if code == 0:
        return
    text = (message.value or b"").decode(errors="replace")
    detail = (additional_info.value or b"").decode(errors="replace")
    raise Z3950Error(f"{stage}: {text}{f' ({detail})' if detail else ''} [code {code}]")
