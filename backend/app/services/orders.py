from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories import orders as order_repository
from app.repositories import products as product_repository
from app.repositories import users as user_repository
from app.schemas.orders import OrderCreate
from app.services.payments import simulate_successful_payment

logger = get_logger(__name__)


def create_order(db: Session, payload: OrderCreate):
    user = user_repository.get_user(db, payload.user_id)
    if not user:
        logger.warning(
            "Order creation rejected because user was not found",
            extra={"user_id": payload.user_id},
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    product = product_repository.get_product(db, payload.product_id)
    if not product:
        logger.warning(
            "Order creation rejected because product was not found",
            extra={"product_id": payload.product_id},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    if product.inventory_count < payload.quantity:
        logger.warning(
            "Order creation rejected because inventory is insufficient",
            extra={
                "error_category": "inventory_mismatch",
                "user_id": payload.user_id,
                "product_id": payload.product_id,
                "requested_quantity": payload.quantity,
                "available_inventory": product.inventory_count,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient inventory for this product",
        )

    total_cents = product.price_cents * payload.quantity
    simulate_successful_payment(amount_cents=total_cents)

    product.inventory_count -= payload.quantity
    order = order_repository.create_order(
        db,
        user_id=payload.user_id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        unit_price_cents=product.price_cents,
        total_cents=total_cents,
    )

    logger.info(
        "Order created",
        extra={
            "order_id": order.id,
            "user_id": payload.user_id,
            "product_id": payload.product_id,
            "quantity": payload.quantity,
            "total_cents": total_cents,
        },
    )
    return order_repository.get_order(db, order.id)


def get_order(db: Session, order_id: int):
    order = order_repository.get_order(db, order_id)
    if not order:
        logger.warning("Order lookup failed", extra={"order_id": order_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    logger.info("Order retrieved", extra={"order_id": order.id})
    return order


def list_orders(db: Session):
    orders = order_repository.list_orders(db)
    logger.info("Orders listed", extra={"order_count": len(orders)})
    return orders

