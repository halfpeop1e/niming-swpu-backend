from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils,getCard
from app.core.config import settings

#api路由器，包含所有路由组
api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(getCard.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
