"""Authentication, role policy, password compatibility, and CSRF helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Request

from web.db import connect

ROLES = ("Admin", "InventoryManager", "Pharmacist", "Cashier")
ROLE_PAGES = {
    "Admin": {"dashboard", "sales", "inventory", "records", "reports", "users"},
    "InventoryManager": {"dashboard", "inventory", "records", "reports"},
    "Pharmacist": {"dashboard", "catalogue", "stock", "reports"},
    "Cashier": {"dashboard", "sales"},
}
PASSWORDS = PasswordHasher()


class AuthenticationRequired(Exception):
    pass


class PermissionDenied(Exception):
    pass


def hash_password(password: str) -> str:
    return PASSWORDS.hash(password)


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    """Return (valid, is_legacy_sha256)."""
    if len(stored_hash) == 64 and all(char in "0123456789abcdefABCDEF" for char in stored_hash):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, stored_hash.lower()), True
    try:
        return PASSWORDS.verify(stored_hash, password), False
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, submitted: str | None) -> None:
    expected = request.session.get("csrf_token", "")
    if not submitted or not expected or not hmac.compare_digest(expected, submitted):
        raise PermissionDenied("Your form expired. Please reload the page and try again.")


def get_current_user(request: Request) -> dict[str, Any] | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    with connect() as connection:
        return connection.execute(
            "SELECT userid, fullname, username, role FROM users WHERE userid = %s",
            (user_id,),
        ).fetchone()


def require_user(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if user is None:
        raise AuthenticationRequired
    return user


def require_role(request: Request, *roles: str) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] not in roles:
        raise PermissionDenied("You do not have permission to access that page.")
    return user
