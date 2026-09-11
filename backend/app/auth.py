from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import Staff
from .config import settings

# Use HTTPBearer for simplified Swagger UI (instead of OAuth2PasswordBearer)
oauth2_scheme = HTTPBearer()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    business_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
):
    """
    Create a JWT access token.

    Args:
        data: Dictionary of claims to encode (must include "sub" = staff.id)
        business_id: UUID string of the business (tenant). Embedded as
                     "business_id" claim for multi-tenant filtering.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()

    # Embed tenant context if provided
    if business_id is not None:
        to_encode["business_id"] = business_id

    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_staff(
    credentials=Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Staff:
    """
    Decode the JWT and return the authenticated Staff record.

    Raises 401 if the token is invalid or the staff member doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        staff_id: str = payload.get("sub")
        if staff_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if staff is None:
        raise credentials_exception

    return staff
