from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR_1 = Path(__file__).resolve().parents[1]
BASE_DIR_2 = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # App environment (directly affects Kalshi's client behavior)
    APP_ENV: str = "prod"

    # Kalshi demo credentials
    KALSHI_DEMO_API_KEY: str
    KALSHI_DEMO_PRIVATE_KEY_PATH: str

    # Kalshi prod credentials
    KALSHI_PROD_API_KEY: str
    KALSHI_PROD_PRIVATE_KEY_PATH: str

    # Polymarket credentials
    POLYMARKET_API_KEY: str
    POLYMARKET_WALLET_PRIVATE_KEY: str
    POLYMARKET_WALLET_ADDR: str

    # Supabase credentials
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Extra configurations
    KALSHI_FEE_RATE: float = 0.07
    MIN_PROFIT_THRESHOLD: float = 0.0

    model_config = SettingsConfigDict(
        env_file=BASE_DIR_2 / ".env",
        env_file_encoding="utf-8"
    )

settings = Settings()