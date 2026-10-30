"""Session, CSRF, and role authorization helpers."""
from __future__ import annotations

import hmac
import secrets
from typing import Any

from fastapi import HTTPException, Request

ROLE_PAGES = {
    "Admin": {"sales", "inventory", "catalogue", "reports", "users", "drugs", "stock"},
    "InventoryManager": {"inventory", "catalogue", "reports", "drugs", "stock"},
    "Pharmacist": {"reports", "drugs", "stock"},
    "Cashier": {"sales"},
}
VALID_ROLES = tuple(ROLE_PAGES)


def current_user(request: Request) -> dict[str, Any] | None:
    user = request.session.get("user")
    if not isinstance(user, dict) or user.get("role") not in ROLE_PAGES:
        return None
    return user


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_role(request: Request, page: str) -> dict[str, Any]:
    user = require_user(request)
    if page not in ROLE_PAGES[user["role"]]:
        raise HTTPException(status_code=403, detail="You are not authorized to access this page.")
    return user


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not isinstance(token, str) or len(token) < 32:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def verify_csrf(request: Request, submitted: str | None) -> None:
    expected = request.session.get("csrf_token", "")
    if not submitted or not expected or not hmac.compare_digest(str(expected), str(submitted)):
        raise HTTPException(status_code=403, detail="The form expired. Reload the page and try again.")
    request.session["csrf_token"] = secrets.token_urlsafe(32)


def new_sale_nonce(request: Request) -> str:
    nonce = request.session.get("sale_nonce")
    if not isinstance(nonce, str):
        nonce = secrets.token_urlsafe(24)
        request.session["sale_nonce"] = nonce
    return nonce
