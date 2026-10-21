from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from listinglens.db.database import get_db


class DatabaseUnavailableError(Exception):
    def __init__(self, detail: str = "Database health check failed.") -> None:
        self.detail = detail
        super().__init__(detail)


class HealthService:
    def __init__(
        self,
        database_session: Session,
    ) -> None:
        self.database_session = database_session

    def check_database(self) -> None:
        try:
            self.database_session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            raise DatabaseUnavailableError from error


def get_health_service(
    database_session: Annotated[Session, Depends(get_db)],
) -> HealthService:
    return HealthService(database_session)
