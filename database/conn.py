from sqlmodel import SQLModel, create_engine, Session, Field, Relationship
from utils.settings import settings
from uuid import uuid4, UUID
from enum import Enum


engine = create_engine(settings.DATABASE_URL, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


# Models for SQLModel


# User model
class Users(SQLModel, table=True):
    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    email: str = Field(unique=True, nullable=False)
    password: str = Field(
        min_length=8, nullable=False, regex=r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"
    )
    active: bool = Field(default=True)
    admin: bool = Field(default=False)

    orders: list["Orders"] = Relationship(back_populates="user")


# Item model
class Items(SQLModel, table=True):
    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    quantity: int = Field(default=0)
    flavor: str = Field(default="")
    size: str = Field(default="")
    unit_price: float = Field(default=0.0)
    order_uid: UUID = Field(foreign_key="orders.uid")

    order: Orders = Relationship(back_populates="items")


# Status Enum for Order
class MyStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Order model
class Orders(SQLModel, table=True):
    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    status: MyStatus = Field(default=MyStatus.PENDING)
    user_uid: UUID = Field(foreign_key="users.uid")
    total: float = Field(default=0.0)

    user: Users = Relationship(back_populates="orders")
    items: list["Items"] = Relationship(back_populates="order", cascade_delete=True)
