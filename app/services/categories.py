from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.schemas.categories import CategoryList, CategoryCreate


class CategoryService:
    @staticmethod
    async def get_category_by_id(
        category_id: int, 
        db: AsyncSession
    ) -> CategoryModel:
        """
        Внутренний или внешний метод для получения валидной категории.
        Если не найдена — сразу генерирует HTTPException.
        """
        category = await db.scalar(
            select(CategoryModel).where(
                CategoryModel.id == category_id,
                CategoryModel.is_active == True
            )
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Category not found"
            )
        return category

    @staticmethod
    async def get_all_categories(
        pagination,
        db: AsyncSession
    ) -> CategoryList:
        """
        Возвращает список всех активных категорий с пагинацией. 
        """
        total = await db.scalar(
            select(func.count(CategoryModel.id))
            .where(CategoryModel.is_active == True)
        )
        
        page = pagination.page
        page_size = pagination.page_size
        
        items = (await db.scalars(
            select(CategoryModel)
            .where(CategoryModel.is_active == True)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()
        
        return CategoryList(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
        
    @staticmethod
    async def create_category(
        category: CategoryCreate,
        db: AsyncSession
    ) -> CategoryModel:
        """
        Создаёт новую категорию с проверкой родительской категории.
        """
        if category.parent_id is not None:
            # Используем наш метод для проверки существования родителя
            await CategoryService.get_category_by_id(category.parent_id, db)

        db_category = CategoryModel(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return db_category    
    
    @staticmethod
    async def update_category(
        category_id: int,
        category: CategoryCreate,
        db: AsyncSession
    ) -> CategoryModel:
        """
        Обновляет категорию по её ID.
        """
        # Сначала получаем текущую категорию из БД
        db_category = await CategoryService.get_category_by_id(category_id, db)

        if category.parent_id is not None:
            # Защита от зацикливания: нельзя назначить родителем саму себя
            if category.parent_id == db_category.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Category cannot be its own parent"
                )
            # Проверяем, существует ли родитель
            await CategoryService.get_category_by_id(category.parent_id, db)

        update_data = category.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)
        
        await db.commit()
        await db.refresh(db_category)
        return db_category
    
    @staticmethod
    async def delete_category(
        category_id: int,
        db: AsyncSession
    ) -> CategoryModel:
        """
        Выполняет мягкое каскадное удаление категории (is_active = False).
        """
        # Здесь мы запрашиваем с загрузкой children, поэтому пишем кастомный селект
        db_category = await db.scalar(
            select(CategoryModel)
            .options(selectinload(CategoryModel.children))
            .where(
                CategoryModel.id == category_id,
                CategoryModel.is_active == True
            )
        )
        if not db_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Category not found"
            )

        db_category.is_active = False
        
        # Мягкое удаление всех дочерних элементов
        for child in db_category.children:
            if child.is_active:
                child.is_active = False
                
        await db.commit()
        return db_category