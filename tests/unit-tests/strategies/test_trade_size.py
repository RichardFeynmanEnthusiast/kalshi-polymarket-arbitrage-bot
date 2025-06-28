import unittest
from typing import Dict
from unittest.mock import Mock
from decimal import Decimal

from app.domain.types import Wallets
from app.strategies.trade_size import get_trade_size, calculate_minimum_wallet_budget, calculate_trade__size
from shared_wallets.domain.types import Currency, Money
from shared_wallets.domain.models import ExchangeWallet, Exchange


class TestTradeSizeCalculations(unittest.TestCase):

    def setUp(self):
        """
        Set up the test environment by initializing wallet balances for Kalshi and Polymarket exchanges.
        Creates ExchangeWallet instances for each exchange and aggregates them into a Wallets instance.
        """
        # setup
        kalshi_balance : Dict[Currency, Money] = {
            Currency.USD: Money(Decimal("100.00"), Currency.USD),
        }
        polymarket_balance : Dict[Currency, Money] = {
            Currency.USDC_E: Money(Decimal("50.00"), Currency.USDC_E),
            Currency.POL: Money(Decimal("85.00"), Currency.POL),
        }
        self.polymarket_wallet = ExchangeWallet(exchange=Exchange.POLYMARKET, balances=polymarket_balance)
        self.kalshi_wallet = ExchangeWallet(exchange=Exchange.KALSHI, balances=kalshi_balance)

        self.wallets = Wallets(
            kalshi_wallet=self.kalshi_wallet,
            polymarket_wallet=self.polymarket_wallet,
        )

    def test_calculate_trade__size_rounds_down(self):
        """
        Test that the calculate_trade__size function correctly rounds down the trade size.
        Verifies the function's behavior with various decimal inputs.
        """
        # ASSERT
        self.assertEqual(calculate_trade__size(Decimal('9.9')), 3)
        self.assertEqual(calculate_trade__size(Decimal('16')), 4)
        self.assertEqual(calculate_trade__size(Decimal('0')), 0)
        self.assertEqual(calculate_trade__size(Decimal('1.0')), 1)
        self.assertEqual(calculate_trade__size(Decimal('100.00')), 10)
        self.assertEqual(calculate_trade__size(Decimal('10000.92')), 100)

    def test_calculate_minimum_wallet_budget_returns_minimum(self):
        """
        Test that calculate_minimum_wallet_budget returns the minimum balance from the wallets.
        Verifies the function's ability to correctly identify the smallest wallet balance.
        """
        # ASSERT
        self.assertEqual(calculate_minimum_wallet_budget(self.wallets), 50)

    def test_calculate_minimum_wallet_budget_handles_missing_kalshi_currency(self):
        """
        Test that calculate_minimum_wallet_budget handles cases where the Kalshi wallet has no balances.
        Verifies that the function returns 0 when the Kalshi wallet is empty.
        """
        # SETUP
        empty_kalshi_wallet = ExchangeWallet(exchange=Exchange.KALSHI, balances={})
        invalid_wallets = Wallets(
            kalshi_wallet=empty_kalshi_wallet,
            polymarket_wallet=self.polymarket_wallet,
        )
        # ASSERT
        self.assertEqual(calculate_minimum_wallet_budget(invalid_wallets), 0)

    def test_calculate_minimum_wallet_budget_handles_missing_polymarket_currency(self):
        """
        Test that calculate_minimum_wallet_budget handles cases where the Polymarket wallet has no balances.
        Verifies that the function returns 0 when the Polymarket wallet is empty.
        """
        # SETUP
        empty_poly_wallet = ExchangeWallet(exchange=Exchange.POLYMARKET, balances={})
        invalid_wallets = Wallets(
            kalshi_wallet=self.kalshi_wallet,
            polymarket_wallet=empty_poly_wallet,
        )
        # ASSERT
        self.assertEqual(calculate_minimum_wallet_budget(invalid_wallets), 0)

    def test_get_trade_size_min_of_all_factors_with_smaller_trade_size(self):
        """
        Test that get_trade_size returns the minimum of all factors when the trade opportunity size is smaller.
        Verifies the function's behavior when the trade opportunity size is less than the minimum wallet balance.
        """
        # SETUP
        trade_opportunity_size = Decimal('49.50')  # sqrt(49) = 7

        # Wallet min = min(100, 50) = 50
        # Final result = min(50, 7) = 7
        result = get_trade_size(self.wallets, trade_opportunity_size)

        # ASSERT
        self.assertEqual(result, 7)

    def test_get_trade_size_min_of_all_factors_with_larger_trade_size(self):
        """
        Test that get_trade_size returns the minimum of all factors when the trade opportunity size is larger.
        Verifies the function's behavior when the trade opportunity size is greater than the minimum wallet balance.
        """
        # SETUP
        trade_opportunity_size = Decimal('10000.32')  # sqrt(10000) = 100

        # Wallet min = min(100, 50) = 50
        # Final result = min(50, 100) = 50
        result = get_trade_size(self.wallets, trade_opportunity_size)

        # ASSERT
        self.assertEqual(result, 50)


if __name__ == '__main__':
    unittest.main()
