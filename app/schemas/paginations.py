from pydantic import BaseModel
from fastapi import Query, Depends
from typing import Annotated

class PaginationPages(BaseModel):
    page_size: Annotated[int | None, Query(10, ge=1, le=100, description="Номер страницы для пагинации")]
    page: Annotated[int, Query(1, ge=1, description="Количество элементов на странице")] 
    
PaginationDep = Annotated[PaginationPages, Depends()]    
    