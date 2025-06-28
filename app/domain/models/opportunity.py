from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, model_validator

from app.domain.primitives import Platform


class ArbitrageOpportunity(BaseModel):
    """
    Represents a profitable, risk-free "buy-both" arbitrage opportunity.
    This is a simple data-transfer object and contains no logic.
    """
    # --- Core Arb Data ---
    market_id: str
    buy_yes_platform: Platform
    buy_yes_price: Decimal
    buy_no_platform: Platform
    buy_no_price: Decimal
    profit_margin: Decimal
    potential_trade_size: Decimal
    # --- Execution Data ---
    kalshi_ticker: str
    polymarket_yes_token_id: str
    polymarket_no_token_id: str


class ArbitrageOpportunityRecord(BaseModel):
    """
    Database record for arbitrage opportunities with complete market state.
    This class combines the arbitrage opportunity data with the market books
    snapshot for comprehensive historical tracking.
    """
    arbitrage_opportunity: ArbitrageOpportunity
    category: str
    market_books_snapshot: Optional[Dict[str, Any]] = Field(default=None, description="Complete market books state when arbitrage was detected")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    poly_trade_executed: bool = Field(default=False)
    poly_order_id: Optional[str] = None
    kalshi_trade_executed: bool = Field(default=False)
    kalshi_order_id: Optional[str] = None
    id: Optional[int] = Field(default=None, description="Database primary key")
    created_at: Optional[datetime] = Field(default=None, description="Database record creation timestamp")

    @model_validator(mode="before") # noqa this warning is a known issue: https://youtrack.jetbrains.com/issue/PY-34368/False-warning-This-decorator-will-not-receive-a-callable-it-may-expect-when-classmethod-is-not-the-last-applied
    @classmethod
    def combine_flat_fields_into_arb_opportunity(cls, data: Any):
        if "arbitrage_opportunity" not in data:
            arb_keys = set(ArbitrageOpportunity.model_fields.keys())
            arb_data = {k: data.pop(k) for k in list(data.keys()) if k in arb_keys}
            data["arbitrage_opportunity"] = arb_data
        return data

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v),
            Platform: lambda v: v.value,
            datetime: lambda v: v.isoformat()
        }

    def serialize(self):
        try:
            base_data = self.model_dump(mode='json', exclude_none=True)
            arb_opp_data = base_data.pop('arbitrage_opportunity', {})
            return {**base_data, **arb_opp_data}
        except Exception as e:
            raise RuntimeError(f"Failed to serialize {self.arbitrage_opportunity} in category {self.category}. Detail: {e}") from e


class ArbType(str, Enum):
    BUY_BOTH = "buy_both"
    DIRECTIONAL_YES = "directional_yes"
    DIRECTIONAL_NO = "directional_no"
    UNPROFITABLE = "unprofitable"