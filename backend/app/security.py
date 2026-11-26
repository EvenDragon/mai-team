import hashlib
import hmac
import os
import secrets
import time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DB
from .db import get_db
from .models import Session, User

bearer = HTTPBearer(auto_error=False)


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()
    return f"scrypt${salt}${digest}"


def verify_password(password, stored):
    _, salt, expected = stored.split("$")
    actual = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()
    return hmac.compare_digest(actual, expected)


# Compute once, so a missing account still performs exactly one password check.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_session(db, user):
    token = secrets.token_urlsafe(48)
    ttl = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
    db.add(
        Session(
            token_hash=token_hash(token),
            user_id=user.id,
            expires_at=int(time.time()) + ttl,
        )
    )
    db.commit()
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl}


def current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: DB = Depends(get_db),
):
    session = db.get(Session, token_hash(auth.credentials)) if auth else None
    if not session or session.expires_at <= time.time():
        raise HTTPException(
            401, "Войдите в аккаунт", headers={"WWW-Authenticate": "Bearer"}
        )
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, "Аккаунт не найден")
    if user.is_blocked:
        raise HTTPException(403, "Аккаунт заблокирован: " + user.block_reason)
    return user


def moderator(user=Depends(current_user)):
    if user.role != "moderator":
        raise HTTPException(403, "Требуются права модератора")
    return user
