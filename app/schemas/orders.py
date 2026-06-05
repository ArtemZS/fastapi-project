from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime

from app.schemas.products import Product


class OrderItem(BaseModel):
    """Модель для отображения отдельной позиции (товара) в составе заказа."""
    id: int = Field(description="ID позиции товара")
    product_id: int = Field(description="ID товара")
    quantity: int = Field(ge=1, description="Количество" )
    unit_price: Decimal = Field(ge=0, description="Цена за единицу на момент покупки")
    total_price: Decimal = Field(ge=0, description="Сумма позиции")
    product: Product | None = Field(description="Полная информация о товаре")
    
    model_config = ConfigDict(from_attributes=True)


class Order(BaseModel):
    """Модель для отображения полной информации о заказе."""
    id: int = Field(description="ID заказа")
    user_id: int = Field(description="ID пользователя")
    status: str = Field(description="Текущий статус заказа")
    total_amount: Decimal = Field(ge=0, description="Общая стоимость")
    created_at: datetime = Field(description="Дата и время оформленеия заказа")
    updated_at: datetime = Field(description="Дата и время обновления заказа")
    items: list[OrderItem] = Field(default_factory=list, description="Список позиций")
    
    model_config = ConfigDict(from_attributes=True)
    
    
class OrderList(BaseModel):
    """Модель для отображения списка заказов с поддержкой пагинации."""
    items: list[Order] = Field(description="Заказы на текущей странице")
    total: int = Field(ge=0, description="Общее количество заказов")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")
    
    model_config = ConfigDict(from_attributes=True)
