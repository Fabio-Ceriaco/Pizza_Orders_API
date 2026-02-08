from fastapi import FastAPI
from routes import auth, orders
from contextlib import asynccontextmanager
from database.conn import create_db_and_tables


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Starting up...")
#     create_db_and_tables()
#     yield
#     print("Shutting down...")


app = FastAPI()

app.include_router(auth.auth_route)
app.include_router(orders.orders_route)
