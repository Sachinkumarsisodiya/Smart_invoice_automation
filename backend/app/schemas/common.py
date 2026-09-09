from typing import Generic, TypeVar, List, Any
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def create(cls, items: List[T], total: int, page: int, page_size: int) -> "PaginatedResponse[T]":
        import math
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )
