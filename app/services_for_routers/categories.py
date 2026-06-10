from app.models.categories import Category as CategoryModel
from app.schemas.categories import CategoryList, CategoryCreate
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

class CategoryService:
    @staticmethod
    async def get_all_categories(
        pagination,
        db: AsyncSession
    ):
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
    async def get_category(
        category: CategoryModel
    ):
        """
        
        """
        # Если get_valid_category отработал в роуте, объект уже валиден
        return category  
        
    @staticmethod
    async def create_category(
        category: CategoryCreate,
        db: AsyncSession
    ):
        """
        Создаёт новую категорию с проверкой родительской категории.
        """
        if category.parent_id is not None:
            parent = await db.scalar(
                select(CategoryModel).where(
                    CategoryModel.id == category.parent_id,
                    CategoryModel.is_active == True
                )
            )
            if parent is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Parent category not found"
                )

        db_category = CategoryModel(**category.model_dump())
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return db_category    
    
    @staticmethod
    async def update_category(
        category: CategoryCreate,
        db_category: CategoryModel,
        db: AsyncSession
    ):
        """
        Обновляет категорию по её ID.
        """
        if category.parent_id is not None:
            # Защита от зацикливания: нельзя назначить родителем саму себя
            if category.parent_id == db_category.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Category cannot be its own parent"
                )
                
            parent = await db.scalar(
                select(CategoryModel).where(
                    CategoryModel.id == category.parent_id,
                    CategoryModel.is_active == True
                )
            )
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Parent category not found"
                )

        # ИСПРАВЛЕНО: Добавлен .items() для словаря
        update_data = category.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_category, key, value)
        
        # ИСПРАВЛЕНО: Сначала коммит, потом рефреш
        await db.commit()
        await db.refresh(db_category)
        return db_category
    
    @staticmethod
    async def delete_category(
        category_id: int,
        db: AsyncSession
    ):
        """
        Выполняет мягкое каскадное удаление категории (is_active = False).
        """
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