from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.domain.primitives import Platform
from shared_wallets.domain.models import ExchangeWallet


class KalshiOrder(BaseModel):
    action: Optional[str] = None
    client_order_id: Optional[str] = None
    created_time: Optional[datetime] = None
    expiration_time: Optional[datetime] = None
    no_price: Optional[int] = None
    order_id: Optional[str] = None
    side: Optional[str] = None
    status: str  # trade can possibly be resent so we don't freeze the status
    ticker: str
    type: Optional[str] = None
    user_id: Optional[str] = None
    yes_price: Optional[int] = None
    trade_size: Optional[Decimal] = None

    model_config = ConfigDict(extra='allow')


class PolymarketOrder(BaseModel):
    errorMsg: Optional[str] = None
    orderID: Optional[str] = None
    takerAmount: Optional[str] = None
    makingAmount: Optional[str] = None
    status: str
    transactionsHashes: Optional[List[str]] = None
    success: bool = Field(default=False)
    trade_size: Optional[Decimal] = None
    token_id: Optional[str] = None

    model_config = ConfigDict(extra='ignore')


class TradeDetails(BaseModel):
    """
    Generic container for the details of a successful trade leg,
    used for unwinding.
    """
    platform: Platform
    trade_size: Decimal
    order_id: Optional[str] = None
    kalshi_ticker: Optional[str] = None
    kalshi_side: Optional[str] = None
    polymarket_token_id: Optional[str] = None

class Wallets(BaseModel):
    """
    Class to hold a user's exchange wallets.
    """
    kalshi_wallet : ExchangeWallet
    polymarket_wallet : ExchangeWallet

    class Config:
        arbitrary_types_allowed = True