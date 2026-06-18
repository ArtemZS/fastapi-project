from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from decimal import Decimal

from app.schemas.products import Product as ProductSchema, ProductCreate, ProductList
from app.models import Category as CategoryModel
from app.schemas.paginations import PaginationDep
from app.core.security import RoleChecker
from app.models.users import User as UserModel
from app.core.dependecies import get_valid_category

from app.core.db_depends import  get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.products import ProductService

router = APIRouter(
    prefix="/products",
    tags=["products"]
)


@router.get("/", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_all_products(
    pagination: PaginationDep,
    category_id: int | None = Query(None, description="ID категории для фильтрации"),
    search: str | None = Query(None, min_length=1, description="Поиск по названию товара"),
    min_price: Decimal | None = Query(None, ge=0, decimal_places=2, description="Минимальная цена товара"),
    max_price: Decimal | None = Query(None, ge=0, decimal_places=2, description="Максимальная цена товара"),
    in_stock: bool | None = Query(None, description="true — только товары в наличии, false — только без остатка"),
    seller_id: int | None = Query(None, description="ID продавца для фильтрации"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список всех товаров с поддержкой фильтров.
    """
    return await ProductService.get_all_products(
        pagination,
        category_id,
        search,
        min_price,
        max_price,
        in_stock,
        seller_id,
        db    
    )


@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate = Depends(ProductCreate.as_form),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(RoleChecker("seller"))
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    return await ProductService.create_product(product, image, db, current_user)


@router.get("/category/{category_id}", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_products_by_category(
    pagination: PaginationDep,
    category: CategoryModel = Depends(get_valid_category),
    db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    return await ProductService.get_products_by_category(pagination, category, db)


@router.get("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    return await ProductService.get_product(product_id, db)


@router.put("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def update_product(
    product_id: int,
    product: ProductCreate = Depends(ProductCreate.as_form),
    image: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(RoleChecker("seller"))
):
    """
    Обновляет товар по его ID.
    """
    return await ProductService.update_product(
        product_id,
        product,
        image,
        db,
        current_user
    )
    

@router.delete("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(RoleChecker("seller"))
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    return await ProductService.delete_product(product_id, db, current_user)