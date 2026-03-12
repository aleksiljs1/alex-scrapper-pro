from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str = "mongodb://mongodb:27017"
    MONGODB_DB_NAME: str = "facebook_scraper"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # Scraper
    SCRAPER_CONTAINER_NAME: str = "scraper-bot"
    SHARED_VOLUME_PATH: str = "/tmp/facebook_data"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Facebook credentials (passed to bot)
    FB_USERNAME: str = ""
    FB_PASSWORD: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
