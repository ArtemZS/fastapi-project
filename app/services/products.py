from pathlib import Path
import uuid
from decimal import Decimal
from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

from app.models.products import Product as ProductModel
from app.models import Category as CategoryModel
from app.models import User as UserModel
from app.schemas.products import ProductList, ProductCreate
from app.services.categories import CategoryService  # Импортируем соседний сервис

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "products"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FILE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"]
MAX_IMAGE_SIZE = 4 * 1024 * 1024


async def save_product_image(file: UploadFile) -> str:
    """
    Сохраняет изображение товара и возвращает относительный URL.
    """
    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    if extension not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file extension: '{extension}'. Only {', '.join(ALLOWED_FILE_EXTENSIONS)} are allowed."
        )
    
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            f"Unsupported file type: '{file.content_type}'. Only {', '.join(ALLOWED_IMAGE_TYPES)} are allowed."
        )
    
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / file_name
    
    total_bytes = 0
    chunk_size = 1024 * 1024
    
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > MAX_IMAGE_SIZE:
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Image is too large")
                await out_file.write(chunk)
    except HTTPException:
        if file_path.exists():
            file_path.unlink()
        raise
    except Exception:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save image")                

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


class ProductService:

    @staticmethod
    async def get_all_products(
        pagination,
        category_id: int | None,
        search: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool | None,
        seller_id: int | None,
        db: AsyncSession
    ) -> ProductList:
        """
        Возвращает список всех товаров с поддержкой фильтров.
        """
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="min_price не может быть больше max_price"
            )

        filters = [ProductModel.is_active == True]
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        
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

        if rank_col is not None:
            products_stmt = (
                select(ProductModel, rank_col)
                .where(*filters)
                .order_by(desc(rank_col), ProductModel.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            result = await db.execute(products_stmt)
            items = [row[0] for row in result.all()]
        else:
            products_stmt = (
                select(ProductModel)
                .where(*filters)
                .order_by(ProductModel.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            items = (await db.scalars(products_stmt)).all()

        return ProductList(items=items, total=total, page=page, page_size=page_size)
        
    @staticmethod
    async def create_product(
        product: ProductCreate,
        image: UploadFile | None,
        db: AsyncSession,
        current_user: UserModel
    ) -> ProductModel:
        """
        Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
        """
        try:
            # Используем логику проверки из CategoryService
            await CategoryService.get_category_by_id(product.category_id, db)
        except HTTPException as exc:
            # Меняем 404 на 400 Bad Request, так как это ошибка входных данных формы
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with id {product.category_id} does not exist or is inactive"
                )
            raise exc
        
        image_url = await save_product_image(image) if image else None

        db_product = ProductModel(
            **product.model_dump(),
            seller_id=current_user.id,
            image_url=image_url
        )
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        return db_product
    
    @staticmethod
    async def get_products_by_category(
        pagination,
        category_id: int,
        db: AsyncSession
    ) -> ProductList:
        """
        Возвращает список товаров в указанной категории по её ID.
        """
        # Проверяем существование самой категории. Если её нет — сгенерируется 404
        await CategoryService.get_category_by_id(category_id, db)

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
    
    @staticmethod
    async def get_product(
        product_id: int,
        db: AsyncSession
    ) -> ProductModel:
        """
        Возвращает детальную информацию о товаре по его ID.
        """
        product = await db.scalar(
            select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
        )
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

        # Дополнительно проверяем, активна ли категория, к которой привязан товар
        await CategoryService.get_category_by_id(product.category_id, db)

        return product
    
    @staticmethod
    async def update_product(
        product_id: int,
        product: ProductCreate,
        image: UploadFile | None,
        db: AsyncSession,
        current_user: UserModel
    ) -> ProductModel:
        """
        Обновляет товар по его ID.
        """
        db_product = await db.scalar(
            select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
        )
        if not db_product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
            
        if db_product.seller_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")
            
        try:
            # Валидация новой категории при обновлении товара
            await CategoryService.get_category_by_id(product.category_id, db)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with id {product.category_id} does not exist or is inactive"
                )
            raise exc

        update_data = product.model_dump()
        for key, value in update_data.items():
            setattr(db_product, key, value)
        
        if image:
            remove_product_image(db_product.image_url)
            db_product.image_url = await save_product_image(image)
            
        await db.commit()
        await db.refresh(db_product)
        return db_product
    
    @staticmethod
    async def delete_product(
        product_id: int,
        db: AsyncSession,
        current_user: UserModel
    ) -> ProductModel:
        """
        Выполняет мягкое удаление товара, если он принадлежит текущему продавцу.
        """
        product = await db.scalar(
            select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
        )
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
            
        if product.seller_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own products")

        product.is_active = False
        remove_product_image(product.image_url)
        
        await db.commit()
        return product