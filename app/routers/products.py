from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from sqlalchemy import func, select, update, desc
from decimal import Decimal
from pathlib import Path
import uuid

from app.models.products import Product as ProductModel
from app.schemas.products import Product as ProductSchema, ProductCreate, ProductList
from app.schemas.paginations import PaginationDep
from app.auth import RoleChecker
from app.models.users import User as UserModel
from app.services import _get_active_category

from app.db_depends import  get_async_db
from sqlalchemy.ext.asyncio import AsyncSession


BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "products"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 097 152 байт


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"]
)


async def save_product_image(file: UploadFile) -> str:
    """
    Сохраняет изображение товара и возвращает относительный URL.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only JPG, PNG or WebP images are allowed")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image is too large")

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / file_name
    file_path.write_bytes(content)

    return f"/media/products/{file_name}"


def remove_product_image(url: str | None) -> None:
    """
    Удаляет файл изображения, если он существует.
    """
    if not url:
        return
    relative_path = url.lstrip("/")
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()   


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
    # Проверка логики min_price <= max_price
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price"
        )
    # Формируем список фильтров
    filters = [ProductModel.is_active == True]
    if category_id is not None:
        filters.append(ProductModel.category_id == category_id)
    """        
    if search is not None:
        search_value = search.strip()
        if search_value:
            # Регистронезависимый поиск
            filters.append(ProductModel.name.ilike(f"%{search_value}%"))
    """
    if min_price is not None:
        filters.append(ProductModel.price >= min_price)
        
    if max_price is not None:
        filters.append(ProductModel.price <= max_price)
    
    if in_stock is not None:
        filters.append(ProductModel.stock > 0 if in_stock else ProductModel.stock == 0)  
    
    if seller_id is not None:
        filters.append(ProductModel.seller_id == seller_id)
    
    rank_col = None
    if search:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(ProductModel.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label("rank")

    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    total = await db.scalar(total_stmt) or 0

    page = pagination.page
    page_size = pagination.page_size
    # Основной запрос (если есть поиск — добавим ранг в выборку и сортировку)
    if rank_col is not None:
        products_stmt = (
            select(ProductModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(products_stmt)  #? Выполняем запрос, который возвращает кортежи (ProductModel, rank)
        items = [row[0] for row in result.all()]    # сами объекты
        # при желании можно вернуть ранг в ответе
        # ranks = [row.rank for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*filters)
            .order_by(ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await db.scalars(products_stmt)).all()

    return ProductList(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size
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
    # Проверяем, существует ли активная категория
    await _get_active_category(product.category_id, db, status_code=status.HTTP_400_BAD_REQUEST)
    
    image_url = await save_product_image(image) if image else None
    # Создаём товар
    db_product = ProductModel(
        **product.model_dump(),
        seller_id=current_user.id,
        image_url=image_url
    )
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)
    return db_product


@router.get("/category/{category_id}", response_model=ProductList, status_code=status.HTTP_200_OK)
async def get_products_by_category(
    category_id: int,
    pagination: PaginationDep,
    db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    await _get_active_category(category_id, db, status_code=status.HTTP_404_NOT_FOUND)
    filters = [ProductModel.category_id == category_id, ProductModel.is_active == True]
    total_stmt = select(func.count()).select_from(ProductModel).where(*filters)
    total = await db.scalar(total_stmt) or 0
    
    page = pagination.page
    page_size = pagination.page_size
    product_result = await db.scalars(
        select(ProductModel).where(*filters)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = product_result.all()
    return ProductList(items=items, total=total, page=page, page_size=page_size)


@router.get("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    # Проверяем, существует ли активный товар
    product = await db.scalar(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    # Проверяем, существует ли активная категория
    await _get_active_category(product.category_id, db, status_code=status.HTTP_400_BAD_REQUEST)

    return product


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
    # Проверяем, существует ли товар
    db_product = await db.scalar(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or inactive")
    if db_product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only update your own products")
    # Проверяем, существует ли активная категория
    await _get_active_category(product.category_id, db, status_code=status.HTTP_400_BAD_REQUEST)

    # Обновляем товар
    await db.execute(
        update(ProductModel).
        where(ProductModel.id == product_id).
        values(**product.model_dump())
    )
    
    if image:
        remove_product_image(db_product.image_url)  #? Удаляем старое изображение, если было
        db_product.image_url = await save_product_image(image)  #? Сохраняем новое изображение и обновляем URL
    await db.commit()
    await db.refresh(db_product) #? Для консистентности данных
    return db_product


@router.delete("/{product_id}", response_model=ProductSchema, status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(RoleChecker("seller"))
):
    """
    Выполняет мягкое удаление товара, если он принадлежит текущему продавцу (только для 'seller').
    """
    # Проверяем, существует ли активный товар
    product = await db.scalar(
        select(ProductModel).where(ProductModel.id == product_id, 
                                ProductModel.is_active == True)
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Product not found or inactive")
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only delete your own products")

    # Изменяем объект установив is_active=False и сохраняем
    product.is_active = False
    remove_product_image(product.image_url)  #? Удаляем изображение товара при удалении
    
    await db.commit()
    return product