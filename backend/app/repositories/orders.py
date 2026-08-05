from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderItem


def create_order(
    db: Session,
    *,
    user_id: int,
    product_id: int,
    quantity: int,
    unit_price_cents: int,
    total_cents: int,
) -> Order:
    order = Order(user_id=user_id, total_cents=total_cents)
    order.items.append(
        OrderItem(
            product_id=product_id,
            quantity=quantity,
            unit_price_cents=unit_price_cents,
        )
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_order(db: Session, order_id: int) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.user))
    )


def list_orders(db: Session) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .order_by(Order.id.desc())
            .options(selectinload(Order.items), selectinload(Order.user))
        ).all()
    )


def list_reconcilable_orders(db: Session) -> list[Order]:
    return list(
        db.scalars(
            select(Order)
            .where(Order.status == "created", Order.payment_status == "paid")
            .order_by(Order.id)
        ).all()
    )


def mark_orders_completed(db: Session, orders: list[Order]) -> int:
    for order in orders:
        order.status = "completed"

    db.commit()
    return len(orders)
