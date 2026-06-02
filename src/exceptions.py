"""
exceptions.py — Domain exceptions and FastAPI exception handlers.

OOP concepts applied:
- Inheritance: All domain exceptions form a hierarchy rooted at
  ``AppException``.  A single ``except AppException`` can catch any of
  them, while specific handlers still differentiate HTTP status codes.
  Adding a new error type means adding one subclass — zero handler changes.
- Encapsulation: Each exception class owns its ``message`` and ``status_code``
  as instance data.  HTTP translation is done in dedicated handler classes
  that inherit from ``BaseExceptionHandler``, keeping domain and HTTP concerns
  separated.
- Abstraction: ``ExceptionHandlerRegistry`` presents a single ``register``
  method to ``main.py``, hiding all the handler-wiring details.
- Polymorphism: ``BaseExceptionHandler.handle`` is overridden by every
  concrete handler; FastAPI dispatches to the right one at runtime.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# ── Domain exception hierarchy ────────────────────────────────────────────────

class AppException(Exception):
    """Base class for all application-domain exceptions.

    Carries a human-readable ``message`` and an HTTP ``status_code`` so
    concrete subclasses only need to override ``status_code``.
    """

    status_code: int = 500  # Subclasses override this class attribute

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:  # encapsulation — clean debug output
        return f"{type(self).__name__}(message={self.message!r})"


class NotFoundException(AppException):
    """Raised when a requested resource does not exist (HTTP 404)."""
    status_code: int = 404


class ConflictException(AppException):
    """Raised when a create/update conflicts with existing data (HTTP 409)."""
    status_code: int = 409


class UnauthorizedException(AppException):
    """Raised when authentication is missing or invalid (HTTP 401)."""
    status_code: int = 401


class ForbiddenException(AppException):
    """Raised when an authenticated user lacks permission (HTTP 403)."""
    status_code: int = 403


class BadRequestException(AppException):
    """Raised when the client sends semantically invalid data (HTTP 400)."""
    status_code: int = 400


# ── Abstract handler base (abstraction + polymorphism) ────────────────────────

class BaseExceptionHandler:
    """Template for turning a domain exception into a JSONResponse.

    Subclasses implement ``handle``; the registry calls it polymorphically.
    """

    exception_class: type[Exception]  # must be set by subclasses

    @staticmethod
    def build_response(status_code: int, message: str) -> JSONResponse:
        """Shared helper — encapsulates the response shape."""
        return JSONResponse(
            status_code=status_code,
            content={"detail": message},
        )

    async def handle(self, request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        raise NotImplementedError


class AppExceptionHandler(BaseExceptionHandler):
    """Handles any ``AppException`` subclass by reading its own ``status_code``."""

    exception_class = AppException

    async def handle(self, request: Request, exc: AppException) -> JSONResponse:
        return self.build_response(exc.status_code, exc.message)


class ValidationErrorHandler(BaseExceptionHandler):
    """Translates Pydantic ``RequestValidationError`` into a structured 422."""

    exception_class = RequestValidationError

    async def handle(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})


# ── Registry (encapsulates handler wiring) ────────────────────────────────────

class ExceptionHandlerRegistry:
    """Registers all exception handlers onto a FastAPI application.

    Keeps ``main.py`` clean: it calls ``register(app)`` and never needs to
    know which handlers exist or how they are wired.
    """

    # Ordered list of handler instances — extend here to add more
    _handlers: list[BaseExceptionHandler] = [
        AppExceptionHandler(),
        ValidationErrorHandler(),
    ]

    @classmethod
    def register(cls, app: FastAPI) -> None:
        """Attach every handler to *app* via ``app.exception_handler``."""
        for handler in cls._handlers:
            # Closure captures the correct handler instance via default arg
            exc_class = handler.exception_class

            async def _dispatch(
                request: Request,
                exc: Exception,
                _h: BaseExceptionHandler = handler,
            ) -> JSONResponse:
                return await _h.handle(request, exc)

            app.exception_handler(exc_class)(_dispatch)


# ── Backwards-compatible public helper ────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Thin wrapper kept for compatibility with ``main.py``."""
    ExceptionHandlerRegistry.register(app)
