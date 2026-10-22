import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1
_SALT_BYTES = 16
_DKLEN = 32


def hash_password(password: str) -> str:
    """scrypt 해시(D-019). 파라미터와 salt를 함께 저장한다: scrypt$n$r$p$salt$hash"""
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """형식이 깨진 해시는 예외 없이 False."""
    try:
        scheme, n, r, p, salt_hex, hash_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(hash_hex)
        digest = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)
