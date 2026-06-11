from fastapi import HTTPException, status, Response
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.models.cart_items import CartItem as CartItemModel
from app.models.users import User as UserModel
from app.schemas.cart_items import (
    Cart as CartSchema,
    CartItemCreate,
    CartItemUpdate
)
from app.services import _ensure_product_available, _get_cart_item


class CarItemService:
    @staticmethod
    async def get_cart(
        db: AsyncSession,
        current_user:  UserModel
    ):
        """Возвращает текущую корзину пользователя с деталями товаров, общим количеством и общей стоимостью."""
        result = await db.scalars(
            select(CartItemModel)
            .options(selectinload(CartItemModel.product))
            .where(CartItemModel.user_id == current_user.id)
            .order_by(CartItemModel.id)
        )
        items = result.all()
        
        total_quantity = sum(item.quantity for item in items)
        price_items = (
            Decimal(item.quantity) * 
            (item.product.price if item.product.price is not None else Decimal("0")) 
            for item in items
        )
        total_price_decimal = sum(price_items, Decimal("0"))
        
        return CartSchema(
            user_id=current_user.id,
            items=items,
            total_quantity=total_quantity,
            total_price=total_price_decimal
        )
        
    @staticmethod
    async def add_item_to_cart(
        payload: CartItemCreate,
        db: AsyncSession,
        current_user: UserModel
    ):
        """Добавляет товар в корзину. Если товар уже есть, увеличивает количество."""
        await _ensure_product_available(db, payload.product_id)    
        
        cart_item = await _get_cart_item(db, current_user.id, payload.product_id)
        if cart_item:
            cart_item.quantity += payload.quantity
        else:         
            cart_item = CartItemModel(
                user_id=current_user.id,
                product_id=payload.product_id,
                quantity=payload.quantity
            )
            db.add(cart_item)
        
        await db.commit()
        updated_item = await _get_cart_item(db, current_user.id, payload.product_id)  
        return updated_item  
    
    @staticmethod
    async def update_cart_item(
        payload: CartItemUpdate,
        db: AsyncSession,
        current_user: UserModel
    ):
        """Обновляет количество товара в корзине."""
        await _ensure_product_available(db, payload.product_id)

        cart_item = await _get_cart_item(db, current_user.id, payload.product_id)
        if not cart_item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        cart_item.quantity = payload.quantity
        await db.commit()
        await db.refresh(cart_item)
        updated_item = await _get_cart_item(db, current_user.id, payload.product_id)
        return updated_item
    
    @staticmethod
    async def remove_item_from_cart(
        product_id: int,
        db: AsyncSession,
        current_user: UserModel
    ):
        """Удаляет товар из корзины."""
        cart_item = await _get_cart_item(db, current_user.id, product_id)
        if not cart_item:
            raise HTTPException(status_code=404, detail="Cart item not found")

        await db.delete(cart_item)
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
    @staticmethod
    async def clear_cart(
        db: AsyncSession,
        current_user: UserModel
    ):
        """Очищает всю корзину пользователя."""
        await db.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)