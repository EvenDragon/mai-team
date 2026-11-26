import json
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DB
from ..db import get_db
from ..models import User, Session
from ..schemas import Login, MeOut, Message, Profile, Register, TokenOut, UserOut
from ..security import (
    DUMMY_PASSWORD_HASH,
    current_user,
    hash_password,
    verify_password,
    issue_session,
    token_hash,
    bearer,
)
from ..services import user_dict, throttle

router = APIRouter()


@router.post("/auth/register", response_model=TokenOut, status_code=201)
def register(data: Register, request: Request, db: DB = Depends(get_db)):
    throttle(request)
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Аккаунт с таким email уже существует")
    u = User(email=email, name=data.name, password_hash=hash_password(data.password))
    db.add(u)
    db.flush()
    return issue_session(db, u)


@router.post("/auth/login", response_model=TokenOut)
def login(data: Login, request: Request, db: DB = Depends(get_db)):
    throttle(request)
    u = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = verify_password(
        data.password, u.password_hash if u else DUMMY_PASSWORD_HASH
    )
    if not u or not valid:
        raise HTTPException(401, "Неверный email или пароль")
    if u.is_blocked:
        raise HTTPException(403, "Аккаунт заблокирован: " + u.block_reason)
    return issue_session(db, u)


@router.post("/auth/logout", response_model=Message)
def logout(user=Depends(current_user), auth=Depends(bearer), db: DB = Depends(get_db)):
    db.delete(db.get(Session, token_hash(auth.credentials)))
    db.commit()
    return {"detail": "Вы вышли из аккаунта"}


@router.get("/me", response_model=MeOut)
def me(user=Depends(current_user)):
    return user_dict(user, True)


@router.put("/me", response_model=MeOut)
def update_me(data: Profile, user=Depends(current_user), db: DB = Depends(get_db)):
    for key, value in data.model_dump().items():
        setattr(
            user,
            key,
            json.dumps(value, ensure_ascii=False) if key == "skills" else value,
        )
    db.commit()
    return user_dict(user, True)


@router.get("/users/{user_id}", response_model=UserOut)
def public_profile(user_id: int, user=Depends(current_user), db: DB = Depends(get_db)):
    u = db.get(User, user_id)
    if not u or (u.is_blocked and user.role != "moderator" and user.id != u.id):
        raise HTTPException(404, "Профиль не найден")
    return user_dict(u)
