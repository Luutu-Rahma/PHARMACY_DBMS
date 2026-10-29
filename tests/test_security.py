import hashlib

from app.passwords import hash_password, verify_password


def test_legacy_sha256_demo_password_verification():
    password = "Lrahma@123"
    digest = hashlib.sha256(password.encode()).hexdigest()
    assert verify_password(password, digest) == (True, True)
    assert verify_password("wrong-password", digest) == (False, True)


def test_argon2_new_password_verification():
    encoded = hash_password("Better-demo-password-2026")
    assert encoded.startswith("$argon2id$")
    assert verify_password("Better-demo-password-2026", encoded) == (True, False)
    assert verify_password("wrong-password", encoded) == (False, False)
