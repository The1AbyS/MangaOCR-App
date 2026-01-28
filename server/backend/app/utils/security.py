from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Optional, Union
from sqlmodel import delete
from app.db.models.user import RefreshToken

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
import uuid

from app.core.config import settings
from app.db.database import get_session
from app.db.models.user import User, UserInDB, Token


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    safe_password = password[:72]
    return pwd_context.hash(safe_password)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.utcnow() + timedelta(minutes=10)
    }
    return jwt.encode(payload, settings.jwt_secret, settings.jwt_algorithm)


def create_refresh_token(user_id: int):
    return {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "expires_at": datetime.utcnow() + timedelta(days=30)
    }

async def revoke_all_tokens(user_id: int, session):
    stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
    await session.exec(stmt)
    await session.commit()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session=Depends(get_session)
) -> User:
    t0 = perf_counter()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # ───── JWT decode ─────
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        user_id: int = int(payload.get("sub"))
        exp: int = payload.get("exp")

        if user_id is None or exp is None:
            raise credentials_exception

        if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            raise credentials_exception

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    t1 = perf_counter()

    # ───── Token lookup ─────
    stmt = select(Token).where(Token.token == token)
    db_token = await session.exec(stmt)
    db_token = db_token.first()

    if not db_token:
        raise credentials_exception

    t2 = perf_counter()

    # ───── User lookup ─────
    user = await session.get(User, user_id)

    if user is None:
        raise credentials_exception

    t3 = perf_counter()

    print(
        f"[AUTH TIMING] "
        f"jwt={(t1-t0)*1000:.1f}ms | "
        f"token_db={(t2-t1)*1000:.1f}ms | "
        f"user_db={(t3-t2)*1000:.1f}ms | "
        f"total={(t3-t0)*1000:.1f}ms"
    )

    return user