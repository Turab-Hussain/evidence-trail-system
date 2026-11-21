"""Account registration, sign-in and token authentication."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from evidence_trail.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    InvalidInputError,
    NotFoundError,
    RateLimitError,
)
from evidence_trail.domain.models import User, utc_now
from evidence_trail.repositories.base import Repository
from evidence_trail.services.security import PasswordHasher, TokenService

MIN_PASSWORD_LENGTH = 8
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginThrottle:
    """Allows a few failed sign-ins per email in a time window (in-memory, per process)."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300) -> None:
        self._max = max_failures
        self._window = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, now: float | None = None) -> None:
        """Raise ``RateLimitError`` if ``key`` already failed too often recently."""
        if len(self._recent(key, now)) >= self._max:
            raise RateLimitError("Too many failed attempts. Try again in a few minutes.")

    def record_failure(self, key: str, *, now: float | None = None) -> None:
        self._recent(key, now).append(time.time() if now is None else now)

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def _recent(self, key: str, now: float | None) -> deque[float]:
        current = time.time() if now is None else now
        attempts = self._failures[key]
        while attempts and attempts[0] <= current - self._window:
            attempts.popleft()
        return attempts


class AuthService:
    """Creates accounts, checks credentials and resolves tokens to users."""

    def __init__(
        self,
        repository: Repository,
        hasher: PasswordHasher,
        tokens: TokenService,
        throttle: LoginThrottle | None = None,
    ) -> None:
        self._repo = repository
        self._hasher = hasher
        self._tokens = tokens
        self._throttle = throttle or LoginThrottle()
        # Verifying against this when the email is unknown keeps timing the same.
        self._dummy_hash = hasher.hash("not-a-real-password")

    def signup(self, name: str, email: str, password: str) -> tuple[User, str]:
        """Register a user and return ``(user, token)``.

        The very first account also adopts projects created before accounts existed.
        """
        name, email = name.strip(), self._normalise_email(email)
        if not name:
            raise InvalidInputError("Please enter your name.")
        if not _EMAIL.match(email):
            raise InvalidInputError("Please enter a valid email address.")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidInputError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        if self._repo.find_user_by_email(email) is not None:
            raise ConflictError("An account with this email already exists. Sign in instead.")

        is_first_user = self._repo.count_users() == 0
        user = self._repo.save_user(
            User(
                name=name,
                email=email,
                password_hash=self._hasher.hash(password),
                last_login_at=utc_now(),
            )
        )
        if is_first_user:
            self._repo.claim_orphan_projects(user.user_id)
        return user, self._tokens.issue(user.user_id)

    def login(self, email: str, password: str) -> tuple[User, str]:
        """Check credentials and return ``(user, token)``."""
        email = self._normalise_email(email)
        self._throttle.check(email)
        user = self._repo.find_user_by_email(email)
        stored = user.password_hash if user is not None else self._dummy_hash
        valid = self._hasher.verify(password, stored)
        if user is None or not valid:
            self._throttle.record_failure(email)
            raise AuthenticationError("Incorrect email or password.")
        self._throttle.reset(email)
        user = self._repo.save_user(user.model_copy(update={"last_login_at": utc_now()}))
        return user, self._tokens.issue(user.user_id)

    def authenticate(self, token: str) -> User:
        """Resolve a bearer token to its user."""
        user_id = self._tokens.verify(token)
        try:
            return self._repo.get_user(user_id)
        except NotFoundError as exc:
            raise AuthenticationError("Invalid session. Please sign in again.") from exc

    @staticmethod
    def _normalise_email(email: str) -> str:
        return email.strip().lower()
