import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, List, Optional, Dict, Any

from pydantic import BaseModel, Field

from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform, SIDES
from app.domain.types import KalshiOrder, PolymarketOrder, TradeDetails, Wallets


# --- Base Message Types ---

class BaseMessage(BaseModel):
    """The base model for all events and commands."""
    message_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseEvent(BaseMessage):
    """The base model for all domain events."""
    pass


class BaseCommand(BaseMessage):
    """The base model for all commands."""
    pass


# --- Event and Command Definitions ---

class PriceLevelData(BaseModel):
    """
    A data transfer object representing a single price level for events.
    """
    price: Decimal
    size: Decimal


class OrderBookSnapshotReceived(BaseEvent):
    """
    Event produced when a full order book snapshot is received.
    This event signifies that the existing book for this market and outcome
    should be completely cleared and replaced with this new data.
    """
    platform: Platform
    market_id: str
    outcome: Literal['YES', 'NO']
    bids: List[PriceLevelData]
    asks: List[PriceLevelData]


class OrderBookDeltaReceived(BaseEvent):
    """
    Event produced when a single price level's size changes.
    The `size` attribute represents the new, final size at that level.
    """
    platform: Platform
    market_id: str
    outcome: Literal['YES', 'NO']
    side: Literal[SIDES.BUY, SIDES.SELL]
    price: Decimal
    size: Decimal


class MarketBookUpdated(BaseEvent):
    """
    Event produced when a market's top-of-book has changed, signaling
    that it should be re-evaluated for arbitrage opportunities.
    """
    market_id: str
    platform: Platform


class ArbitrageOpportunityFound(BaseEvent):
    """Event for when a strategy finds an opportunity."""
    opportunity: ArbitrageOpportunity


class ArbTradeResultReceived(BaseEvent):
    """Event for when the execution service receives trade responses for a single arbitrage opportunity"""
    category: str
    opportunity: ArbitrageOpportunity
    polymarket_order: Optional[PolymarketOrder] = None
    polymarket_error: Optional[str] = None
    kalshi_order: Optional[KalshiOrder] = None
    kalshi_error_message: Optional[str] = None


class ExecuteTrade(BaseCommand):
    """Command to instruct the execution service to place a trade."""
    opportunity: ArbitrageOpportunity
    wallets: Wallets


class StoreTradeResults(BaseCommand):
    """Command to instruct the trade storage service to flush the trade results to the database"""
    arb_trade_results: ArbTradeResultReceived


class TradeFailed(BaseEvent):
    """
    Event published when on leg of an arbitrage trade fails,
    triggering an unwind
    """
    failed_leg_platform: Platform
    successful_leg: TradeDetails
    opportunity: ArbitrageOpportunity
    error_message: str


class TradeAttemptCompleted(BaseEvent):
    """
    Event published after a trade attempt (success, partial failure, or full failure)
    has been fully processed by the executor. This signals that the system is ready to evaluate
    new arbitrage opportunities
    """
    pass


class ArbitrageTradeSuccessful(BaseEvent):
    """
    Event published when both legs of an arbitrage trade succeed.
    """
    pass
