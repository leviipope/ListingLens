from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from listinglens.schemas.errors import ErrorResponse
from listinglens.services.health_service import HealthService, get_health_service

router = APIRouter(
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
    }
)


class HealthCheckResponse(BaseModel):
    status: str
    message: str


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check service health",
    description="Return the service health status.",
)
def health_check() -> HealthCheckResponse:
    return HealthCheckResponse(status="healthy", message="Service is healthy.")


@router.get(
    "/health/database",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check database health",
    description="Return the service database health status.",
)
def database_health_check(
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthCheckResponse:
    health_service.check_database()
    return HealthCheckResponse(status="healthy", message="Database is healthy.")
