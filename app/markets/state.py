from decimal import Decimal
from typing import Optional, Dict

from pydantic import BaseModel, Field

from app.domain.events import OrderBookDeltaReceived
from app.domain.primitives import SIDES, Platform
from app.markets.order_book import Orderbook


class MarketOutcomes(BaseModel):
    """
    An explicit container for the YES and NO order books.
    """
    yes: Optional[Orderbook] = None
    no: Optional[Orderbook] = None

    class Config:
        arbitrary_types_allowed = True

    def get_book(self, outcome: str) -> Optional[Orderbook]:
        """
        Safely retrieves the order book for a given outcome string.
        """
        if outcome.upper() == 'YES':
            return self.yes
        elif outcome.upper() == 'NO':
            return self.no
        return None

    def reset(self):
        """Resets the order books for both YES and NO outcomes"""
        if self.yes:
            self.yes.clear()
        if self.no:
            self.no.clear()

    def apply_update_from_delta(self, update: OrderBookDeltaReceived) -> bool:
        """
        Applies a normalized update to the correct book (yes or no) and
        returns True if the top-of-book was changed.
        """
        book_to_update = self.get_book(update.outcome)
        if not book_to_update:
            return False

        old_tob = book_to_update.get_top_of_book()
        book_to_update.apply_update(update.side, update.price, update.size)
        new_tob = book_to_update.get_top_of_book()

        return old_tob != new_tob


class MarketState(BaseModel):
    """
    The root domain model for the live state of a single market across all platforms.
    """
    market_id: str
    platforms: Dict[Platform, MarketOutcomes] = Field(default_factory=dict)

    def get_outcomes_for_platform(self, platform: Platform) -> Optional[MarketOutcomes]:
        """
        Safely retrieves the MarketOutcomes object for a given platform.
        """
        return self.platforms.get(platform)

    def apply_update(self, update: OrderBookDeltaReceived) -> bool:
        """
        Applies a normalized update to the correct platform's outcomes,
        returning True if the top-of-book changed.
        """
        platform_outcomes = self.get_outcomes_for_platform(update.platform)
        if not platform_outcomes:
            return False

        return platform_outcomes.apply_update_from_delta(update)

    def get_price(self, platform: Platform, outcome: str, side: str) -> Optional[Decimal]:
        """
        Convenience method to get a specific price from the nested state.
        """
        platform_outcomes = self.get_outcomes_for_platform(platform)
        if not platform_outcomes:
            return None

        book = platform_outcomes.get_book(outcome)
        if not book:
            return None

        best_bid, best_ask = book.get_top_of_book()

        price_level = None
        if side == SIDES.BUY:
            price_level = best_bid
        elif side == SIDES.SELL:
            price_level = best_ask

        # The price is the first element of the (price, size) tuple
        return price_level[0] if price_level else None

    def get_kalshi_derived_no_ask_price(self) -> Optional[Decimal]:
        """
        Calculates the Kalshi 'NO' ask price based on the 'YES' bid.
        """
        yes_bid_price = self.get_price(Platform.KALSHI, 'YES', SIDES.BUY)
        if yes_bid_price is None:
            return None
        return Decimal('1.0') - yes_bid_price

    def reset(self):
        """Resets the outcomes for all platforms"""
        for platform_outcomes in self.platforms.values():
            platform_outcomes.reset()
