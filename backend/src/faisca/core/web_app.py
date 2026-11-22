"""Serving the exported Next.js web app (web/out) from FastAPI."""

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

ROUTE_PAYLOAD_PREFIX = "__next."
ROUTE_PAYLOAD_SUFFIX = ".txt"


def nested_payload_path(path: str) -> str | None:
    """Where the export wrote a client-navigation payload the browser asks for by a dotted name.

    On a client-side navigation, Next.js fetches the next page's data as
    `cesto/__next.cesto.__PAGE__.txt` (route segments joined with dots), but
    the static export writes it as `cesto/__next.cesto/__PAGE__.txt` (one
    folder per segment). Returns that nested path, or None for any other file.
    """
    # StaticFiles passes an OS path: backslashes on Windows.
    folder, _, filename = path.replace("\\", "/").rpartition("/")
    if not (filename.startswith(ROUTE_PAYLOAD_PREFIX) and filename.endswith(ROUTE_PAYLOAD_SUFFIX)):
        return None
    segments = filename[len(ROUTE_PAYLOAD_PREFIX) : -len(ROUTE_PAYLOAD_SUFFIX)].split(".")
    if len(segments) < 2:
        return None
    nested = ROUTE_PAYLOAD_PREFIX + "/".join(segments) + ROUTE_PAYLOAD_SUFFIX
    return f"{folder}/{nested}" if folder else nested


class ExportedWebApp(StaticFiles):
    """StaticFiles for a Next.js export: index.html per folder, 404.html, and nested payloads."""

    def __init__(self, directory: str) -> None:
        super().__init__(directory=directory, html=True)

    async def get_response(self, path: str, scope: Scope) -> Response:
        """The file at [path], or the nested payload it names, or the export's 404 page."""
        nested = nested_payload_path(path)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or nested is None:
                raise
            return await super().get_response(nested, scope)
        # With html=True a missing file is not raised: StaticFiles answers
        # with 404.html, so the fallback looks at the status instead.
        if response.status_code == 404 and nested is not None:
            return await super().get_response(nested, scope)
        return response
