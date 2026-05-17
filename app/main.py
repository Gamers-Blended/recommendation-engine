from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.mongo import connect_db, close_db
from app.routers import recommendations
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await close_db()

app = FastAPI(
    title="Recommendation Service",
    version="1.0",
    lifespan=lifespan
)

app.include_router(recommendations.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}