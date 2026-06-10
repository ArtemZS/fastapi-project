from decimal import Decimal
from sqlalchemy import select, cast, Numeric, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload

from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel
from app.models.cart_items import CartItem as CartItemModel
from app.models.categories import Category as CategoryModel
from app.models.orders import Order as OrderModel, OrderItem as OrderItemModel


async def _recalculate_product_rating(product_id: int, db: AsyncSession) -> Decimal:
    """
    Вычисляет средний рейтинг товара на основе активных отзывов.
    Возвращает Decimal (Numeric(3, 2)) или 0.00, если отзывов нет.
    """
    new_rating = await db.scalar(
        select(cast(func.avg(ReviewModel.rating), Numeric(3, 2)))
        .where(
            ReviewModel.product_id == product_id,
            ReviewModel.is_active == True
        )
    )
    
    return new_rating if new_rating is not None else Decimal("0.00")


async def _ensure_product_available(db: AsyncSession, product_id: int) -> None:
    """Проверяет, что товар существует в БД и активен."""
    product = await db.scalar(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or inactive",
        )
        
        
async def _get_cart_item(
    db: AsyncSession, user_id: int, product_id: int
) -> CartItemModel | None:
    """Ищет позицию товара в корзине пользователя. Возвращает объект CartItem или None."""
    result = await db.scalar(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == user_id,
            CartItemModel.product_id == product_id,
        )
    )
    return result        


async def _load_order_with_items(db: AsyncSession, order_id: int) -> OrderModel | None:
    """Загружает заказ с его элементами."""
    result = await db.scalar(
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.product),
        )
        .where(OrderModel.id == order_id)
    )
    return result


