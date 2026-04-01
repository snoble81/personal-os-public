"""
Configuration
Environment-based settings for Payments API Gateway
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Redis Cache - Payments
    REDIS_HOST: str = "redis-payments.orbitpay.internal"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # Payments DB (Aurora MySQL)
    DB_HOST: str = "payments-db.orbitpay.internal"
    DB_PORT: int = 3306
    DB_USER: str = "payments_api"
    DB_PASSWORD: str = ""
    DB_NAME: str = "payments"

    # Visa API (3rd Party Card Networks)
    VISA_API_URL: str = "https://api.visa.com"
    VISA_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
