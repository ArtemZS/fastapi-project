from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Annotated, Optional
from app.schemas.paginations import PaginationGeneric

from fastapi import Form


class ReviewCreate(BaseModel):
    """Модель для создания отзыва."""
    product_id: int = Field(description="ID товара, к которому оставляется отзыв")
    rating: int = Field(ge=1, le=5, description="Рейтинг от 1 до 5")
    comment: str | None = Field(None, max_length=3000, description="Комментарий (до 3000 символов)")
    
    @classmethod
    def as_form(
        cls,
        product_id: Annotated[int, Form(...)],
        rating: Annotated[int, Form(...)],
        comment: Annotated[Optional[str], Form()] = None
    ) -> "ReviewCreate":
        return cls(
            product_id=product_id,
            rating=rating,
            comment=comment
        )
        
class Review(BaseModel):
    """Модель для ответа с данными отзыва."""
    id: int
    rating: int = Field(description="Рейтинг от 1 до 5")
    comment: str | None = Field(None, description="Комментарий")
    product_id: int = Field(description="ID товара")
    user_id: int = Field(description="ID пользователя")
    comment_date: datetime = Field(description="Дата комментария")
    is_active: bool = Field(description="Активность отзыва")
    
    model_config = ConfigDict(from_attributes=True)
    
class ReviewList(PaginationGeneric[Review]):
    """
    Модель для отображения списка отзывов с поддержкой пагинации
        
    [НАСЛЕДУЕМЫЕ ПОЛЯ]:
    - `items (list[Review])`: Элементы на текущей странице
    - `total (int)`: Общее количество элементов.
    - `page (int)`: Номер текущей страницы.
    - `page_size (int)`: Количество элементов на странице.
    """