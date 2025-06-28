from dataclasses import dataclass
from typing import Tuple, Optional

from pydantic import create_model

from app.domain.models.platform_models import PolymarketMarket, KalshiMarket


@dataclass
class MarketPair:
    """Represents a pair of markets from polymarket and kalshi"""
    poly_id: str
    kalshi_ticker: str

# Extract fields dynamically and rename with prefixes
def pydantic_fields_with_prefix(cls, prefix: str):
    return {
        f"{prefix}{name}": (typ.annotation, None)
        for name, typ in cls.model_fields.items()
    }

def from_markets(cls, poly: PolymarketMarket, kalshi: KalshiMarket):
    """ Create the base class without matching algo data"""
    data = {
        f"poly_{k}": getattr(poly, k) for k in PolymarketMarket.model_fields
    }
    data.update({
        f"kalshi_{k}": getattr(kalshi, k) for k in KalshiMarket.model_fields
    })
    return cls(**data)

# Collect fields`
poly_fields = pydantic_fields_with_prefix(PolymarketMarket, "poly_")
kalshi_fields = pydantic_fields_with_prefix(KalshiMarket, "kalshi_")

# Create dynamic Pydantic model by mreging all fields
MatchedMarketBase = create_model("MatchedMarket", **{ **poly_fields, **kalshi_fields})
MatchedMarketBase.from_markets = classmethod(from_markets)
# Extend it to add methods
class MatchedMarket(MatchedMarketBase):
    """ Model for matched market with results of matching algo"""

    match_id : Optional[int] = None
    recall_rank: Optional[float] = None
    recall_score: Optional[float] = None
    rerank_score: Optional[float] = None
    poly_text: Optional[str] = None
    kalshi_text: Optional[str] = None

    @classmethod
    def from_base(cls, base: MatchedMarketBase, **extra_fields):
        return cls(**base.model_dump(), **extra_fields)

    @property
    def poly_token_ids(self) -> Tuple[str, str]:
        """
        Extracts Polymarket token IDs for yes/no positions.
        Returns: (yes_token_id, no_token_id)
        """
        if not self.poly_clobTokenIds:
            raise ValueError("No clobTokenIds available")

        token_ids = self.poly_clobTokenIds
        if len(token_ids) != 2:
            raise ValueError("Expected two tokens")

        return str(token_ids[0]), str(token_ids[1])

    def get_token_id(self, side: str) -> str:
        if side not in ('yes', 'no'):
            raise ValueError("Invalid side")

        yes_id, no_id = self.poly_token_ids
        return yes_id if side == 'yes' else no_id

    class Config:
        extra = 'ignore'  # This line tells Pydantic to ignore unknown fields