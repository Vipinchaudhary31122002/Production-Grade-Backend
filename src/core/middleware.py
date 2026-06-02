"""
core/middleware.py — Application middleware classes and registration.

OOP concepts applied:
- Inheritance: ``RequestIDMiddleware`` and ``LoggingMiddleware`` both inherit
  from ``BaseHTTPMiddleware``, overriding only ``dispatch`` while reusing
  Starlette's request/response plumbing.
- Encapsulation: Each middleware class owns its own state (the logger, the
  header name constant).  ``MiddlewareRegistry`` owns the registration order
  so that no other file needs to know which middleware are active or in what
  order they must be added.
- Abstraction: ``main.py`` calls ``MiddlewareRegistry.register(app)`` and
  never references individual middleware classes.
- Single-Responsibility: Each class handles exactly one cross-cutting concern
  (request IDs, access logging, device fingerprinting, CORS).
"""

import time
import uuid
import logging

from src.core.device_fingerprint import DeviceFingerprintMiddleware

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.config import settings

logger = logging.getLogger(__name__)


# ── Request-ID middleware ─────────────────────────────────────────────────────

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Stamp every request and response with a unique ``X-Request-ID`` header.

    If the client already sends an ``X-Request-ID`` header, that value is
    echoed back unchanged (useful for end-to-end tracing).  Otherwise a new
    UUID4 is generated and stored on ``request.state`` so downstream handlers
    can reference it.
    """

    _HEADER_NAME: str = "X-Request-ID"   # encapsulated constant

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self._HEADER_NAME, str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self._HEADER_NAME] = request_id
        return response


# ── Access-logging middleware ─────────────────────────────────────────────────

class LoggingMiddleware(BaseHTTPMiddleware):
    """Log the HTTP method, path, status code, and latency for every request.

    The ``request_id`` from ``RequestIDMiddleware`` is included in the log
    line when available, making it easy to correlate logs with traces.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        request_id = getattr(request.state, "request_id", "N/A")
        logger.info(
            "%s %s -> %d (%.1fms) [request_id=%s]",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
        )
        return response


# ── Middleware registry (encapsulation) ───────────────────────────────────────

class MiddlewareRegistry:
    """Registers all application middleware onto a FastAPI instance.

    Middleware must be added in reverse execution order — the last ``add_middleware``
    call is the first to run.  Centralising this here prevents scattered
    ``app.add_middleware`` calls and makes the middleware stack easy to audit.
    """

    @staticmethod
    def register(app: FastAPI) -> None:
        """Attach all middleware to *app* in the correct order.

        Execution order (outermost → innermost):
          1. CORS        — must be outermost so pre-flight OPTIONS bypass auth
          2. Logging     — record timing before anything else strips state
          3. Fingerprint — capture raw request before body is consumed
          4. Request-ID  — stamp the ID before any logging reads it
        """
        # Added last → runs first (Starlette middleware stack is LIFO)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(DeviceFingerprintMiddleware)
        app.add_middleware(RequestIDMiddleware)


# ── Public helper ─────────────────────────────────────────────────────────────

def register_middleware(app: FastAPI) -> None:
    """Thin wrapper kept for compatibility with ``main.py``."""
    MiddlewareRegistry.register(app)
