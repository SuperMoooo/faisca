"""Writes the /api/v1 OpenAPI schema to contracts/openapi.json.

The web app generates its TypeScript types from that file (`npm run
generate:api`), and the Flutter app will generate its Dart client from the
same file, so both clients follow one contract. Run it after changing a schema:

    uv run python scripts/export_openapi.py
"""

import json
from pathlib import Path

from faisca.core.config import Environment, Settings
from faisca.main import create_app

CONTRACT_FILE = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"


def export_openapi() -> None:
    """Builds the app without a database or web app and saves its schema."""
    settings = Settings(
        environment=Environment.TEST, database_url="sqlite+aiosqlite:///:memory:", web_dist_dir=None
    )
    schema = create_app(settings).openapi()
    CONTRACT_FILE.parent.mkdir(exist_ok=True)
    CONTRACT_FILE.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {CONTRACT_FILE}")


if __name__ == "__main__":
    export_openapi()
