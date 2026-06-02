"""
utils/pagination.py — Pagination parameter handling.

OOP concepts applied:
- Encapsulation: The ``offset`` / ``limit`` derivation lives inside the
  class, not in every router that needs it.  Routers only see ``page`` and
  ``page_size``; the conversion is a private implementation detail.
- Abstraction: FastAPI injects ``PaginationParams`` via ``Depends()``.
  Routers call ``pagination.offset`` and ``pagination.limit`` without knowing
  how those values are computed.
- Single-Responsibility: This class owns *only* pagination concerns; it does
  not touch DB sessions or HTTP responses.
"""

from dataclasses import dataclass
from fastapi import Query


@dataclass
class PaginationParams:
    """Dependency-injectable pagination parameters.

    Inject via ``Depends()`` in any route that needs paging::

        @router.get("/")
        async def list_items(pagination: Annotated[PaginationParams, Depends()]):
            items = await repo.list(offset=pagination.offset, limit=pagination.limit)

    Attributes:
        page:       Current page number, 1-indexed (minimum: 1).
        page_size:  Number of items per page (range: 1 – 100).
    """

    page: int = Query(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Query(
        default=10, ge=1, le=100, description="Items per page (max 100)"
    )

    # ── Derived / computed properties (encapsulation) ─────────────────────

    @property
    def offset(self) -> int:
        """Row offset for SQL ``OFFSET`` clause."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Row count for SQL ``LIMIT`` clause — alias for ``page_size``."""
        return self.page_size

    def __repr__(self) -> str:
        return (
            f"PaginationParams(page={self.page}, page_size={self.page_size}, "
            f"offset={self.offset})"
        )
