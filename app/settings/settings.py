from decimal import Decimal
from pathlib import Path

from pydantic import Field
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

    # Trading Parameters
    KALSHI_FEE_RATE: float = 0.07
    MIN_PROFIT_THRESHOLD: float = 0.0
    DRY_RUN: bool = True
    SHUTDOWN_BALANCE: Decimal = 10.00
    MINIMUM_WALLET_BALANCE: Decimal = Field(..., description="Minimum wallet balance required")

    # API & Execution Configuration
    ENABLE_API: bool = True
    # Format: '[["POLY_ID_1", "KALSHI_TICKER_1"], ["POLY_ID_2", "KALSHI_TICKER_2"]]'
    TARGET_MARKETS: str = "[]"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR_2 / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
