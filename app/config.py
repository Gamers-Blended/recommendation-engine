from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongo_uri: str
    mongo_db: str = "products"
    redis_url: str = "redis://redis:6379"
    cache_tl_seconds: int = 3600
    recommendation_limit: int = 10
    service_secret: str # shared with Spring Boot

    class Config:
        env_file = ".env"

settings = Settings()