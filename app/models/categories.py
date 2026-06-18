from typing import Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    #? Связь с продуктами один-ко-многим
    products: Mapped[list["Product"]] = relationship(
        # "Product", #? можно не писать, так как Mapped
        back_populates="category"
    )

    #? самоссылка для организации иерархии категорий
    #? remote
    parent: Mapped[Optional["Category"]] = relationship(
        # "Category", #? можно не писать, так как Mapped
        back_populates="children",
        #? remote_side показывает, что это родительская сторона связи, а не дочерняя
        remote_side="Category.id" #? или remote_side=[id]
    )
    children: Mapped[list["Category"]] = relationship(
        # "Category", #? можно не писать, так как Mapped
        back_populates="parent"
    )
    
#? parent_id: Физический столбец в БД (внешний ключ).

#? parent: Удобный доступ к объекту-родителю в коде.

#? children: Удобный доступ ко всем вложенным категориям.

#? products: Связь с другой таблицей, позволяющая получить все товары, привязанные к этой конкретной категории.

'''
if __name__ == "__main__":
    from sqlalchemy.schema import CreateTable
    print(CreateTable(Category.__table__))'''