"""The one HTTP client the app uses for every external service, and its dependency."""

import ssl
from typing import Annotated

import httpx
import truststore
from fastapi import Depends, Request

from faisca.core.config import Settings

# Per-request timeouts are set by each target; this is only the ceiling for
# a call that forgets to pass one.
DEFAULT_TIMEOUT_SECONDS = 30.0


def create_http_client(settings: Settings) -> httpx.AsyncClient:
    """A pooled async client that always sends the polite User-Agent."""
    # truststore: verify certificates against the operating system's store,
    # not only certifi's bundle, so a network that inspects TLS with its own
    # (system-installed) certificate authority still works.
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.AsyncClient(
        verify=ssl_context,
        headers={"User-Agent": settings.user_agent},
        timeout=DEFAULT_TIMEOUT_SECONDS,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
    )


def get_http_client(request: Request) -> httpx.AsyncClient:
    """The app's shared client (built in `create_app`, closed on shutdown)."""
    client: httpx.AsyncClient = request.app.state.http_client
    return client


HttpClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
