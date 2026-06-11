from fastapi import APIRouter, HTTPException, Depends, status, Response
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal

from app.core.security import get_current_user
from app.db_depends import get_async_db
from app.models.cart_items import CartItem as CartItemModel
from app.models.users import User as UserModel
from app.schemas.cart_items import (
    Cart as CartSchema,
    CartItem as CartItemSchema,
    CartItemCreate,
    CartItemUpdate
)
from app.services import _ensure_product_available, _get_cart_item

from app.services_for_routers.cart_items import CarItemService

router = APIRouter(
    prefix="/cart",
    tags=["cart"]
)

router_v2 = APIRouter(
    prefix="/v2/cart",
    tags=["v2/cart"]
)


@router.get("/", response_model=CartSchema, status_code=status.HTTP_200_OK)
async def get_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user:  UserModel = Depends(get_current_user)
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
    

@router.post("/items", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    payload: CartItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
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


@router.put("/items/{product_id}", response_model=CartItemSchema)
async def update_cart_item(
    product_id: int,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Обновляет количество товара в корзине."""
    await _ensure_product_available(db, product_id)

    cart_item = await _get_cart_item(db, current_user.id, product_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    cart_item.quantity = payload.quantity
    await db.commit()
    updated_item = await _get_cart_item(db, current_user.id, product_id)
    return updated_item



@router.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Удаляет товар из корзины."""
    cart_item = await _get_cart_item(db, current_user.id, product_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await db.delete(cart_item)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Очищает всю корзину пользователя."""
    await db.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router_v2.get("/", response_model=CartSchema, status_code=status.HTTP_200_OK)
async def get_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user:  UserModel = Depends(get_current_user)
):
    """Возвращает текущую корзину пользователя с деталями товаров, общим количеством и общей стоимостью."""
    return await CarItemService.get_cart(db, current_user)

@router_v2.post("/items", response_model=CartItemSchema, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    payload: CartItemCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Добавляет товар в корзину. Если товар уже есть, увеличивает количество."""
    return await CarItemService.add_item_to_cart(payload, db, current_user)

@router_v2.put("/items/{product_id}", response_model=CartItemSchema)
async def update_cart_item(
    product_id: int,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Обновляет количество товара в корзине."""
    return await CarItemService.update_cart_item(product_id, payload, db, current_user)

@router_v2.delete("/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_from_cart(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Удаляет товар из корзины."""
    return await CarItemService.remove_item_from_cart(product_id, db, current_user)

@router_v2.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """Очищает всю корзину пользователя."""
    return await CarItemService.clear_cart(db, current_user)