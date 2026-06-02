"""
core/device_fingerprint.py — Middleware for device fingerprinting and logging.

OOP concepts applied:
- Inheritance: ``DeviceFingerprintMiddleware`` extends ``BaseHTTPMiddleware``,
  overriding only ``dispatch`` while reusing Starlette's plumbing.
- Encapsulation: ``FingerprintLoggerFactory`` owns all logger-setup details
  (path, rotation policy, formatter) and exposes only a ``create`` class
  method.  The middleware simply calls ``create()`` and gets a ready-to-use
  logger without knowing how it was built.
- Abstraction: ``DeviceFingerprintMiddleware`` delegates fingerprint assembly
  to ``_build_fingerprint``, a private method — callers (``dispatch``) never
  construct the dict directly.
- Single-Responsibility: Logger creation and request fingerprinting are in
  separate classes so each can change independently.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from logging.handlers import RotatingFileHandler


# ── Logger factory (encapsulation of logger setup) ────────────────────────────

class FingerprintLoggerFactory:
    """Creates and configures the dedicated device-fingerprint logger.

    Encapsulates the log directory, file path, rotation policy, and
    formatter so the middleware class never deals with handler internals.
    """

    _LOG_DIR: Path = Path("logs")
    _LOG_FILE: str = "device_fingerprint.log"
    _MAX_BYTES: int = 5 * 1024 * 1024  # 5 MB
    _BACKUP_COUNT: int = 5
    _LOGGER_NAME: str = "device_fingerprint"
    _FORMAT: str = "%(asctime)s | %(levelname)-8s | %(message)s"
    _DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def create(cls) -> logging.Logger:
        """Return a fully configured ``Logger`` for fingerprint records."""
        cls._LOG_DIR.mkdir(exist_ok=True)

        logger = logging.getLogger(cls._LOGGER_NAME)
        logger.setLevel(logging.INFO)

        handler = RotatingFileHandler(
            cls._LOG_DIR / cls._LOG_FILE,
            maxBytes=cls._MAX_BYTES,
            backupCount=cls._BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(fmt=cls._FORMAT, datefmt=cls._DATE_FORMAT)
        )

        logger.handlers = []   # prevent duplicate handlers on hot-reload
        logger.addHandler(handler)
        return logger


# ── Middleware ────────────────────────────────────────────────────────────────

class DeviceFingerprintMiddleware(BaseHTTPMiddleware):
    """Capture request metadata and write a fingerprint record per request.

    Recorded fields:
    - Timestamp (ISO-8601, UTC)
    - HTTP method and full URL
    - Client IP address
    - Query parameters
    - All request headers
    - Request body (decoded as JSON when possible, raw text otherwise)

    The logger is created once at instantiation time via
    ``FingerprintLoggerFactory.create()`` and reused for every request,
    avoiding repeated handler setup.
    """

    def __init__(self, app) -> None:  # type: ignore[override]
        super().__init__(app)
        # Encapsulate the logger as a private instance attribute
        self._logger: logging.Logger = FingerprintLoggerFactory.create()

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    async def _read_body(request: Request) -> Any:
        """Read and decode the request body; return parsed JSON or raw text."""
        try:
            body_bytes = await request.body()
            if not body_bytes:
                return None
            body_text = body_bytes.decode(errors="ignore")
            try:
                return json.loads(body_text)
            except json.JSONDecodeError:
                return body_text
        except Exception as exc:  # pragma: no cover — defensive
            return {"body_read_error": str(exc)}

    @staticmethod
    def _build_fingerprint(request: Request, body: Any) -> dict[str, Any]:
        """Assemble the fingerprint dict from request metadata."""
        fp: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host if request.client else None,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
        }
        if body is not None:
            fp["body"] = body
        return fp

    # ── Middleware entry point ────────────────────────────────────────────

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        body = await self._read_body(request)
        fingerprint = self._build_fingerprint(request, body)
        self._logger.info(json.dumps(fingerprint, ensure_ascii=False))
        return await call_next(request)


__all__ = ["DeviceFingerprintMiddleware"]
