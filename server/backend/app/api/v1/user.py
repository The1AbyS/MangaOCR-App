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

router = APIRouter(tags=["users"])


@router.post("/register", response_model=UserRead)
async def register(user_in: UserCreate, session=Depends(get_session)):
    # Проверяем, существует ли уже
    stmt = select(User).where(User.email == user_in.email)
    existing = await session.exec(stmt)
    if existing.first():
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
    return db_user


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session=Depends(get_session)
):
    stmt = select(User).where(User.email == form_data.username)
    result = await session.exec(stmt)
    user = result.first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Сохраняем токен в БД
    expires_at = datetime.now(timezone.utc) + access_token_expires
    db_token = Token(
        user_id=user.id,
        token=access_token,
        expires_at=expires_at
    )
    session.add(db_token)
    await session.commit()

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
    return current_user