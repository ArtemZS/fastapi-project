from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db
from app.models.reviews import Review as ReviewModel
from app.schemas.reviews import Review as ReviewSchema, ReviewCreate, ReviewList
from app.schemas.paginations import PaginationDep
from app.models.users import User as UserModel
from app.models.products import Product as ProductModel
from app.core.security import RoleChecker
from app.services import _recalculate_product_rating
from app.services_for_routers.reviews import ReviewService

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)

router_v2 = APIRouter(
    prefix="/v2/reviews",
    tags=["v2/reviews"]
)


@router.get("/", response_model=ReviewList, status_code=status.HTTP_200_OK)
async def get_reviews(
    pagination: PaginationDep, 
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получает список всех отзывов.
    """
    total = await db.scalar(select(func.count(ReviewModel.id)).where(ReviewModel.is_active == True)) or 0

    page = pagination.page
    page_size = pagination.page_size
    reviews = await db.scalars(
        select(ReviewModel)
        .where(ReviewModel.is_active == True)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = reviews.all()
    return ReviewList(items=items, total=total, page=page, page_size=page_size)


@router.get("/products/{product_id}", response_model=ReviewList, status_code=status.HTTP_200_OK)
async def get_reviews_by_product(
    product_id: int,
    pagination: PaginationDep,
    rating: int | None = Query(None, ge=1, le=5, description="Фильтр по рейтингу от 1 до 5"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получает отзывы по ID товара.
    """

    product = await db.scalar(select(
        ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True 
            )
    )
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive") 
    
    filters = [ReviewModel.product_id == product_id, ReviewModel.is_active == True]
    if rating is not None:
        filters.append(ReviewModel.rating == rating)
    
    page = pagination.page
    page_size = pagination.page_size
    reviews = await db.scalars(
        select(ReviewModel)
        .where(*filters)
        .order_by(ReviewModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = reviews.all()
    total = await db.scalar(
        select(func.count(ReviewModel.id))
        .where(*filters)
    ) or 0
    return ReviewList(items=items, total=total, page=page, page_size=page_size)


@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate = Depends(ReviewCreate.as_form),
    current_user: UserModel = Depends(RoleChecker("buyer")),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создает новый отзыв для товара.
    """
    # Проверяем, что товар существует и активен
    product = await db.scalar(
        select(ProductModel).where(
            ProductModel.id == review.product_id,
            ProductModel.is_active == True
        )
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    # Создаем новый отзыв
    db_review = ReviewModel(**review.model_dump(), user_id=current_user.id) 
    db.add(db_review)
    
    new_rating = await _recalculate_product_rating(review.product_id, db)
    # Обновляем рейтинг товара
    product.rating = new_rating
    await db.commit()
    await db.refresh(db_review)
    return db_review


@router.delete("/{review_id}", response_model=ReviewSchema, status_code=status.HTTP_200_OK)
async def delete_review(
    review_id: int,
    current_user: UserModel = Depends(RoleChecker(["buyer", "admin"])),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Удаляет отзыв по ID.
    """
    #? Получаем отзыв вместе с товаром, чтобы потом пересчитать рейтинг
    review = await db.scalar(
        select(ReviewModel)
        .options(joinedload(ReviewModel.product))
        .where(
            ReviewModel.id == review_id,
            ReviewModel.is_active == True
        )
    )
    
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found or inactive")
    
    if current_user.role != "admin" and review.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own reviews")

    if not review.product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated product for this review not found")

    review.is_active = False
    await db.flush() #? flush нужен, чтобы изменения были видны при пересчете рейтинга, не дожидаясь коммита
    
    product = review.product
    new_rating = await _recalculate_product_rating(product.id, db)
    product.rating = new_rating
    await db.commit()
    await db.refresh(review)
    
    return review
    
    
@router_v2.get("/", response_model=ReviewList, status_code=status.HTTP_200_OK)
async def get_reviews(
    pagination: PaginationDep, 
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получает список всех отзывов.
    """   
    return await ReviewService.get_reviews(pagination, db)


@router_v2.get("/products/{product_id}", response_model=ReviewList, status_code=status.HTTP_200_OK)
async def get_reviews_by_product(
    product_id: int,
    pagination: PaginationDep,
    rating: int | None = Query(None, ge=1, le=5, description="Фильтр по рейтингу от 1 до 5"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Получает отзывы по ID товара.
    """
    return await ReviewService.get_reviews_by_product(product_id, pagination, rating, db)

@router_v2.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate = Depends(ReviewCreate.as_form),
    current_user: UserModel = Depends(RoleChecker("buyer")),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создает новый отзыв для товара.
    """
    return await ReviewService.create_review(review, current_user, db)

@router_v2.delete("/{review_id}", response_model=ReviewSchema, status_code=status.HTTP_200_OK)
async def delete_review(
    review_id: int,
    current_user: UserModel = Depends(RoleChecker(["buyer", "admin"])),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Удаляет отзыв по ID.
    """
    return await ReviewService.delete_review(review_id, current_user, db)