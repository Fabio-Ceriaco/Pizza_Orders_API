from sqlmodel import SQLModel, Field
from uuid import UUID
from pydantic import EmailStr
from pydantic import BaseModel


# Schemas for User
class UserCreate(SQLModel):
    name: str = Field(min_length=3)
    email: EmailStr
    password: str


class UserRead(SQLModel):
    uid: UUID
    name: str
    email: EmailStr
    active: bool
    admin: bool


class UserUpdate(SQLModel):
    name: str = Field(min_length=3, default=None)
    email: EmailStr = None
    hashed_password: str = None
    active: bool = None
    admin: bool = None


# Schemas for Item


class ItemCreate(SQLModel):
    name: str
    quantity: int = Field(default=0)
    flavor: str = Field(default="")
    size: str = Field(default="")
    unit_price: float = Field(default=0.0)
    order_uid: UUID | None = None


class ItemRead(SQLModel):
    uid: UUID
    name: str
    quantity: int
    flavor: str
    size: str
    unit_price: float
    order_uid: UUID


class ItemUpdate(SQLModel):
    name: str = None
    quantity: int = None
    flavor: str = None
    size: str = None
    unit_price: float = None


# Schemas for Order
class OrderCreate(SQLModel):
    user_uid: UUID


class OrderRead(SQLModel):
    uid: UUID
    status: str
    user_uid: UUID
    total: float
    items: list[ItemRead] = []


class OrderUpdate(SQLModel):
    status: str = None
    user_uid: UUID = None
    total: float = None


# Token
class Token(SQLModel):
    access_token: str
    token_type: str
    data: dict | None = None
    refresh_token: dict | None = None


class TokenData(SQLModel):
    email: EmailStr | None = None
