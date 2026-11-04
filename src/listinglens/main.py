from fastapi import APIRouter, FastAPI

from listinglens.config import settings
from listinglens.exception_handlers import register_exception_handlers

from .routers.health_router import router as health_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    debug=settings.debug,
)

register_exception_handlers(app)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router, tags=["Health"])

app.include_router(v1_router)
