"""Version 1 of the API: every module router, mounted under `/api/v1`.

A new version (`api/v2/`) gets its own router, so v1 clients (the web app and
the Flutter app) keep working while v2 changes shapes. `moarch-py create
module` registers each router here.
"""

from fastapi import APIRouter

from faisca.modules.basket_items.router import router as basket_items_router
from faisca.modules.catalogues.router import router as catalogues_router
from faisca.modules.digital.router import router as digital_router
from faisca.modules.targets.router import router as targets_router

# moarch:router-imports

api_router = APIRouter()

api_router.include_router(catalogues_router)
api_router.include_router(digital_router)
api_router.include_router(basket_items_router)
api_router.include_router(targets_router)
# moarch:routers
