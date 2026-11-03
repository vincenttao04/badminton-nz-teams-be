from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_secret(secret: str) -> str:
    """Hash a password or team access detail with Argon2id."""
    return _hasher.hash(secret)


def verify_secret(secret: str, hashed: str) -> bool:
    """Check a secret against its Argon2id hash, returning False on a mismatch."""
    try:
        return _hasher.verify(hashed, secret)
    except VerifyMismatchError:
        return False
