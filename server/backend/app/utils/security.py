from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select

from app.core.config import settings
from app.db.database import get_session
from app.db.models.user import User, UserInDB, Token


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session=Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        email: str = payload.get("sub")
        exp: int = payload.get("exp")
        if email is None or exp is None:
            raise credentials_exception
        if datetime.fromtimestamp (exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Получаем наличие токена в БД
    stmt = select(Token). where(Token.token == token)
    db_token = await session.exec(stmt)
    db_token = db_token.first()
    if not db_token:
        raise credentials_exception
    
    # Полуаем пользователя
    stmt = select(User).where(User.email == email)
    user = await session.exec(stmt)
    user = user.first()
    if user is None:
        raise credentials_exception

    return {"username": user}  