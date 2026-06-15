from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db
from app.schemas.reviews import Review as ReviewSchema, ReviewCreate, ReviewList
from app.schemas.paginations import PaginationDep
from app.models.users import User as UserModel
from app.core.security import RoleChecker
from app.services_for_routers.reviews import ReviewService

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)

@router.get("/", response_model=ReviewList, status_code=status.HTTP_200_OK)
async def get_reviews(
    pagination: PaginationDep, 
    db: AsyncSession = Depends(get_async_db),
):
    """
    Получает список всех отзывов.
    """   
    return await ReviewService.get_reviews(pagination, db)


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
    return await ReviewService.get_reviews_by_product(product_id, pagination, rating, db)

@router.post("/", response_model=ReviewSchema, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate = Depends(ReviewCreate.as_form),
    current_user: UserModel = Depends(RoleChecker("buyer")),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создает новый отзыв для товара.
    """
    return await ReviewService.create_review(review, current_user, db)

@router.delete("/{review_id}", response_model=ReviewSchema, status_code=status.HTTP_200_OK)
async def delete_review(
    review_id: int,
    current_user: UserModel = Depends(RoleChecker(["buyer", "admin"])),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Удаляет отзыв по ID.
    """
    return await ReviewService.delete_review(review_id, current_user, db)