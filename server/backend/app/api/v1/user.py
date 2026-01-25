from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from app.core.config import settings

from typing import List
from app.utils.security import oauth2_scheme
from app.db.database import get_session
from app.db.models.user import User, UserCreate, UserRead, Token
from app.utils.security import get_password_hash, verify_password, create_access_token, get_current_user

import logging

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
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    expires_at = datetime.utcnow() + access_token_expires
    db_token = Token(
        user_id=user.id,
        token=access_token,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    session.add(db_token)
    await session.commit()

    #logger.info(f"Пользователь вошёл: {user.email} (id={user.id})")
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    session=Depends(get_session),
    token: str = Depends(oauth2_scheme)
):
    # Удаляем токен из БД
    stmt = select(Token).where(Token.token == token)
    db_token = await session.exec(stmt)
    db_token = db_token.first()

    if db_token:
        await session.delete(db_token)
        await session.commit()

    return {"message":"Logged out"}

@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    #logger.info(f"Запрос профиля пользователя: {current_user.email} (id={current_user.id})")
    return current_user.model_dump()