"""Password hashing and signed login tokens, built only on the standard library."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time

from evidence_trail.domain.exceptions import AuthenticationError

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LEN = 32


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class PasswordHasher:
    """Salted scrypt hashes in the self-describing form ``scrypt$n$r$p$salt$hash``."""

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_KEY_LEN,
        )
        return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"

    def verify(self, password: str, stored: str) -> bool:
        """Constant-time check; a malformed stored hash simply fails."""
        try:
            scheme, n, r, p, salt, expected = stored.split("$")
            if scheme != "scrypt":
                return False
            digest = hashlib.scrypt(
                password.encode("utf-8"),
                salt=_unb64(salt),
                n=int(n),
                r=int(r),
                p=int(p),
                dklen=_KEY_LEN,
            )
            return hmac.compare_digest(digest, _unb64(expected))
        except (ValueError, binascii.Error):
            return False


class TokenService:
    """Issues and checks HMAC-signed tokens: ``base64(payload).base64(signature)``.

    The payload holds the user id (``sub``) and an expiry (``exp``, unix seconds).
    """

    def __init__(self, secret: str, ttl_seconds: int) -> None:
        self._secret = secret.encode("utf-8")
        self._ttl = ttl_seconds

    def issue(self, user_id: str, *, now: float | None = None) -> str:
        issued = time.time() if now is None else now
        payload = json.dumps({"sub": user_id, "exp": int(issued + self._ttl)}).encode("utf-8")
        body = _b64(payload)
        return f"{body}.{self._sign(body)}"

    def verify(self, token: str, *, now: float | None = None) -> str:
        """Return the user id inside a valid token.

        Raises:
            AuthenticationError: if the token is malformed, forged or expired.
        """
        try:
            body, signature = token.split(".")
            if not hmac.compare_digest(signature, self._sign(body)):
                raise AuthenticationError("Invalid session. Please sign in again.")
            payload = json.loads(_unb64(body))
            user_id, expires = str(payload["sub"]), float(payload["exp"])
        except (ValueError, KeyError, TypeError, binascii.Error) as exc:
            raise AuthenticationError("Invalid session. Please sign in again.") from exc
        if (time.time() if now is None else now) >= expires:
            raise AuthenticationError("Your session has expired. Please sign in again.")
        return user_id

    def _sign(self, body: str) -> str:
        return _b64(hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest())
