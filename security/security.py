from utils.settings import settings
from datetime import datetime, timedelta, timezone
import jwt
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from typing import Annotated
from sqlmodel import Session, select
from fastapi import Depends, HTTPException, status
from database.conn import Users, get_session
from schemas.schemas import Token, TokenData

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

password_hasher = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/token"
)  # Define the token URL for OAuth2 authentication


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return password_hasher.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using the recommended hashing algorithm."""
    return password_hasher.hash(password)


async def get_user(db: Session = Depends(get_session), email: str = None):
    """Retrieve a user from the database by email."""
    query = select(Users).where(Users.email == email)
    result = db.exec(query).first()
    if result:
        return result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


async def authenticate_user(
    db: Session = Depends(get_session), email: str = None, password: str = None
):
    """Authenticate a user by verifying their email and password."""
    user = await get_user(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token with the given data and expiration time."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_session)
):
    """Retrieve the current user based on the provided JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    user = await get_user(db, email=token_data.email)
    if user:
        return user
    raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[Users, Depends(get_current_user)],
):
    """Check if the current user is active and return the user if they are."""
    if current_user.active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def verify_refresh_token(
    token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_session)
):
    """Verify the provided refresh token and return the associated user if valid."""
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )  # Decode the JWT token using the secret key and algorithm
        email: str = payload.get(
            "sub"
        )  # Extract the email (subject) from the token payload
        if (
            email is None
        ):  # If the email is not present in the token, raise an HTTP 401 Unauthorized exception
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(
            email=email
        )  # Create a TokenData instance with the extracted email
    except InvalidTokenError:
        raise HTTPException(  # If the token is invalid, raise an HTTP 401 Unauthorized exception
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user(
        db, email=token_data.email
    )  # Retrieve the user from the database using the email from the token
    if user is None:
        raise HTTPException(  # If the user is not found, raise an HTTP 401 Unauthorized exception
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user  # Return the user associated with the valid refresh token
