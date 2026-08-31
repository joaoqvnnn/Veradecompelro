from aiogram import Router

from handlers.admin.panel import router as panel_router
from handlers.admin.products import router as products_router
from handlers.admin.stock import router as stock_router
from handlers.admin.users import router as users_router
from handlers.admin.others import router as others_router


def setup_admin_routers() -> Router:
    router = Router()
    router.include_router(panel_router)
    router.include_router(products_router)
    router.include_router(stock_router)
    router.include_router(users_router)
    router.include_router(others_router)
    return router
