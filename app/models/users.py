from sqlalchemy import String, Boolean
from sqlalchemy.orm import  Mapped, mapped_column, relationship

from app.database import Base
from app.models.orders import Order
from app.models.products import Product
from app.models.cart_items import CartItem
from app.models.reviews import Review


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[str] = mapped_column(String, default="buyer") #? "buyer" or "seller" or "admin"
    
    products: Mapped[list["Product"]] = relationship(back_populates="seller")
    reviews: Mapped[list["Review"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user", cascade="all, delete-orphan")