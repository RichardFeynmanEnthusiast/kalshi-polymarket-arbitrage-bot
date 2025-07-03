import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, Mock

from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform
from app.domain.events import StoreTradeResults, ExecuteTrade, TradeAttemptCompleted, ArbitrageTradeSuccessful
from app.gateways.trade_gateway import TradeGateway
from app.services.execution import executor
from decimal import Decimal
from shared_wallets.domain.types import Currency, Money
from shared_wallets.domain.models import Exchange, ExchangeWallet
from app.domain.types import Wallets

from app.services.operational.balance_service import BalanceService
from tests.sample_data import DUMMY_VALID_KALSHI_ORDER_RESPONSE, DUMMY_VALID_POLYMARKET_ORDER_RESPONSE, VALID_WALLETS_LARGER_KALSHI

def make_wallet(balances, exchange):
    return ExchangeWallet(exchange=exchange, balances=balances)

class TestExecutor(unittest.IsolatedAsyncioTestCase):

    def __init__(self, methodName: str = "runTest"):
        super().__init__(methodName)
        self.trade_gateway = None

    async def asyncSetUp(self):
        self.mock_bus = MagicMock()
        self.mock_gateway = Mock()
        self.mock_bus.publish = AsyncMock()

        # Mock the shutdown event
        self.mock_shutdown_event = MagicMock(spec=asyncio.Event)
        self.mock_shutdown_event.set = MagicMock()

        # Required to prevent crash on uninitialized global _bus in module
        executor.initialize_trade_executor(
            trade_repo=None,  # Not needed for this test
            bus=self.mock_bus,
            shutdown_event=self.mock_shutdown_event,
            dry_run=False,
            balance_service=MagicMock(),
        )

        # Shared test data
        self.dummy_opportunity = ArbitrageOpportunity(
            market_id="test-market",
            buy_yes_platform=Platform.KALSHI,
            buy_yes_price=Decimal("0.27"),
            buy_no_platform=Platform.POLYMARKET,
            buy_no_price=Decimal("0.25"),
            profit_margin=Decimal("0.50"),
            potential_trade_size=Decimal("10.00"),
            kalshi_ticker="KXFEDCHAIRNOM-29-KW",
            polymarket_yes_token_id="yes-token",
            polymarket_no_token_id="no-token",
            kalshi_fees=Decimal("0.00"),
        )

        self.trade_gateway = TradeGateway(polymarket_http=None, kalshi_http=None)
        self.dummy_valid_kalshi_response = self.trade_gateway.process_raw_kalshi_order(
            DUMMY_VALID_KALSHI_ORDER_RESPONSE,
            trade_size=Decimal("3.00")
        )
        self.dummy_valid_poly_response = self.trade_gateway.process_raw_polymarket_order(
            DUMMY_VALID_POLYMARKET_ORDER_RESPONSE,
            token_id_to_add=self.dummy_opportunity.polymarket_yes_token_id
        )

    async def test_handle_trade_response_on_success(self):
        """
        Verify that on success, it publishes StoreTradeResults, ArbitrageTradeSuccessful,
        and TradeAttemptCompleted.
        """

        await executor.handle_trade_response(
            kalshi_result=self.dummy_valid_kalshi_response,
            polymarket_result=self.dummy_valid_poly_response,
            trade_type="buy both",
            opportunity=self.dummy_opportunity
        )

        self.assertEqual(self.mock_bus.publish.call_count, 3)

        message_types = [type(call.args[0]) for call in self.mock_bus.publish.call_args_list]
        self.assertIn(StoreTradeResults, message_types)
        self.assertIn(ArbitrageTradeSuccessful, message_types)
        self.assertIn(TradeAttemptCompleted, message_types)
        self.mock_shutdown_event.set.assert_not_called()

    async def test_handle_trade_response_triggers_shutdown_on_total_failure(self):
        """
        Verify that if both trade legs fail, the shutdown event is triggered.
        """
        # Arrange: Define two exception objects for the failed legs
        kalshi_error = Exception("Kalshi exchange is down")
        polymarket_error = Exception("Polymarket request timed out")

        # Act
        await executor.handle_trade_response(
            kalshi_result=kalshi_error,
            polymarket_result=polymarket_error,
            trade_type="buy both",
            opportunity=self.dummy_opportunity
        )

        # Assert: Shutdown event was triggered
        self.mock_shutdown_event.set.assert_called_once()

        # Assert: Only StoreTradeResults was published before shutdown was triggered
        self.mock_bus.publish.assert_called_once()
        published_event = self.mock_bus.publish.call_args[0][0]
        self.assertIsInstance(published_event, StoreTradeResults)

    async def test_handle_execute_trade_unlocks_on_zero_size(self):
        """
        Verify that if a trade is not executed due to zero size,
        it still publishes TradeAttemptCompleted to unlock the monitor.
        """
        # Arrange: An opportunity with zero potential size
        zero_size_opportunity = self.dummy_opportunity.model_copy(
            update={"potential_trade_size": Decimal("0")}
        )
        # Mock with valid values
        balance_service = BalanceService(balance_data_gateway=self.mock_gateway,
                                         minimum_balance=Decimal(1.00))
        balance_service.set_wallets(VALID_WALLETS_LARGER_KALSHI)
        executor.initialize_trade_executor(
            trade_repo=None,
            bus=self.mock_bus,
            shutdown_event=self.mock_shutdown_event,
            dry_run=False,
            balance_service=balance_service,
        )

        command = ExecuteTrade(opportunity=zero_size_opportunity)

        # Act
        await executor.handle_execute_trade(command)

        # Assert: The bus was called once to unlock the monitor
        self.mock_bus.publish.assert_called_once()
        published_event = self.mock_bus.publish.call_args[0][0]
        self.assertIsInstance(published_event, TradeAttemptCompleted)

    async def test_handle_trade_response_leads_to_shut_down_when_balance_limit_reached(self):
        """
        Verify that when the balance is reached, the shutdown event is triggered from the happy path.
        """
        # Arrange
        test_poly_wallet : ExchangeWallet = make_wallet({Currency.USDC_E : Money(Decimal("50.00"), Currency.USDC_E)}, exchange=Exchange.POLYMARKET)
        test_kalshi_wallet : ExchangeWallet = make_wallet({Currency.USD :Money(Decimal("50.00"), Currency.USDC)}, exchange=Exchange.KALSHI)
        min_balance = test_poly_wallet.get_balance(Currency.USDC_E).amount # same balance will shut down the service
        balance_service = BalanceService(balance_data_gateway=self.mock_gateway,
                                              minimum_balance=min_balance)
        opportunity = self.dummy_opportunity.model_copy()
        opportunity.potential_trade_size = min_balance
        balance_service.generate_new_wallets = Mock(return_value=Wallets(kalshi_wallet=test_kalshi_wallet,
                                                                              polymarket_wallet=test_poly_wallet))
        executor.initialize_trade_executor(
            trade_repo=None,
            bus=self.mock_bus,
            shutdown_event=self.mock_shutdown_event,
            dry_run=False,
            balance_service=balance_service,  # use your real one with mocked method
        )

        # Act
        await executor.handle_trade_response(
            kalshi_result=self.dummy_valid_kalshi_response,
            polymarket_result=self.dummy_valid_poly_response,
            trade_type="buy both",
            opportunity=self.dummy_opportunity
        )

        # Assert
        self.assertEqual(self.mock_bus.publish.call_count, 3)
        self.mock_shutdown_event.set.assert_called_once()

    async def test_handle_trade_response_does_not_lead_to_shut_down_when_balance_limit_not_reached(self):
        """
        Verify that when there is sufficient balance, a shutdown event is not triggered.
        """
        # Arrange
        test_poly_wallet: ExchangeWallet = make_wallet({Currency.USDC_E: Money(Decimal("50.00"), Currency.USDC_E)},
                                                       exchange=Exchange.POLYMARKET)
        test_kalshi_wallet: ExchangeWallet = make_wallet({Currency.USD: Money(Decimal("50.00"), Currency.USDC)},
                                                         exchange=Exchange.KALSHI)
        min_balance = test_poly_wallet.get_balance(Currency.USDC_E).amount - Decimal("1.00")
        balance_service = BalanceService(balance_data_gateway=self.mock_gateway,
                                              minimum_balance=min_balance)
        opportunity = self.dummy_opportunity.model_copy()
        opportunity.potential_trade_size = min_balance
        balance_service.generate_new_wallets = Mock(return_value=Wallets(kalshi_wallet=test_kalshi_wallet,
                                                                              polymarket_wallet=test_poly_wallet))
        executor.initialize_trade_executor(
            trade_repo=None,
            bus=self.mock_bus,
            shutdown_event=self.mock_shutdown_event,
            dry_run=False,
            balance_service=balance_service,  # use your real one with mocked method
        )

        # Act
        await executor.handle_trade_response(
            kalshi_result=self.dummy_valid_kalshi_response,
            polymarket_result=self.dummy_valid_poly_response,
            trade_type="buy both",
            opportunity=self.dummy_opportunity
        )

        # Assert
        self.assertEqual(self.mock_bus.publish.call_count, 3)
        self.mock_shutdown_event.set.assert_not_called()


if __name__ == '__main__':
    unittest.main()
