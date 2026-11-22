"""Settings read from the environment and `.env`, validated once at startup."""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "0.1.0"

# backend/src/faisca/core/config.py → the monorepo root, where config/ and
# web/ live in a checkout. The Docker image sets both paths explicitly.
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class Environment(StrEnum):
    """Where the app is running; decides defaults such as the docs and log format."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Every configuration value the app reads. Add a field here, then to `.env.example`."""

    # Real environment variables win over `.env`, so a container or CI can
    # override any value without touching the file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Faisca"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./faisca.db"
    # Logs every SQL statement; useful locally, far too noisy in production.
    database_echo: bool = False

    api_v1_prefix: str = "/api/v1"
    # Interactive OpenAPI docs at /docs (and the schema at /openapi.json). On by
    # default even in production: Faísca has no public users, and whoever
    # builds a client (the Flutter app) needs them.
    api_docs_enabled: bool = True
    cors_origins: list[str] = []

    # The catalogues and digital-copy sources, one YAML file for both.
    targets_file: Path = REPOSITORY_ROOT / "config" / "targets.yaml"
    # The exported Next.js site (`next build` → web/out), served at "/".
    # Empty: serve the API only (as in `npm run dev`, which serves its own).
    web_dist_dir: Path | None = REPOSITORY_ROOT / "web" / "out"

    # Sent in the User-Agent of every request to an external service, as
    # most of them ask, so an operator can reach us instead of blocking us.
    contact_email: str = ""
    europeana_api_key: str = ""
    google_books_api_key: str = ""

    # Live results are reused for this long; a cataloguer repeating a search
    # (or opening a record from it) does not query the targets again.
    cache_ttl_hours: int = 24
    # Records fetched per target and search: the first page, as ZZZ does.
    max_records_per_target: int = 20
    # Politeness towards each external service: at most this many requests
    # at once, and this long between the start of two requests.
    max_concurrent_requests_per_target: int = 2
    min_seconds_between_requests: float = 1.0

    # Every module answers from its `mocks.py` samples instead of the
    # database, so a client app can be built and tested before real data
    # exists, or with no database running at all.
    mock_responses: bool = False

    @property
    def is_production(self) -> bool:
        """True in production, where the interactive API docs are switched off."""
        return self.environment is Environment.PRODUCTION

    @property
    def user_agent(self) -> str:
        """The polite User-Agent: who we are and how to reach us."""
        contact = f"; mailto:{self.contact_email}" if self.contact_email else ""
        return f"Faisca/{APP_VERSION} (bibliographic search for library cataloguing{contact})"

    @model_validator(mode="after")
    def refuse_mock_responses_in_production(self) -> Self:
        """Stops the app at startup rather than serve made-up data to real users."""
        if self.mock_responses and self.is_production:
            raise ValueError("MOCK_RESPONSES must be false when ENVIRONMENT=production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """The settings, read once per process. Tests override this dependency."""
    return Settings()
