from pydantic import BaseModel, Field, ConfigDict
from fastapi import Query, Depends
from typing import Annotated, Generic, TypeVar

T = TypeVar('T')

class PaginationPages(BaseModel):
    page_size: Annotated[int | None, Query(10, ge=1, le=100, description="Номер страницы для пагинации")]
    page: Annotated[int, Query(1, ge=1, description="Количество элементов на странице")] 
    
PaginationDep = Annotated[PaginationPages, Depends()]    
    
class PaginationGeneric(BaseModel, Generic[T]):
    """Generic модель для классов с поддержкой пагинации"""
    items: list[T] = Field(description="Элементы для текущей страницы")
    total: int = Field(ge=0, description="Общее количество отзывов")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")
    
    model_config = ConfigDict(from_attributes=True)  