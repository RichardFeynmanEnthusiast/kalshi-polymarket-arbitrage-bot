import itertools
from datetime import datetime, timezone
from decimal import getcontext, Decimal
from typing import Dict, List, Any, ClassVar

from py_clob_client.clob_types import OrderBookSummary
from pydantic import BaseModel, Field
from sortedcontainers import SortedDict
from typing_extensions import Optional, Tuple

from app.domain.primitives import Money, SIDES

getcontext().prec = 18


class PriceLevel(BaseModel):
    """
    Representation of a single price level.
    """
    price: Money = Field(..., description="Price at this level")
    size: Money = Field(..., description="Quantity available for this level")

class Orderbook:
    """
    Maintains the complete, sorted order book for a single market.
    """

    def __init__(self, market_id) -> None:
        """
        Initializes a new, empty OrderBook for a given market.
        """
        self.market_id = market_id
        self.bids: SortedDict[Decimal] = SortedDict(lambda price: -price)
        self.asks: SortedDict[Decimal] = SortedDict()
        self.last_update: datetime = datetime.now(timezone.utc)

    def apply_update(self, side: str, price: Decimal, size: Decimal) -> None:
        """
        Applies a single, normalized update to a price level in the book.
        """
        book_side = self.bids if side == SIDES.BUY else self.asks
        if size.is_zero():
            book_side.pop(price, None)
        else:
            book_side[price] = size
        self.last_update = datetime.now(timezone.utc)

    def get_top_of_book(self) -> Tuple[Optional[Tuple[Decimal, Decimal]], Optional[Tuple[Decimal, Decimal]]]:
        """
        Returns the best bid and best ask as (price, size) tuples

        This method provides instant access to the most critical data for
        arbitrage detection.

        Returns:
            A tuple containing two elements:
            - The best bid as a (price, size) tuple, or None if no bids exist
            - The best ask as a (price, size) tuple, or None if no asks exist
        """
        best_bid = self.bids.peekitem(0) if self.bids else None
        best_ask = self.asks.peekitem(0) if self.asks else None
        return best_bid, best_ask

    def get_top_of_book_prices(self) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        A convenience method to get only the prices of the best bid and ask.

        Returns:
            A tuple containing:
            - The best bid price, or None.
            - The best ask price, or None.
        """
        best_bid, best_ask = self.get_top_of_book()
        bid_price = best_bid[0] if best_bid else None
        ask_price = best_ask[0] if best_ask else None
        return bid_price, ask_price

    def get_book_snapshot(self, depth: int = 5) -> Dict[str, list]:
        """
        Returns a snapshot of the order book up to a given depth.

        Args:
            depth: The number of price levels to return for each side.

        Returns:
            A dictionary with the top bids and asks.
        """
        bid_items = self.bids.items()
        top_bids = list(itertools.islice(bid_items, len(bid_items) - depth, len(bid_items)))
        top_asks = list(itertools.islice(self.asks.items(), depth))

        return {
            "bids": top_bids,
            "asks": top_asks
        }

    def clear(self) -> None:
        """
        Atomically clears all bids and asks from the order book.
        """
        self.bids.clear()
        self.asks.clear()
        self.last_update = datetime.now(timezone.utc)

class BinaryOrderBook(BaseModel):
    """
    Represents a binary 'yes/no' order book, with meta for trading.

    For Kalshi trades, only `ticker` is used to identify the market.
    For Polymarket trades, `condition_ids` maps 'yes'/'no' to their token IDs.
    """
    first_side_asks: List[PriceLevel] = Field(default_factory=list)
    second_side_asks: List[PriceLevel] = Field(default_factory=list)
    first_side_bids: List[PriceLevel] = Field(default_factory=list)
    second_side_bids: List[PriceLevel] = Field(default_factory=list)

    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the snapshot was obtained",
    )

    # Internal JSON format keys for different venues
    _kalshi_key: ClassVar[str] = "orderbook"
    _poly_key: ClassVar[str] = "orderbook"

    class Config:
        frozen = True
        json_encoders = {datetime: lambda v: v.isoformat(), Decimal: float}

    @property
    def best_yes_ask(self) -> Optional[PriceLevel]:
        return self.first_side_asks[0] if self.first_side_asks else None

    @property
    def best_no_ask(self) -> Optional[PriceLevel]:
        return self.second_side_asks[0] if self.second_side_asks else None

    @property
    def best_yes_bid(self) -> Optional[PriceLevel]:
        return self.first_side_bids[0] if self.first_side_bids else None

    @property
    def best_no_bid(self) -> Optional[PriceLevel]:
        return self.second_side_bids[0] if self.second_side_bids else None

    @property
    def age_ms(self) -> int:
        """Age of the snapshot right now (milliseconds)."""
        return int((datetime.now(timezone.utc) - self.fetched_at).total_seconds() * 1000)

    @classmethod
    def from_kalshi_http_orderbook(
            cls,
            raw: Dict[str, Any],
            fetched_at: datetime | None = None,
    ) -> Optional["BinaryOrderBook"]:
        """
        Convert Kalshi REST orderbook JSON into a BinaryOrderBook.

        Expected raw format:
            {
              "orderbook": {
                "no": [[price_cents, volume], ...],
                "yes": [[price_cents, volume], ...]
              }
            }
        Prices come in cents; we convert to dollars.  Kalshi does not expose separate token IDs,
        so `condition_ids` remains None.
        """
        orderbook = raw.get("orderbook")
        if not orderbook:
            return None
        yes_raw = orderbook.get("yes")
        no_raw = orderbook.get("no")
        if yes_raw is None or no_raw is None:
            return None

        # Bids for each side (highest-first)
        yes_bids = sorted(
            [PriceLevel(price=Decimal(p) / Decimal(100), size=Decimal(v)) for p, v in yes_raw],
            key=lambda lv: lv.price,
            reverse=True
        )
        no_bids = sorted(
            [PriceLevel(price=Decimal(p) / Decimal(100), size=Decimal(v)) for p, v in no_raw],
            key=lambda lv: lv.price,
            reverse=True
        )
        # Derive asks: price = 1 - opposite bid price
        yes_asks = sorted(
            [PriceLevel(price=Decimal(1) - lvl.price, size=lvl.size) for lvl in no_bids],
            key=lambda lv: lv.price
        )
        no_asks = sorted(
            [PriceLevel(price=Decimal(1) - lvl.price, size=lvl.size) for lvl in yes_bids],
            key=lambda lv: lv.price
        )

        return cls(
            first_side_bids=yes_bids,
            second_side_bids=no_bids,
            first_side_asks=yes_asks,
            second_side_asks=no_asks,
            fetched_at=fetched_at or datetime.now(timezone.utc),
        )

    @classmethod
    def from_polymarket_http_orderbook(
            cls,
            raw_data: List[Any],
            kalshi_yes_index : int,
            fetched_at: datetime | None = None,
    ) -> Optional["BinaryOrderBook"]:
        """
        Convert Polymarket GraphQL orderbook JSON into a BinaryOrderBook.

        Expected raw format:
            [OrderBookSummary(market='a', asset_id='outcome', bids=[..., ...], asks=[...,...]),
            OrderBookSummary(market='a', asset_id='outcome_complement' bids=[..., ...], asks=[...,...]]
        'kalshi_yes_index' defines which index in the polymarket orderbook array holds the equivalent yes orderbook in kalshi market
        `condition_ids` holds the token ID for each side.
        """
        first_side : OrderBookSummary = raw_data[kalshi_yes_index] # maps to the 'yes' orderbook in kalshi
        second_side : OrderBookSummary = raw_data[1-kalshi_yes_index]
        if first_side is None or second_side is None:
            return None

        first_side_bids = sorted(
            [PriceLevel(price=Decimal(order_summary.price), size=Decimal(order_summary.size)) for order_summary in first_side.bids],
            key=lambda lv: lv.price,
            reverse=True
        )
        second_side_bids = sorted(
            [PriceLevel(price=Decimal(order_summary.price), size=Decimal(order_summary.size)) for order_summary in second_side.bids],
            key=lambda lv: lv.price,
            reverse=True
        )
        first_side_asks = sorted(
            [PriceLevel(price=Decimal(order_summary.price), size=Decimal(order_summary.size)) for order_summary in first_side.asks],
            key=lambda lv: lv.price
        )
        second_side_asks = sorted(
            [PriceLevel(price=Decimal(order_summary.price), size=Decimal(order_summary.size)) for order_summary in second_side.asks],
            key=lambda lv: lv.price
        )

        return cls(
            first_side_bids=first_side_bids,
            second_side_bids=second_side_bids,
            first_side_asks=first_side_asks,
            second_side_asks=second_side_asks,
            fetched_at=fetched_at or datetime.now(timezone.utc),
        )
