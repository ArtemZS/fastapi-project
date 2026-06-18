from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db_depends import get_async_db
from app.schemas.categories import (
    Category as CategorySchema,
    CategoryCreate,
    CategoryList
) 
from app.schemas.paginations import PaginationDep
from app.core.security import RoleChecker
from app.services.categories import CategoryService 

router = APIRouter(
    prefix="/categories",
    tags=["categories"]
)


@router.get("/", response_model=CategoryList, status_code=status.HTTP_200_OK)
async def get_all_categories(
    pagination: PaginationDep,                      
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список всех активных категорий. 
    """
    return await CategoryService.get_all_categories(pagination, db) 


@router.get("/{category_id}", response_model=CategorySchema, status_code=status.HTTP_200_OK)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает активную категорию по ее ID. 
    """
    return await CategoryService.get_category_by_id(category_id, db)


@router.post("/",
    response_model=CategorySchema,
    dependencies=[Depends(RoleChecker("admin"))],
    status_code=status.HTTP_201_CREATED
)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новую категорию. Только администраторы могут создавать категории.
    """
    return await CategoryService.create_category(category, db)


@router.put("/{category_id}",
    response_model=CategorySchema,
    dependencies=[Depends(RoleChecker("admin"))],
    status_code=status.HTTP_200_OK
)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID. Только администраторы могут обновлять категории.
    """
    return await CategoryService.update_category(category_id, category, db)


@router.delete("/{category_id}",
    response_model=CategorySchema,
    dependencies=[Depends(RoleChecker("admin"))],
    status_code=status.HTTP_200_OK
)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Выполняет мягкое удаление категории по её ID, устанавливая is_active = False.
    Только администраторы могут удалять категории.
    """
    return await CategoryService.delete_category(category_id, db)