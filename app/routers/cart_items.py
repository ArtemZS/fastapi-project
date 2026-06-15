from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.schemas.cart_items import (
    Cart as CartSchema,
    CartItem as CartItemSchema,
    CartItemCreate,
    CartItemUpdate
)

from app.services_for_routers.cart_items import CarItemService

router = APIRouter(
    prefix="/cart",
    tags=["cart"]
)

@router.get("/", response_model=CartSchema, status_code=status.HTTP_200_OK)
async def get_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user:  UserModel = Depends(get_current_user)
):
    """Возвращает текущую корзину пользователя с деталями товаров, общим количеством и общей стоимостью."""
    return await CarItemService.get_cart(db, current_user)

@router.post("/items", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    payload: CartItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Добавляет товар в корзину. Если товар уже есть, увеличивает количество."""
    return await CarItemService.add_item_to_cart(payload, db, current_user)

@router.put("/items/{product_id}", response_model=CartItemSchema)
async def update_cart_item(
    product_id: int,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Обновляет количество товара в корзине."""
    return await CarItemService.update_cart_item(product_id, payload, db, current_user)

@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Удаляет товар из корзины."""
    return await CarItemService.remove_item_from_cart(product_id, db, current_user)

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Очищает всю корзину пользователя."""
    return await CarItemService.clear_cart(db, current_user)