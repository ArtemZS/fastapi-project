from decimal import Decimal

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db_depends import get_async_db
from app.models.cart_items import CartItem as CartItemModel
from app.models.orders import Order as OrderModel, OrderItem as OrderItemModel
from app.models.users import User as UserModel
from app.schemas.orders import Order as OrderSchema, OrderList 
from app.schemas.paginations import PaginationDep

from app.services import _load_order_with_items
from app.services_for_routers.orders import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
)

router_v2 = APIRouter(
    prefix="/v2/orders",
    tags=["v2/orders"]
)


@router.post("/checkout", response_model=OrderSchema, status_code=status.HTTP_201_CREATED )
async def checkout_order(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Создаёт заказ на основе текущей корзины пользователя.
    Сохраняет позиции заказа, вычитает остатки и очищает корзину.
    """

    cart_result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(CartItemModel.user_id == current_user.id)
        .order_by(CartItemModel.id)
    )
    cart_items = cart_result.all()
    if cart_items is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")
    
    order = OrderModel(user_id=current_user.id)
    total_amount = Decimal("0")
    
    for cart_item in cart_items:
        product = cart_item.product
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {cart_item.product_id} is unavailable"
            )
        if product.stock < cart_item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for product {product.name}"
            )
        unit_price = product.price
        if unit_price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product {product.name} has no price set"
            )            
        total_price = unit_price * cart_item.quantity
        total_amount += total_price
        
        order_item = OrderItemModel(
            product_id=product.id,
            quantity=cart_item.quantity,
            unit_price=unit_price,
            total_price=total_price
        )            
        order.items.append(order_item)
        
        product.stock -= cart_item.quantity

    order.total_amount = total_amount
    db.add(order)
    
    await db.execute(delete(CartItemModel).where(CartItemModel.user_id == current_user.id))        
    await db.commit()
    
    created_order = await _load_order_with_items(db, order.id)
    if created_order is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created order"
        )
    return created_order        


@router.get("", response_model=OrderList, status_code=status.HTTP_200_OK)
async def list_orders(
    pagination: PaginationDep,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Возвращает заказы текущего пользователя с простой пагинацией.
    """
    total = await db.scalar(
        select(func.count(OrderModel.id))
        .where(OrderModel.user_id == current_user.id)
    )
    
    page = pagination.page
    page_size = pagination.page_size
    result = await db.scalars(
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItemModel.product)
        )
        .where(OrderModel.user_id == current_user.id)
        .order_by(OrderModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    orders = result.all()
    
    return OrderList(
        items=orders,
        total=total or 0,
        page=page,
        page_size=page_size
    )
    

@router.get("/{order_id}", response_model=OrderSchema, status_code=status.HTTP_200_OK)    
async def get_order(
    order_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Возвращает детальную информацию по заказу, если он принадлежит пользователю.
    """
    order = await _load_order_with_items(db, order_id)
    if not order or order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return order



@router_v2.post("/checkout", response_model=OrderSchema, status_code=status.HTTP_201_CREATED )
async def checkout_order(
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Создаёт заказ на основе текущей корзины пользователя.
    Сохраняет позиции заказа, вычитает остатки и очищает корзину.
    """
    return await OrderService.checkout_order(db, current_user)


@router_v2.get("", response_model=OrderList, status_code=status.HTTP_200_OK)
async def list_orders(
    pagination: PaginationDep,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Возвращает заказы текущего пользователя с простой пагинацией.
    """
    return await OrderService.list_orders(pagination, db, current_user)


@router_v2.get("/{order_id}", response_model=OrderSchema, status_code=status.HTTP_200_OK)    
async def get_order(
    order_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Возвращает детальную информацию по заказу, если он принадлежит пользователю.
    """
    return await OrderService.get_order(order_id, db, current_user)