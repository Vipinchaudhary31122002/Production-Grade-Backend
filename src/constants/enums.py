"""
constants/enums.py — Application-wide enumerations.

OOP concepts applied:
- Inheritance: Each enum inherits from StrEnum, gaining string-comparison
  behaviour and a rich set of enum utilities without duplicating any logic.
- Encapsulation: All related constant values are grouped inside their own
  enum class, hiding the raw strings behind a typed interface.
- Abstraction: Callers work with e.g. UserRole.ADMIN instead of the
  literal "admin", abstracting away the underlying string representation.
"""

from enum import StrEnum


class UserRole(StrEnum):
    """Defines the permission tiers available to a user account.

    Inherits from StrEnum so instances compare equal to their string values
    (``UserRole.ADMIN == "admin"`` is True) — useful for DB storage and JWT claims.
    """

    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"

    # ── Class-level helpers (encapsulation of related logic) ──────────────

    @classmethod
    def privileged_roles(cls) -> frozenset["UserRole"]:
        """Return the set of roles considered privileged (admin-level access)."""
        return frozenset({cls.ADMIN, cls.MODERATOR})

    def is_privileged(self) -> bool:
        """Return True if this role has elevated permissions."""
        return self in self.privileged_roles()


class TokenType(StrEnum):
    """Distinguishes the two JWT token types issued by the auth system.

    Keeping token-type constants here prevents magic strings from spreading
    across the codebase.
    """

    ACCESS = "access"
    REFRESH = "refresh"

    def is_access(self) -> bool:
        """Convenience check — avoids string literals at call sites."""
        return self == TokenType.ACCESS

    def is_refresh(self) -> bool:
        return self == TokenType.REFRESH


class UserStatus(StrEnum):
    """Lifecycle states a user account can be in.

    Encapsulates the transition rules via ``can_login``, keeping business
    logic out of routers and services.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"

    def can_login(self) -> bool:
        """Return True if a user with this status is allowed to authenticate."""
        return self == UserStatus.ACTIVE
