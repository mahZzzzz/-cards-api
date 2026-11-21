import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import database
from app.models import LoginRequest, TokenResponse


router = APIRouter()

# Password hashing parameters (stdlib scrypt).
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SALT_BYTES = 16

# Opaque bearer tokens.
TOKEN_BYTES = 32
TOKEN_TTL_SECONDS = 8 * 60 * 60

bearer_scheme = HTTPBearer(auto_error=False)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def hash_password(password: str) -> str:
    """Return a salted scrypt hash in a self-describing string format."""

    salt = secrets.token_bytes(SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )

    return "$".join(
        (
            "scrypt",
            str(SCRYPT_N),
            str(SCRYPT_R),
            str(SCRYPT_P),
            _encode(salt),
            _encode(derived),
        )
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored scrypt hash."""

    try:
        algorithm, n_text, r_text, p_text, salt_text, hash_text = (
            stored_hash.split("$")
        )
    except (AttributeError, ValueError):
        return False

    if algorithm != "scrypt":
        return False

    try:
        n = int(n_text)
        r = int(r_text)
        p = int(p_text)
        salt = _decode(salt_text)
        expected = _decode(hash_text)
    except (ValueError, TypeError):
        return False

    # Reject malformed or excessive parameters from a corrupted row.
    if n < 2 or n > 2 ** 20 or n & (n - 1) or r < 1 or p < 1:
        return False

    try:
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
        )
    except (ValueError, MemoryError):
        return False

    return hmac.compare_digest(derived, expected)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest stored for a bearer token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token(user_id: int, ttl_seconds: int | None = None) -> str:
    """Create an opaque token and persist only its hash."""

    lifetime = TOKEN_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    token = secrets.token_urlsafe(TOKEN_BYTES)
    expires_at = (_utcnow() + timedelta(seconds=lifetime)).isoformat()

    database.create_session(hash_token(token), user_id, expires_at)

    return token


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> dict:
    """Resolve the authenticated user from a bearer token."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated")

    session = database.get_session(hash_token(credentials.credentials))

    if session is None:
        raise _unauthorized("Invalid or expired token")

    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
    except (TypeError, ValueError):
        database.delete_session(session["token_hash"])
        raise _unauthorized("Invalid or expired token")

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= _utcnow():
        database.delete_session(session["token_hash"])
        raise _unauthorized("Invalid or expired token")

    return {
        "id": session["user_id"],
        "username": session["username"],
        "role": session["role"],
    }


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Allow only users with the admin role."""

    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )

    return user


def ensure_bootstrap_admin():
    """Create the first admin from environment variables when needed.

    Startup must fail rather than fall back to default credentials.
    """

    if database.count_users() > 0:
        return

    username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

    if not username or not password:
        raise RuntimeError(
            "No users exist and bootstrap credentials are missing. "
            "Set BOOTSTRAP_ADMIN_USERNAME and BOOTSTRAP_ADMIN_PASSWORD "
            "before starting the API."
        )

    database.create_user(
        username,
        hash_password(password),
        "admin",
        _utcnow().isoformat(),
    )


@router.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    """Exchange a username and password for a bearer token."""

    user = database.get_user_by_username(credentials.username)

    if user is None or not verify_password(
        credentials.password,
        user["password_hash"],
    ):
        raise _unauthorized("Invalid username or password")

    database.delete_expired_sessions(_utcnow().isoformat())
    token = issue_token(user["id"])

    return TokenResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
    )
