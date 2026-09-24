import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import get_db

PBKDF2_ITERATIONS = 260_000
_SESSION_DAYS = 7

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: str | None = None, iterations: int = PBKDF2_ITERATIONS) -> tuple[str, str, int]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return digest.hex(), salt, iterations


def verify_password(password: str, salt: str, expected_hash: str, iterations: int) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return hmac.compare_digest(digest.hex(), expected_hash)


def create_session(db: Session, user: models.User, days: int = _SESSION_DAYS) -> models.Session:
    token = secrets.token_urlsafe(32)
    session = models.Session(
        token=token,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def authenticate(db: Session, username: str, password: str) -> models.User | None:
    user = db.scalar(select(models.User).where(models.User.username == username))
    if not user or not user.active:
        return None
    if not verify_password(password, user.salt, user.password_hash, user.password_iterations):
        return None
    return user


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if credentials is None or not credentials.scheme.lower() == "bearer" or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.scalar(select(models.Session).where(models.Session.token == credentials.credentials))
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = db.get(models.User, session.user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")
    return user


def require_admin(user: models.User = Depends(current_user)) -> models.User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


def log_action(
    db: Session,
    user: models.User | None,
    action: str,
    target: str = "",
    detail: str = "",
) -> None:
    db.add(
        models.AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action,
            target=target,
            detail=detail,
        )
    )
    db.commit()


def get_setting(db: Session, key: str, default: str = "") -> str:
    setting = db.get(models.Setting, key)
    return setting.value if setting else default


def set_setting(db: Session, key: str, value: str) -> None:
    setting = db.get(models.Setting, key)
    if setting:
        setting.value = value
    else:
        db.add(models.Setting(key=key, value=value))
    db.commit()