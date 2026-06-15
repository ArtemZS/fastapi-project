from pydantic import BaseModel, Field, ConfigDict
from app.schemas.paginations import PaginationGeneric

class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: str = Field(min_length=3, max_length=50,
                    description="Название категории (3-50 символов)")
    parent_id: int | None = Field(None, description="ID родительской категории, если есть")


class Category(BaseModel):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор категории")
    name: str = Field(description="Название категории")
    parent_id: int | None = Field(None, description="ID родительской категории, если есть")
    is_active: bool = Field(description="Активность категории")

    model_config = ConfigDict(from_attributes=True)

    
class CategoryList(PaginationGeneric[Category]):
    """
    Модель для отображения списка категорий с поддержкой пагинации.

    [НАСЛЕДУЕМЫЕ ПОЛЯ]:
    - `items (list[Category])`: Элементы на текущей странице
    - `total (int)`: Общее количество элементов.
    - `page (int)`: Номер текущей страницы.
    - `page_size (int)`: Количество элементов на странице.
    """
        