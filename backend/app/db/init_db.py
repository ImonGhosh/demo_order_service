from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import Base, engine
from app.models import Product

logger = get_logger(__name__)

SEED_PRODUCTS = [
    {
        "sku": "SKU-COFFEE-001",
        "name": "House Coffee Beans",
        "price_cents": 1499,
        "inventory_count": 100,
    },
    {
        "sku": "SKU-MUG-002",
        "name": "Ceramic Travel Mug",
        "price_cents": 2199,
        "inventory_count": 50,
    },
    {
        "sku": "SKU-FILTER-003",
        "name": "Paper Filter Pack",
        "price_cents": 699,
        "inventory_count": 200,
    },
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized")


def seed_products(db: Session) -> None:
    existing_product = db.scalar(select(Product).limit(1))
    if existing_product:
        logger.info("Seed products already exist")
        return

    for product_data in SEED_PRODUCTS:
        db.add(Product(**product_data))

    db.commit()
    logger.info("Seed products inserted", extra={"seed_product_count": len(SEED_PRODUCTS)})

