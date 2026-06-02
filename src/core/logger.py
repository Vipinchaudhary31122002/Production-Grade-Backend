"""
core/logger.py — Application-wide logging configuration.

OOP concepts applied:
- Encapsulation: ``TerminalFilter`` owns its filtering logic; the condition
  strings are private class attributes rather than inline literals.
- Inheritance: ``TerminalFilter`` extends ``logging.Filter``, overriding only
  ``filter`` while inheriting the rest of the standard filter machinery.
- Abstraction: ``LoggingConfigurator`` exposes a single ``configure`` class
  method.  Callers in ``main.py`` call ``configure()`` and never touch
  handlers, formatters, or logger hierarchies directly.
- Single-Responsibility: Each class is responsible for exactly one concern —
  filtering or configuration — making both independently testable.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import settings


# ── Terminal log filter ───────────────────────────────────────────────────────

class TerminalFilter(logging.Filter):
    """Allow only critical startup and database messages through to stdout.

    Keeps the developer terminal clean while the log file captures everything.
    The allowed prefixes are stored as a private class attribute so they are
    easy to extend without touching the ``filter`` logic itself.
    """

    # Private set of substrings — any record whose message contains one is shown
    _ALLOWED_SUBSTRINGS: frozenset[str] = frozenset({
        "Started server process",
        "Uvicorn running on",
        "Application startup complete",
        "Database connection",
    })

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return any(substr in msg for substr in self._ALLOWED_SUBSTRINGS)


# ── Logging configurator ──────────────────────────────────────────────────────

class LoggingConfigurator:
    """Configures the root logger and all relevant third-party loggers.

    Encapsulates every configuration decision — log level, formatter pattern,
    file rotation policy, noisy-library suppression — behind a single
    ``configure`` class method so ``main.py`` stays thin.
    """

    _FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    _DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    _LOG_DIR: Path = Path("logs")
    _LOG_FILE: str = "app.log"
    _MAX_BYTES: int = 5 * 1024 * 1024   # 5 MB
    _BACKUP_COUNT: int = 5

    # Loggers to quieten in non-debug mode
    _QUIET_LOGGERS: dict[str, int] = {
        "sqlalchemy.engine": logging.INFO,   # used in debug; WARNING otherwise
        "aiosqlite": logging.INFO,
        "uvicorn.access": logging.WARNING,
        "watchfiles": logging.WARNING,
    }

    @classmethod
    def _build_formatter(cls) -> logging.Formatter:
        """Build and return the shared log formatter."""
        return logging.Formatter(fmt=cls._FORMAT, datefmt=cls._DATE_FORMAT)

    @classmethod
    def _build_file_handler(cls, formatter: logging.Formatter) -> RotatingFileHandler:
        """Create the rotating file handler, ensuring the log directory exists."""
        cls._LOG_DIR.mkdir(exist_ok=True)
        handler = RotatingFileHandler(
            cls._LOG_DIR / cls._LOG_FILE,
            maxBytes=cls._MAX_BYTES,
            backupCount=cls._BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        return handler

    @classmethod
    def _build_stream_handler(cls, formatter: logging.Formatter) -> logging.StreamHandler:
        """Create the stdout handler with the terminal-only filter applied."""
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.addFilter(TerminalFilter())
        return handler

    @classmethod
    def configure(cls) -> None:
        """Set up the root logger and suppress noisy third-party loggers.

        Call once at application startup (before the ASGI app is created).
        """
        level = logging.DEBUG if settings.DEBUG else logging.INFO
        formatter = cls._build_formatter()

        root = logging.getLogger()
        root.setLevel(level)
        root.handlers = [
            cls._build_file_handler(formatter),
            cls._build_stream_handler(formatter),
        ]

        # Force all existing loggers to propagate to the root handler
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.handlers = []
            logger.propagate = True

        # Suppress noisy libraries
        quiet_level = logging.WARNING
        for name, debug_level in cls._QUIET_LOGGERS.items():
            effective = debug_level if settings.DEBUG else quiet_level
            logging.getLogger(name).setLevel(effective)


# ── Public helper ─────────────────────────────────────────────────────────────

def setup_logging() -> None:
    """Thin wrapper kept for compatibility with ``main.py``."""
    LoggingConfigurator.configure()
