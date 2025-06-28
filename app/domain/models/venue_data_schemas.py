from typing import Tuple, List

from pydantic import BaseModel, Field

# --- Kalshi Schemas ---
KalshiPriceLevel = Tuple[int, int]

class KalshiSnapshotData(BaseModel):
    market_ticker: str
    yes: List[KalshiPriceLevel]
    no: List[KalshiPriceLevel] # could be optional
    class Config:
        frozen = True

class KalshiSnapshotMessage(BaseModel):
    type: str = Field(..., pattern="orderbook_snapshot")
    seq: int
    msg: KalshiSnapshotData
    class Config:
        frozen = True

class KalshiDeltaData(BaseModel):
    market_ticker: str
    price: int
    delta: int
    side: str

class KalshiDeltaMessage(BaseModel):
    type: str = Field(..., pattern="orderbook_delta")
    seq: int
    msg: KalshiDeltaData

# --- Polymarket Schemas ---
class PolyPriceLevel(BaseModel):
    price: str
    size: str

class PolyBookMessage(BaseModel):
    event_type: str = Field(..., pattern="book")
    market: str
    bids: List[PolyPriceLevel]
    asks: List[PolyPriceLevel]

class PolyChange(BaseModel):
    price: str
    side: str  # 'BUY' or 'SELL'
    size: str

class PolyPriceChangeMessage(BaseModel):
    event_type: str = Field(..., pattern="price_change")
    market: str
    changes: List[PolyChange]