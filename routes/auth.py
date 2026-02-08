from fastapi import APIRouter, Depends, HTTPException, status
from schemas.schemas import UserCreate, Token
from security.security import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    oauth2_scheme,
    verify_refresh_token,
    get_current_user,
)
from fastapi.security import OAuth2PasswordRequestForm
from database.conn import Users, get_session
from sqlmodel import Session, select
from typing import Annotated
from utils.settings import settings
from datetime import timedelta

auth_route = APIRouter(prefix="/auth", tags=["auth"])


@auth_route.post("/signup")
async def signup(user: UserCreate, db: Session = Depends(get_session)):
    """
    Endpoint for user registration.
    """
    query = select(Users).where(Users.email == user.email)
    existing_user = db.exec(query).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )
    hashed_password = get_password_hash(user.password)
    new_user = Users.model_validate(user)
    new_user.password = hashed_password
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully!", "user_id": new_user.uid}


@auth_route.post("/token", response_model=Token)
async def signin(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_session),
):
    """
    Endpoint for user authentication and token generation.
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(days=7)
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        data={"user_id": user.uid, "email": user.email},
        refresh_token={"access_token": refresh_token, "token_type": "bearer"},
    )


@auth_route.get("/refresh")
async def refresh_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_session),
):
    """
    Endpoint to refresh access token using a valid refresh token.
    """
    verify_token = await verify_refresh_token(token, db)

    if not verify_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user_email = verify_token.email
    new_access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user_email}, expires_delta=new_access_token_expires
    )
    new_refresh_token = create_access_token(
        data={"sub": user_email}, expires_delta=timedelta(days=7)
    )
    return Token(
        access_token=new_access_token,
        token_type="bearer",
        data={"email": user_email},
        refresh_token={"access_token": new_refresh_token, "token_type": "bearer"},
    )
