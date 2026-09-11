from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import HTTPBearer
from .config import settings
from .auth import SECRET_KEY, ALGORITHM

# Reuse the same HTTPBearer scheme from auth
_bearer_scheme = HTTPBearer()


async def get_current_business_id(
    credentials = Depends(_bearer_scheme),
) -> str:
    """
    Extract and validate the `business_id` claim from the JWT.

    This dependency is intended for endpoints that need the tenant context
    but do not need the full Staff object.

    Raises:
        401 if the token is invalid, missing, or lacks the business_id claim.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token missing tenant context. Please re-login.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        business_id: str = payload.get("business_id")
        if business_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return business_id
