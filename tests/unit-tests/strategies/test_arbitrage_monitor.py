import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

from app.domain.events import MarketBookUpdated, ArbitrageOpportunityFound, ExecuteTrade, TradeAttemptCompleted
from app.domain.primitives import Platform, SIDES
from app.markets.order_book import Orderbook
from app.markets.state import MarketState, MarketOutcomes
from app.strategies import arbitrage_monitor


class TestArbitrageMonitor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """
        Set up mocks and initialize the arbitrage_monitor module before each test.
        """
        self.market_manager = MagicMock()
        self.bus = MagicMock()
        self.bus.publish = AsyncMock()

        self.market_id = 'test_market_id'
        self.markets_config = [{
            'id': self.market_id,
            'kalshi_ticker': 'KALSHI-TICKER-24',
            'polymarket_yes_token_id': '0x123',
            'polymarket_no_token_id': '0x456',
        }]

        # Initialize the module with our mocks
        arbitrage_monitor.initialize_arbitrage_handlers(
            market_manager=self.market_manager,
            bus=self.bus,
            markets_config=self.markets_config,
        )
        # Ensure the lock state is reset after each test for isolation
        self.addAsyncCleanup(self._reset_monitor_state)

    def _reset_monitor_state(self):
        """Resets the internal state of the monitor for test isolation."""
        arbitrage_monitor._is_trade_in_progress = False

    def _create_market_state(
            self,
            kalshi_yes_ask_price: Decimal = None,
            kalshi_yes_ask_size: Decimal = Decimal('0'),
            kalshi_yes_bid_price: Decimal = None,
            kalshi_yes_bid_size: Decimal = Decimal('0'),
            poly_yes_ask_price: Decimal = None,
            poly_yes_ask_size: Decimal = Decimal('0'),
            poly_no_ask_price: Decimal = None,
            poly_no_ask_size: Decimal = Decimal('0'),
            kalshi_timestamp: datetime = None,
            poly_timestamp: datetime = None,
    ) -> MarketState:
        """
        Helper function to build a complete MarketState object for tests
        """
        now = datetime.now(timezone.utc)
        kalshi_ts = kalshi_timestamp or now
        poly_ts = poly_timestamp or now

        # Create Kalshi Orderbook and Outcomes
        kalshi_yes_book = Orderbook("KALSHI_YES")
        if kalshi_yes_ask_price is not None:
            kalshi_yes_book.apply_update(SIDES.SELL, kalshi_yes_ask_price, kalshi_yes_ask_size)
        if kalshi_yes_bid_price is not None:
            kalshi_yes_book.apply_update(SIDES.BUY, kalshi_yes_bid_price, kalshi_yes_bid_size)
        kalshi_yes_book.last_update = kalshi_ts
        kalshi_outcomes = MarketOutcomes(yes=kalshi_yes_book)

        # Create Polymarket `Orderbooks` and `Outcomes`
        poly_yes_book = Orderbook("POLY_YES")
        if poly_yes_ask_price is not None:
            poly_yes_book.apply_update(SIDES.SELL, poly_yes_ask_price, poly_yes_ask_size)
        poly_yes_book.last_update = poly_ts
        poly_no_book = Orderbook("POLY_NO")
        if poly_no_ask_price is not None:
            poly_no_book.apply_update(SIDES.SELL, poly_no_ask_price, poly_no_ask_size)
        poly_no_book.last_update = poly_ts
        poly_outcomes = MarketOutcomes(yes=poly_yes_book, no=poly_no_book)

        # Create and return the full MarketState
        market_state = MarketState(market_id=self.market_id)
        market_state.platforms[Platform.KALSHI] = kalshi_outcomes
        market_state.platforms[Platform.POLYMARKET] = poly_outcomes

        self.market_manager.get_market_state.return_value = market_state
        return market_state

    # --------------------------------------------------------------------------
    # Fee Calculation Tests
    # --------------------------------------------------------------------------
    def test_kalshi_fee_calculation(self):
        """Test the _kalshi_fee static method with a standard case."""
        fee_1 = arbitrage_monitor._kalshi_fee(Decimal('10'), Decimal('0.25'))
        self.assertEqual(fee_1, Decimal('0.14'))
        fee_2 = arbitrage_monitor._kalshi_fee(Decimal('10'), Decimal('0.5'))
        self.assertEqual(fee_2, Decimal('0.18'))

        fee_3 = arbitrage_monitor._kalshi_fee(Decimal('1'), Decimal('0.99'))
        self.assertEqual(fee_3, Decimal('0.01'))

        fee_4 = arbitrage_monitor._kalshi_fee(Decimal('100'), Decimal('0.01'))
        self.assertEqual(fee_4, Decimal('0.07'))

        fee_5 = arbitrage_monitor._kalshi_fee(Decimal('50'), Decimal('0.20'))
        self.assertEqual(fee_5, Decimal('0.56'))

    def test_kalshi_fee_at_boundaries(self):
        """Test that fees are zero when the price is 0 or 1."""
        self.assertEqual(arbitrage_monitor._kalshi_fee(Decimal('10'), Decimal('0')), Decimal('0.00'))
        self.assertEqual(arbitrage_monitor._kalshi_fee(Decimal('10'), Decimal('1')), Decimal('0.00'))

    # --------------------------------------------------------------------------
    # Handler and Strategy Logic Tests
    # --------------------------------------------------------------------------

    # --- Test Cases for Event Handlers and Full Flow ---

    async def test_full_flow_market_update_to_execute_trade(self):
        """
        Verify the full chain: MarketBookUpdated -> ArbitrageOpportunityFound -> ExecuteTrade.
        """
        # Set up a profitable state
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.40"), poly_no_ask_size=Decimal("10")
        )

        # Trigger the first handler
        update_event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(update_event)

        # Verify an ArbitrageOpportunityFound event was published
        self.bus.publish.assert_called_once()
        found_event = self.bus.publish.call_args[0][0]
        self.assertIsInstance(found_event, ArbitrageOpportunityFound)
        self.bus.publish.reset_mock()  # Reset for the next assertion

        # Trigger the second handler with the event from the step above
        await arbitrage_monitor.handle_arbitrage_opportunity_found(found_event)

        # Verify an ExecuteTrade command was published
        self.bus.publish.assert_called_once()
        execute_command = self.bus.publish.call_args[0][0]
        self.assertIsInstance(execute_command, ExecuteTrade)
        self.assertEqual(execute_command.opportunity, found_event.opportunity)

    # --- Test Cases for Locking Mechanism ---

    async def test_monitor_locks_after_finding_opportunity(self):
        """The monitor's internal flag should be set to True after finding an opportunity."""
        # Arrange: A profitable market
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.40"), poly_no_ask_size=Decimal("10")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)

        # Act
        await arbitrage_monitor.handle_market_book_update(event)

        # Assert: Bus was called and the monitor is now locked
        self.bus.publish.assert_called_once()
        self.assertTrue(arbitrage_monitor._is_trade_in_progress)

    async def test_monitor_skips_when_locked(self):
        """If the monitor is locked, it should not process new market updates."""
        # Arrange: A profitable market and a locked monitor
        arbitrage_monitor._is_trade_in_progress = True
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.40"), poly_no_ask_size=Decimal("10")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)

        # Act
        await arbitrage_monitor.handle_market_book_update(event)

        # Assert: The bus was never called because the monitor was locked
        self.bus.publish.assert_not_called()

    async def test_monitor_unlocks_on_trade_completed_event(self):
        """The monitor should unlock when it handles a TradeAttemptCompleted event."""
        # Arrange: A locked monitor
        arbitrage_monitor._is_trade_in_progress = True
        event = TradeAttemptCompleted()

        # Act
        await arbitrage_monitor.handle_trade_attempt_completed(event)

        # Assert: The monitor is now unlocked
        self.assertFalse(arbitrage_monitor._is_trade_in_progress)

    # --- Test Cases for Strategy Logic: Opportunity Found ---

    async def test_opportunity_buy_kalshi_yes_poly_no_is_found(self):
        """
        A clear opportunity to buy YES on Kalshi and NO on Polymarket should be found and published.
        Cost = 0.40 + 0.35 = 0.75.
        """
        # Arrange
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("20"),
            poly_no_ask_price=Decimal("0.35"), poly_no_ask_size=Decimal("15")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)

        # Act
        await arbitrage_monitor.handle_market_book_update(event)

        # Assert
        self.bus.publish.assert_called_once()
        published_event = self.bus.publish.call_args[0][0]
        self.assertIsInstance(published_event, ArbitrageOpportunityFound)
        opportunity = published_event.opportunity
        self.assertEqual(opportunity.buy_yes_platform, Platform.KALSHI)
        self.assertEqual(opportunity.buy_no_platform, Platform.POLYMARKET)
        self.assertEqual(opportunity.potential_trade_size, Decimal('15'))

    async def test_opportunity_buy_poly_yes_kalshi_no_is_found(self):
        """
        A clear opportunity to buy YES on Polymarket and NO on Kalshi should be found.
        Kalshi NO price is derived from its YES bid (1 - YES bid).
        Kalshi NO ask = 1 - 0.60 = 0.40. Cost = 0.35 + 0.40 = 0.75.
        """
        # Arrange
        self._create_market_state(
            kalshi_yes_bid_price=Decimal("0.60"), kalshi_yes_bid_size=Decimal("25"),
            poly_yes_ask_price=Decimal("0.35"), poly_yes_ask_size=Decimal("30")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.POLYMARKET)

        # Act
        await arbitrage_monitor.handle_market_book_update(event)

        # Assert
        self.bus.publish.assert_called_once()
        published_event = self.bus.publish.call_args[0][0]
        self.assertIsInstance(published_event, ArbitrageOpportunityFound)
        opportunity = published_event.opportunity
        self.assertEqual(opportunity.buy_yes_platform, Platform.POLYMARKET)
        self.assertEqual(opportunity.buy_no_platform, Platform.KALSHI)
        self.assertEqual(opportunity.potential_trade_size, Decimal('25'))

    # --- Test Cases for Strategy Logic: No Opportunity Found ---

    async def test_no_opportunity_due_to_unprofitable_prices(self):
        """
        If cost is > 1.0, no event should be published.
        """
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.55"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.50"), poly_no_ask_size=Decimal("10")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()

    async def test_no_opportunity_due_to_profitability_buffer(self):
        """
        A marginal opportunity (cost = 0.99) should be rejected by the buffer.
        """
        # NOTE: PROFITABILITY_BUFFER is 0.01. Cost must be < (1.0 - 0.01) = 0.99
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.50"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.49"), poly_no_ask_size=Decimal("10")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()

    async def test_no_opportunity_due_to_kalshi_fees(self):
        """
        An opportunity that is profitable before fees but not after should be rejected.
        Cost = 0.45 + 0.53 = 0.98. Profit = 0.02.
        Fee on 10 contracts @ 0.45 is ~0.017, for a total cost of 0.997.
        This is not less than (1.0 - 0.01), so it should be rejected.
        """
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.45"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.53"), poly_no_ask_size=Decimal("10")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()

    # --- Test Cases for Edge Cases and Data Integrity ---

    async def test_no_opportunity_due_to_zero_liquidity(self):
        """If prices are good but size is zero on one side, no event is published."""
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.40"), poly_no_ask_size=Decimal("0")  # Zero size
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.POLYMARKET)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()

    async def test_no_opportunity_due_to_stale_data(self):
        """
        If the data from one platform is too old compared to the other, reject the opportunity.
        """
        now = datetime.now(timezone.utc)
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=Decimal("0.40"), poly_no_ask_size=Decimal("10"),
            kalshi_timestamp=now,
            poly_timestamp=now - timedelta(seconds=10)  # Stale data
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()

    async def test_graceful_handling_of_missing_prices(self):
        """If a required price is missing (None), no error should occur."""
        self._create_market_state(
            kalshi_yes_ask_price=Decimal("0.40"), kalshi_yes_ask_size=Decimal("10"),
            poly_no_ask_price=None,  # Missing price
            poly_no_ask_size=Decimal("10")
        )
        event = MarketBookUpdated(market_id=self.market_id, platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()

    async def test_graceful_handling_of_unconfigured_market(self):
        """If an event for an unknown market ID arrives, it should be ignored."""
        event = MarketBookUpdated(market_id="unknown_market", platform=Platform.KALSHI)
        await arbitrage_monitor.handle_market_book_update(event)

        self.bus.publish.assert_not_called()


if __name__ == '__main__':
    unittest.main()
