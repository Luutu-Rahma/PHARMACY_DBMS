"""Password helpers shared by the Tkinter desktop application's login/forms."""

import hashlib
import hmac

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> tuple[bool, bool]:
    """Return (valid, is_legacy_sha256_digest)."""
    if len(stored_hash) == 64 and all(char in "0123456789abcdefABCDEF" for char in stored_hash):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(digest, stored_hash.lower()), True
    try:
        return _hasher.verify(stored_hash, password), False
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False, False
