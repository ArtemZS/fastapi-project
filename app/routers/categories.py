from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload

from app.db_depends import get_async_db
from app.models.categories import Category as CategoryModel
from app.schemas.categories import (
    Category as CategorySchema,
    CategoryCreate,
    CategoryList
) 
from app.schemas.paginations import PaginationDep
from app.core.security import RoleChecker
from app.dependecies import get_valid_category

from sqlalchemy.ext.asyncio import AsyncSession

from app.services_for_routers.categories import CategoryService 

# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    deprecated=True
)

router_v2 = APIRouter(
    prefix="/v2/categories",
    tags=["v2/categories"]
)

@router.get("/", response_model=CategoryList, status_code=status.HTTP_200_OK)
async def get_all_categories(
    pagination: PaginationDep,                      
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список всех активных категорий. 
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
    #? db.scalars возвращает корутину, которая при await выдаёт результат запроса. result.all() возвращает список категорий
    return CategoryList(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


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
    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        parent = await db.scalar(
            select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                        CategoryModel.is_active == True)
        )
        #? db.scalar(parent_stmt) возвращет корутину, которая при await выдаёт результат запроса. Если parent не найден, будет None
        if parent is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent category not found")

    # Создание новой категории
    db_category = CategoryModel(**category.model_dump())
    db.add(db_category)
    await db.commit()
    # await db.refresh(db_category) #? не нужно, так как engine настроен с expire_on_commit=False
    return db_category


@router.put("/{category_id}",
    response_model=CategorySchema,
    dependencies=[Depends(RoleChecker("admin"))],
    status_code=status.HTTP_200_OK
)
async def update_category(
    category: CategoryCreate,
    db_category: CategoryModel = Depends(get_valid_category),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID. Только администраторы могут обновлять категории.
    """
    # Проверяем parent_id, если указан
    if category.parent_id is not None:
        parent = await db.scalar(
            select(CategoryModel).where(CategoryModel.id == category.parent_id,
                                                CategoryModel.is_active == True)
        )
        #? Проверяем, что parent существует и не является ссылкой на себя
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Parent category not found")
        if parent.id == db_category.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category cannot be it's own parent")

    # Обновляем категорию
    #? exclude_unset=True позволяет исключить из обновления поля, которые не были переданы в запросе (т.е. не изменять их)
    update_data = category.model_dump(exclude_unset=True)
    await db.execute(
        update(CategoryModel)
        .where(CategoryModel.id == db_category.id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.delete("/{category_id}",
    response_model=CategorySchema,
    dependencies=[Depends(RoleChecker("admin"))],
    status_code=status.HTTP_200_OK
)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Выполняет мягкое удаление категории по её ID, устанавливая is_active = False.
    Только администраторы могут удалять категории.
    """
    #? selectinload(CategoryModel.children) позволяет загрузить связанные дочерние категории вместе с родительской категорией, 
    #? что необходимо для их деактивации при удалении родительской категории
    
    db_category = await db.scalar(
        select(CategoryModel)
        .options(selectinload(CategoryModel.children))
        .where(
            CategoryModel.id == category_id,
            CategoryModel.is_active == True
        )
    )
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db_category.is_active = False
    #? Деактивируем все дочерние категории (логическое удаление)
    for child in db_category.children:
        if child.is_active:
            child.is_active = False
            
    await db.commit()
    return db_category






@router_v2.get("/", response_model=CategoryList, status_code=status.HTTP_200_OK)
async def get_all_categories(
    pagination: PaginationDep,                      
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список всех активных категорий. 
    """
    return await CategoryService.get_all_categories(pagination, db) 


@router_v2.get("/{category_id}", response_model=CategorySchema, status_code=status.HTTP_200_OK)
async def get_category(
    category: CategoryModel = Depends(get_valid_category)
):
    """
    Возвращает активную категорию по ее ID. 
    """
    return await CategoryService.get_category(category)


@router_v2.post("/",
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


@router_v2.put("/{category_id}",
    response_model=CategorySchema,
    dependencies=[Depends(RoleChecker("admin"))],
    status_code=status.HTTP_200_OK
)
async def update_category(
    category: CategoryCreate,
    db_category: CategoryModel = Depends(get_valid_category),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID. Только администраторы могут обновлять категории.
    """
    return await CategoryService.update_category(category, db_category, db)


@router_v2.delete("/{category_id}",
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