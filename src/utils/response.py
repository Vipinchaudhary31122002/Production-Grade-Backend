"""
utils/response.py — Standard API response wrappers.

OOP concepts applied:
- Inheritance: ``PaginatedResponse`` inherits from ``ApiResponse``, reusing
  the ``success`` / ``message`` envelope without duplication.
- Encapsulation: Pagination maths (``total_pages``) is hidden inside
  ``PaginatedResponse.create``; callers pass raw numbers and get a correct,
  fully-formed object back.
- Abstraction: Callers build responses through the class interface
  (``ApiResponse(data=…)``, ``PaginatedResponse.create(…)``) and never
  construct the dict manually.
- Generics (parametric polymorphism): Both classes are generic over ``T``,
  so a single implementation works for any data type while preserving
  full static-type information.
"""

from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Wraps every success response in a consistent envelope.

    Attributes:
        success:  Always ``True`` for a non-error response.
        message:  Human-readable status string, defaults to ``"OK"``.
        data:     The actual payload — type-safe via the generic ``T``.
    """

    success: bool = True
    message: str = "OK"
    data: T | None = None

    @classmethod
    def ok(cls, data: T, message: str = "OK") -> "ApiResponse[T]":
        """Factory method — preferred over the constructor for readability."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error(cls, message: str) -> "ApiResponse[None]":
        """Convenience factory for an unsuccessful (non-exception) response."""
        return cls(success=False, message=message, data=None)


class PaginatedResponse(ApiResponse[T], Generic[T]):
    """Extends ``ApiResponse`` with pagination metadata.

    Inherits ``success`` and ``message`` from the parent; adds the list
    of items and the page navigation fields.

    Note:
        Use the ``create`` class method instead of the constructor directly —
        it computes ``total_pages`` from the other inputs automatically.
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Build a ``PaginatedResponse``, computing ``total_pages`` internally.

        Args:
            items:      The current page's items.
            total:      Total number of records across all pages.
            page:       Current page number (1-indexed).
            page_size:  Maximum items per page.

        Returns:
            A fully populated ``PaginatedResponse`` instance.
        """
        # Encapsulate the maths so callers never compute total_pages themselves
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
