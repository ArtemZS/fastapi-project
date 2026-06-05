from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Annotated, Optional

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
            product_id,
            rating,
            comment
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
    
class ReviewList(BaseModel):
    """Список пагинации для отзывов."""
    items: list[Review] = Field(description="Отзывы для текущей страницы")
    total: int = Field(ge=0, description="Общее количество отзывов")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")
    
    model_config = ConfigDict(from_attributes=True)