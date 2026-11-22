"""Every model in the app, imported in one place so `Base.metadata` knows every table.

Alembic's autogenerate and the test database both read `Base.metadata`; a
model that is not imported here is invisible to them. `moarch-py create module`
adds each module's import above the anchor.

Never import this file from inside `modules/`: it imports every module, so
`lint-imports` would rightly see that module reaching into all the others.
Only Alembic and the tests need it.
"""

from faisca.db.base import Base
from faisca.modules.basket_items.models import BasketItem  # noqa: F401
from faisca.modules.cached_responses.models import CachedResponse  # noqa: F401

# moarch:models

__all__ = ["Base"]
