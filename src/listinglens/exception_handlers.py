import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from listinglens.services.health_service import DatabaseUnavailableError

logger = logging.getLogger(__name__)


def database_unavailable_handler(
    request: Request, exception: DatabaseUnavailableError
) -> JSONResponse:
    logger.error("%s %s: %s", request.method, request.url.path, exception.detail)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": exception.detail},
    )


def unhandled_exception_handler(request: Request, exception: Exception) -> JSONResponse:
    logger.exception(
        "Unhandled exception during%s %s",
        request.method,
        request.url.path,
        exc_info=exception,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error."},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DatabaseUnavailableError, database_unavailable_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
