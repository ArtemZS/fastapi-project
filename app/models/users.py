from sqlalchemy import String, Boolean
from sqlalchemy.orm import  Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.orders import Order
from app.models.products import Product
from app.models.cart_items import CartItem
from app.models.reviews import Review
from app.schemas.users import UserRole

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(String, default=UserRole.BUYER)
    
    # Связь с табллицей Products, если пользователь - продавец 
    products: Mapped[list["Product"]] = relationship(back_populates="seller")
    
    # Связь с таблицей Reviews, если пользователь - покупатель
    reviews: Mapped[list["Review"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    # Связь с таблицей CartItems, если пользователь - покупатель
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    
    # Связь с таблицей Orders, если пользователь - покупатель
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")