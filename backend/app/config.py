from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://tilltrack:tilltrack123@db:5432/tilltrack"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    MOCK_MPESA: bool = True
    MPESA_ENVIRONMENT: str = "sandbox"
    MPESA_CONSUMER_KEY: str = "mock_key"
    MPESA_CONSUMER_SECRET: str = "mock_secret"
    MPESA_PASSKEY: str = "mock_passkey"
    MPESA_SHORTCODE: str = "174379"
    MPESA_CALLBACK_URL: str = "http://localhost:8000/api/payments/callback"

    # Timezone
    TIMEZONE: str = "Africa/Nairobi"

    # Pesapal billing
    PESAPAL_CONSUMER_KEY: str = ""
    PESAPAL_CONSUMER_SECRET: str = ""
    PESAPAL_BASE_URL: str = "https://cybqa.pesapal.com/pesapalv3/api/"
    PESAPAL_IPN_URL: str = "https://mpesa-service-backend.onrender.com/api/billing/callback"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
