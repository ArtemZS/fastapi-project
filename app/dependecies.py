from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db_depends import get_async_db
from app.models.categories import Category as CategoryModel

class GetValidCategory:
    def __init__(self, exc_code: int = 404, exc_detail: str = "Category not found or inactive"):
        self.exc_code = exc_code
        self.exc_detail = exc_detail

    async def __call__(
        self, 
        category_id: int,  # Только этот параметр пойдёт в путь (path) Swagger
        db: AsyncSession = Depends(get_async_db)
    ) -> CategoryModel:
        
        category = await db.scalar(
            select(CategoryModel).where(
                CategoryModel.id == category_id,
                CategoryModel.is_active == True
            )
        )
        if not category:
            raise HTTPException(status_code=self.exc_code, detail=self.exc_detail)
            
        return category

# Создаем готовые дефолтные зависимости
get_valid_category = GetValidCategory()
get_valid_category_or_400 = GetValidCategory(exc_code=400, exc_detail="Bad category ID")