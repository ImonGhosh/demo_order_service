from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.products import ProductCreate, ProductRead
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=201)
async def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return product_service.create_product(db, payload)


@router.get("", response_model=list[ProductRead])
async def list_products(db: Session = Depends(get_db)):
    return product_service.list_products(db)

