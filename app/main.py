import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo import AsyncMongoClient

from app.routers import products

@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database_name = os.getenv("MONGO_DB_NAME", "local")

    client = AsyncMongoClient(mongo_uri)

    try:
        await client.admin.command('ping')
        print("Successfully connected to MongoDB")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise e
    
    app.state.mongo_client = client
    app.state.db = client[database_name]

    print(f"Using database: {database_name}")

    yield
    client.close()

app = FastAPI(
    title="Product Recommendation Engine API",
    description="API for suggesting products",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(products.router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}