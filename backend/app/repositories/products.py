from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product


def create_product(
    db: Session, *, sku: str, name: str, price_cents: int, inventory_count: int
) -> Product:
    product = Product(
        sku=sku,
        name=name,
        price_cents=price_cents,
        inventory_count=inventory_count,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)


def get_product_by_sku(db: Session, sku: str) -> Product | None:
    return db.scalar(select(Product).where(Product.sku == sku))


def list_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).order_by(Product.id)).all())

