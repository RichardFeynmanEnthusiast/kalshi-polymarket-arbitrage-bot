import logging
from typing import Dict, Optional, Union, List

from app.domain.events import OrderBookSnapshotReceived, OrderBookDeltaReceived, MarketBookUpdated
from app.domain.primitives import SIDES, Platform
from app.markets.order_book import Orderbook
from app.markets.state import MarketState, MarketOutcomes
from app.message_bus import MessageBus
from app.services.query_interface import IMarketStateQuerier


class MarketManager(IMarketStateQuerier):
    """
    Orchestrates state management by consuming and publishing events via the message bus.
    """

    def __init__(self, bus: MessageBus):
        """
        Initializes the MarketManager.
        """
        self.bus = bus
        self.market_states: Dict[str, MarketState] = {}
        self.logger = logging.getLogger(__name__)

        # The manager now subscribes its own handlers to the bus.
        self.bus.subscribe(OrderBookSnapshotReceived, self._handle_snapshot)
        self.bus.subscribe(OrderBookDeltaReceived, self._handle_delta)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset(self):
        """
        Clears the state of all managed markets, effectively resetting all order books.
        This is called by the orchestrator during a cool-down cycle.
        """
        for market_state in self.market_states.values():
            market_state.reset()
        self.logger.info("MarketManager state for all markets has been reset")

    def get_market_state(self, market_id: str) -> Optional[MarketState]:
        return self.market_states.get(market_id)

    def register_market(self, market_id: str) -> None:
        """
        Initializes a full MarketState domain model for a new market_id.
        """
        if market_id not in self.market_states:
            self.logger.info("Registering new market: %s", market_id)
            # Create the state model for this market
            market_state = MarketState(market_id=market_id)
            # Kalshi only has one normalized book
            market_state.platforms[Platform.KALSHI] = MarketOutcomes(yes=Orderbook(f"{market_id}-KALSHI-YES"))
            # Polymarket has two distinct books
            market_state.platforms[Platform.POLYMARKET] = MarketOutcomes(
                yes=Orderbook(f"{market_id}-POLY-YES"), no=Orderbook(f"{market_id}-POLY-NO")
            )
            self.market_states[market_id] = market_state
        else:
            self.logger.warning(f"Market '{market_id}' is already registered.")

    async def _handle_snapshot(self, event: OrderBookSnapshotReceived) -> None:
        """Handles a full book snapshot, clearing the book first."""
        market_state = self.market_states.get(event.market_id)
        if not market_state: return

        platform_outcomes = market_state.get_outcomes_for_platform(event.platform)
        if not platform_outcomes: return

        book = platform_outcomes.get_book(event.outcome)
        if not book: return

        old_tob = book.get_top_of_book()

        # Clear the book before applying snapshot
        book.clear()
        self.logger.debug(
            "Cleared %s %s book for %s",
            event.platform,
            event.outcome,
            event.market_id
        )

        updates = [(level.price, level.size) for level in event.bids]
        book.apply_updates(SIDES.BUY, updates)
        updates = [(level.price, level.size) for level in event.asks]
        book.apply_updates(SIDES.SELL, updates)

        if old_tob != book.get_top_of_book():
            self.logger.info(
                "Top-of-book changed for %s via snapshot on platform %s.",
                event.market_id,
                event.platform
            )
            await self._emit_book_update(event)

    async def _handle_delta(self, event: OrderBookDeltaReceived) -> None:
        """Handles an incremental update to a single price level."""
        market_state = self.market_states.get(event.market_id)
        if not market_state: return

        platform_outcomes = market_state.get_outcomes_for_platform(event.platform)
        if not platform_outcomes: return

        book = platform_outcomes.get_book(event.outcome)
        if not book: return

        old_tob = book.get_top_of_book()
        book.apply_update(event.side, event.price, event.size)

        if old_tob != book.get_top_of_book():
            self.logger.info(
                "Top-of-book changed for %s via snapshot on platform %s.",
                event.market_id,
                event.platform
            )
            await self._emit_book_update(event)

    async def _emit_book_update(self, source_event: Union[OrderBookSnapshotReceived, OrderBookDeltaReceived]) -> None:
        """Creates a MarketBookUpdated event and publishes it back to the bus."""
        update_event = MarketBookUpdated(
            market_id=source_event.market_id,
            platform=source_event.platform
        )
        await self.bus.publish(update_event)

    def get_all_market_states(self) -> List[MarketState]:
        """Returns a list of all current market state models."""
        return list(self.market_states.values())
