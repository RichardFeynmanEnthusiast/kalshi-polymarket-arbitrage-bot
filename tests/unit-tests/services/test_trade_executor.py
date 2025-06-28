import unittest
from unittest.mock import MagicMock, AsyncMock

from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform
from app.domain.events import StoreTradeResults, ExecuteTrade, TradeAttemptCompleted
from app.gateways.trade_gateway import TradeGateway
from app.services.execution import executor
from decimal import Decimal

from tests.sample_data import DUMMY_VALID_KALSHI_ORDER_RESPONSE


class TestExecutor(unittest.IsolatedAsyncioTestCase):


    def __init__(self, methodName: str = "runTest"):
        super().__init__(methodName)
        self.trade_gateway = None

    async def asyncSetUp(self):
        self.mock_bus = MagicMock()
        self.mock_bus.publish = AsyncMock()

        # Required to prevent crash on uninitialized global _bus in module
        executor.initialize_trade_executor(
            trade_repo=None,  # Not needed for this test
            bus=self.mock_bus,
            dry_run=False,
            max_trade_size=100
        )

        # Shared test data
        self.dummy_opportunity = ArbitrageOpportunity(
            market_id="test-market",
            buy_yes_platform=Platform.KALSHI,
            buy_yes_price=Decimal("0.27"),
            buy_no_platform=Platform.POLYMARKET,
            buy_no_price=Decimal("0.25"),
            profit_margin=Decimal("0.50"),
            potential_trade_size=Decimal("100.000"),
            kalshi_ticker="KXFEDCHAIRNOM-29-KW",
            polymarket_yes_token_id="yes-token",
            polymarket_no_token_id="no-token"
        )

        dummy_raw_kalshi_order_response = DUMMY_VALID_KALSHI_ORDER_RESPONSE
        self.trade_gateway = TradeGateway(polymarket_http=None, kalshi_http=None)
        self.dummy_valid_kalshi_response = self.trade_gateway.process_raw_kalshi_order(dummy_raw_kalshi_order_response,
                                                                                       trade_size=Decimal("3.00"))
        self.dummy_poly_order_response = {'errorMsg': '', 'orderID': '0x2edf84dfc54d8d60e1c4549f01cf2e8ea73f6d284c75ebe648c9e2c4ba7c8d51', 'takingAmount': '2.140844', 'makingAmount': '1.519999', 'status': 'matched', 'transactionsHashes': ['0x6a701d6af2f1a524a78b61bf96313e5efad066ba7016f151f9bbfc395400a9ab'], 'success': True}

    async def asyncTearDown(self):
        self.mock_bus.stop()

    async def test_handle_trade_response_publishes_required_messages(self):
        """
        Verify that handle_trade_response publishes both StoreTradeResults
        and the essential TradeAttemptCompleted to unlock the monitor.
        """
        await executor.handle_trade_response(
            kalshi_result=self.dummy_valid_kalshi_response,
            polymarket_result=self.dummy_poly_order_response,
            category="buy both",
            opportunity=self.dummy_opportunity
        )

        # Assert that publish was called twice
        self.assertEqual(self.mock_bus.publish.call_count, 2)

        # Check that both expected message types were published
        published_messages = [call.args[0] for call in self.mock_bus.publish.call_args_list]
        message_types = [type(msg) for msg in published_messages]
        self.assertIn(StoreTradeResults, message_types)
        self.assertIn(TradeAttemptCompleted, message_types)

        # Optional: More detailed check on the StoreTradeResults command
        store_trade_command = next(
            (msg for msg in published_messages if isinstance(msg, StoreTradeResults)),
            None
        )
        self.assertIsNotNone(store_trade_command)
        self.assertEqual(store_trade_command.arb_trade_results.opportunity, self.dummy_opportunity)

    async def test_handle_execute_trade_unlocks_on_zero_size(self):
        """
        Verify that if a trade is not executed due to zero size,
        it still publishes TradeAttemptCompleted to unlock the monitor.
        """
        # Arrange: An opportunity with zero potential size
        zero_size_opportunity = self.dummy_opportunity.model_copy(
            update={"potential_trade_size": Decimal("0")}
        )
        command = ExecuteTrade(opportunity=zero_size_opportunity)

        # Act
        await executor.handle_execute_trade(command)

        # Assert: The bus was called once to unlock the monitor
        self.mock_bus.publish.assert_called_once()
        published_event = self.mock_bus.publish.call_args[0][0]
        self.assertIsInstance(published_event, TradeAttemptCompleted)


if __name__ == '__main__':
    unittest.main()