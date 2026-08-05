from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import SessionLocal

router = APIRouter(tags=["service"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.service_name,
        "environment": settings.environment,
    }


@router.get("/ready")
async def ready() -> dict[str, str | bool]:
    database_ready = True
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        database_ready = False

    return {
        "status": "ready" if database_ready else "not_ready",
        "service": settings.service_name,
        "environment": settings.environment,
        "database": database_ready,
    }
