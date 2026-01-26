from fastapi import APIRouter, Body, Depends, HTTPException, status
import time
from jose import JWTError, jwt
from sqlmodel import delete, select
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from app.core.config import settings

from typing import List
from app.utils.security import create_refresh_token, oauth2_scheme
from app.db.database import get_session
from app.db.models.user import RefreshToken, User, UserCreate, UserRead, Token
from app.utils.security import get_password_hash, verify_password, create_access_token, get_current_user

import logging

import functools

def timing(fn):
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"{fn.__name__} -> {elapsed:.2f} ms")
        return result
    return wrapper

# Настройка логирования
logger = logging.getLogger("users")
logger.setLevel(logging.INFO)  # Можно INFO или DEBUG

# Добавим StreamHandler (вывод в консоль)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
ch.setFormatter(formatter)
logger.addHandler(ch)

router = APIRouter(tags=["users"])


@router.post("/register", response_model=UserRead)
async def register(user_in: UserCreate, session=Depends(get_session)):
    stmt = select(User).where(User.email == user_in.email)
    existing = await session.exec(stmt)
    if existing.first():
        logger.warning(f"Попытка регистрации с уже существующим email: {user_in.email}")
        raise HTTPException(
            status_code=400, detail="Email already registered"
        )

    hashed = get_password_hash(user_in.password)
    db_user = User(
        **user_in.model_dump(exclude={"password"}),
        hashed_password=hashed
    )
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    logger.info(f"Новый пользователь зарегистрирован: {db_user.email} (id={db_user.id})")
    return db_user


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_session)
):
    stmt = select(User).where(User.email == form_data.username)
    result = await session.exec(stmt)
    user = result.first()

    if user:
        await session.refresh(user)

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Неудачная попытка входа: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(user.id)
    refresh = create_refresh_token(user.id)

    session.add(RefreshToken(**refresh))
    session.add(Token(
        token=access_token, 
        user_id=user.id,
        expires_at=datetime.utcnow() + access_token_expires
    ))
    await session.commit()

    #logger.info(f"Пользователь вошёл: {user.email} (id={user.id})")

    return {
        "access_token": access_token,
        "refresh_token": str(refresh["id"]),
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    refresh_token: str,
    session=Depends(get_session)
):
    await session.exec(
        delete(RefreshToken).where(RefreshToken.id == refresh_token)
    )
    await session.commit()

@router.get("/me", response_model=UserRead)
async def get_me(
    token: str = Depends(oauth2_scheme),
    session=Depends(get_session)
) -> User:

    
    if not token or token == "Bearer":

        raise HTTPException(401, "No token provided")
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: int = int(payload.get("sub"))
        if not user_id:

            raise HTTPException(status_code=401)
    except (JWTError, ValueError, TypeError) as e:

        raise HTTPException(status_code=401)

    user = await session.get(User, user_id)

    if not user:
        raise HTTPException(status_code=401)

    return user

@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    session=Depends(get_session)
):
    stmt = select(RefreshToken).where(
        RefreshToken.id == refresh_token,
        RefreshToken.expires_at > datetime.utcnow()
    )
    token = (await session.exec(stmt)).first()

    if not token:
        raise HTTPException(status_code=401)

    access_token = create_access_token(token.user_id)
    return {"access_token": access_token}
