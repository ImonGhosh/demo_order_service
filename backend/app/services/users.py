from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import users as user_repository
from app.schemas.users import UserCreate

logger = get_logger(__name__)


def create_user(db: Session, payload: UserCreate):
    existing_user = user_repository.get_user_by_email(db, payload.email)
    if existing_user:
        logger.warning(
            "User creation rejected because email already exists",
            extra={"email": payload.email},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    try:
        user = user_repository.create_user(db, email=payload.email, name=payload.name)
    except IntegrityError as exc:
        db.rollback()
        logger.exception(
            "User creation failed due to database integrity error",
            extra={
                "email": payload.email,
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from exc

    logger.info("User created", extra={"user_id": user.id, "email": user.email})
    return user


def get_user(db: Session, user_id: int):
    user = user_repository.get_user(db, user_id)
    if not user:
        logger.warning("User lookup failed", extra={"user_id": user_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info("User retrieved", extra={"user_id": user.id})
    return user

