import itertools
from datetime import datetime, timezone
from decimal import getcontext, Decimal
from typing import Dict, List

from sortedcontainers import SortedDict
from typing_extensions import Optional, Tuple

from app.domain.events import PriceLevelData
from app.domain.primitives import SIDES

getcontext().prec = 10


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

    def clear(self):
        """
        Clears all bids and asks from the order book.
        """
        self.bids.clear()
        self.asks.clear()
        self.last_update = datetime.now(timezone.utc)

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

    def apply_updates(self, side: str, updates: List[PriceLevelData]) -> None:
        """
        Applies multiple normalized updates (price, size) to the book side.
        """
        book_side = self.bids if side == SIDES.BUY else self.asks

        for price, size in updates:
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
