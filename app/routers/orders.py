from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.schemas.orders import Order as OrderSchema, OrderList 
from app.schemas.paginations import PaginationDep

from app.services.orders import OrderService

router = APIRouter(
    prefix="/orders",
    tags=["orders"]
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
    return await OrderService.checkout_order(db, current_user)


@router.get("", response_model=OrderList, status_code=status.HTTP_200_OK)
async def list_orders(
    pagination: PaginationDep,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Возвращает заказы текущего пользователя с простой пагинацией.
    """
    return await OrderService.list_orders(pagination, db, current_user)


@router.get("/{order_id}", response_model=OrderSchema, status_code=status.HTTP_200_OK)    
async def get_order(
    order_id: int, 
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Возвращает детальную информацию по заказу, если он принадлежит пользователю.
    """
    return await OrderService.get_order(order_id, db, current_user)