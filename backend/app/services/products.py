from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import products as product_repository
from app.schemas.products import ProductCreate

logger = get_logger(__name__)


def create_product(db: Session, payload: ProductCreate):
    existing_product = product_repository.get_product_by_sku(db, payload.sku)
    if existing_product:
        logger.warning(
            "Product creation rejected because SKU already exists",
            extra={"sku": payload.sku},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        )

    try:
        product = product_repository.create_product(
            db,
            sku=payload.sku,
            name=payload.name,
            price_cents=payload.price_cents,
            inventory_count=payload.inventory_count,
        )
    except IntegrityError as exc:
        db.rollback()
        logger.exception(
            "Product creation failed due to database integrity error",
            extra={
                "sku": payload.sku,
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this SKU already exists",
        ) from exc

    logger.info(
        "Product created",
        extra={"product_id": product.id, "sku": product.sku},
    )
    return product


def list_products(db: Session):
    products = product_repository.list_products(db)
    logger.info("Products listed", extra={"product_count": len(products)})
    return products

