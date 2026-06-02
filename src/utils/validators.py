"""
utils/validators.py — Reusable Pydantic field validators.

OOP concepts applied:
- Encapsulation: Each validation rule is hidden inside its own class
  (``PasswordValidator``, ``UsernameValidator``).  Callers only call the
  public ``validate`` class-method; the regex patterns and error messages are
  private class attributes.
- Abstraction: ``BaseFieldValidator`` defines the shared contract — a single
  ``validate`` class-method — so new validators are drop-in additions.
- Inheritance: Concrete validators extend ``BaseFieldValidator`` and only
  override the parts that differ (``_RULES`` dict or ``_PATTERN``), reusing
  the base-class scaffolding for the rest.
- Polymorphism: Any object that is a ``BaseFieldValidator`` subclass can be
  used wherever a validator is expected; the caller doesn't need to know which
  concrete rule-set is active.
"""

import re
from abc import ABC, abstractmethod
from typing import Annotated

from pydantic import AfterValidator


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseFieldValidator(ABC):
    """Contract every field validator must fulfil.

    Subclasses declare their rules as class attributes and implement
    ``validate``, which Pydantic calls via ``AfterValidator``.
    """

    @classmethod
    @abstractmethod
    def validate(cls, value: str) -> str:  # pragma: no cover
        """Validate *value* and return it unchanged, or raise ``ValueError``."""
        raise NotImplementedError


# ── Concrete validators ───────────────────────────────────────────────────────

class PasswordValidator(BaseFieldValidator):
    """Enforces a strong-password policy.

    Rules are encoded as a dict of ``{regex: error_message}`` pairs so that
    adding a new rule is a one-line change.  The minimum length is checked
    first for a fast early exit.
    """

    _MIN_LENGTH: int = 8

    # Each entry: compiled pattern → user-facing error message
    _RULES: list[tuple[re.Pattern[str], str]] = [
        (re.compile(r"[A-Z]"), "Password must contain an uppercase letter"),
        (re.compile(r"\d"),    "Password must contain a digit"),
        (re.compile(r'[!@#$%^&*(),.?":{}|<>]'), "Password must contain a special character"),
    ]

    @classmethod
    def validate(cls, value: str) -> str:
        if len(value) < cls._MIN_LENGTH:
            raise ValueError(f"Password must be at least {cls._MIN_LENGTH} characters")
        for pattern, message in cls._RULES:
            if not pattern.search(value):
                raise ValueError(message)
        return value


class UsernameValidator(BaseFieldValidator):
    """Enforces username format rules (length, allowed characters).

    A single pattern encodes all rules.  Breaking it into a separate class
    keeps ``PasswordValidator`` focused on its own concern.
    """

    _PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
    _ERROR: str = "Username must be 3-30 chars: letters, numbers, underscores only"

    @classmethod
    def validate(cls, value: str) -> str:
        if not cls._PATTERN.match(value):
            raise ValueError(cls._ERROR)
        return value


# ── Pydantic type aliases (public API used by schemas) ────────────────────────

#: Use as a field type in any Pydantic model to enforce the strong-password rules.
StrongPassword = Annotated[str, AfterValidator(PasswordValidator.validate)]

#: Use as a field type in any Pydantic model to enforce the username format rules.
ValidUsername = Annotated[str, AfterValidator(UsernameValidator.validate)]
