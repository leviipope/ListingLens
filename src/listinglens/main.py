from fastapi import APIRouter, FastAPI

from listinglens.config import settings

# from listinglens.exceptionhandlers import register_exception_handlers
# from .routers import health_router, listinglens_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
    debug=settings.debug,
)

# register_exception_handlers(app)

v1_router = APIRouter(prefix="/api/v1")
# v1_router.include_router(health_router, tags=["Health"])
# v1_router.include_router(listinglens_router, tags=["ListingLens"])

app.include_router(v1_router)
