import unittest
from decimal import Decimal
from unittest.mock import patch

from app.domain.primitives import Money
from shared_wallets.domain.types import Currency
from app.domain.types import Wallets
from app.strategies.trade_sqrt_size import get_trade_size, calculate_minimum_wallet_budget, calculate_trade_size
from shared_wallets.domain.models import ExchangeWallet, Exchange
from tests.sample_data import VALID_WALLETS_LARGER_KALSHI, VALID_WALLETS_LARGER_POLY, VALID_WALLETS_EQUAL


class TestTradeSizeCalculations(unittest.TestCase):

    def setUp(self):
        """
        Set up the test environment by initializing wallet balances for Kalshi and Polymarket exchanges.
        Creates ExchangeWallet instances for each exchange and aggregates them into a Wallets instance.
        """
        # setup
        self.wallets = VALID_WALLETS_LARGER_KALSHI
        self.polymarket_wallet = self.wallets.polymarket_wallet # 50
        self.kalshi_wallet = self.wallets.kalshi_wallet # $100
        self.kalshi_fees = Money("1.00")


    def test_calculate_trade_size_rounds_down(self):
        """
        Test that the calculate_trade_size function correctly rounds down the trade size.
        Verifies the function's behavior with various decimal inputs.
        """
        # ASSERT
        self.assertEqual(calculate_trade_size(Decimal('9.9')), 3)
        self.assertEqual(calculate_trade_size(Decimal('16')), 4)
        self.assertEqual(calculate_trade_size(Decimal('0')), 0)
        self.assertEqual(calculate_trade_size(Decimal('1.0')), 1)
        self.assertEqual(calculate_trade_size(Decimal('100.00')), 10)
        self.assertEqual(calculate_trade_size(Decimal('10000.92')), 100)

    def test_calculate_minimum_wallet_budget_returns_minimum_wallet_balance(self):
        # Act
        result = calculate_minimum_wallet_budget(self.wallets, self.kalshi_fees)
        # Assert
        self.assertEqual(result, self.polymarket_wallet.get_balance(Currency.USDC_E).amount)

    def test_calculate_minimum_wallet_budget_returns_kalshi_when_kalshi_smaller(self):
        # Adjust
        wallets = VALID_WALLETS_LARGER_POLY
        expected_kalshi_budget = 95 - 1  # 5% guard minus fees
        # Act
        result = calculate_minimum_wallet_budget(wallets, self.kalshi_fees)
        # Assert
        self.assertEqual(result, expected_kalshi_budget)

    def test_calculate_minimum_wallet_budget_returns_kalshi_minus_fees_when_wallets_equal(self):
        # Adjust
        wallets = VALID_WALLETS_EQUAL
        expected_kalshi_budget = 95 - 1  # 5% guard minus fees
        # Act
        result = calculate_minimum_wallet_budget(wallets, self.kalshi_fees)
        # Assert
        self.assertEqual(result, expected_kalshi_budget)
        self.assertNotEqual(result, self.polymarket_wallet.get_balance(Currency.USDC_E).amount)

    def test_calculate_minimum_wallet_returns_0_with_very_large_fees(self):
        # Adjust
        wallets = VALID_WALLETS_EQUAL
        expected_kalshi_budget = max((95 - 97), 0)  # 5% guard minus $97 fee
        # Act
        result = calculate_minimum_wallet_budget(wallets, kalshi_fees=Decimal('97.00'))
        # Assert
        self.assertEqual(result, expected_kalshi_budget)
        self.assertNotEqual(result, self.polymarket_wallet.get_balance(Currency.USDC_E).amount)

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
        self.assertEqual(calculate_minimum_wallet_budget(invalid_wallets, self.kalshi_fees), 0)

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
        self.assertEqual(calculate_minimum_wallet_budget(invalid_wallets, self.kalshi_fees), 0)

    @patch("app.strategies.trade_sqrt_size.settings")
    def test_get_trade_size_min_of_all_factors_with_smaller_trade_size(self, mock_settings):
        """
        Test that get_trade_size returns the minimum of all factors when the trade opportunity size is smaller.
        Verifies the function's behavior when the trade opportunity size is less than the minimum wallet balance.
        """
        # SETUP
        mock_settings.SHUTDOWN_BALANCE = Decimal("20")
        trade_opportunity_size = Decimal('49.50')  # sqrt(49) = 7

        # Wallet min = min(95-1, 50) = 50
        # Final result = min(50, 7) = 7
        result = get_trade_size(self.wallets, trade_opportunity_size, self.kalshi_fees)

        # ASSERT
        self.assertEqual(result, 0)


    def test_get_trade_size_min_of_all_factors_with_larger_trade_size(self):
        """
        Test that get_trade_size returns the minimum of all factors when the trade opportunity size is larger.
        Verifies the function's behavior when the trade opportunity size is greater than the minimum wallet balance.
        """
        # SETUP
        trade_opportunity_size = Decimal('10000.32')  # sqrt(10000) = 100

        # Wallet min = min(95-1, 50) = 50
        # Final result = min(50, 100) = 50
        result = get_trade_size(self.wallets, trade_opportunity_size, kalshi_fees=self.kalshi_fees)

        # ASSERT
        self.assertEqual(result, 50)


if __name__ == '__main__':
    unittest.main()
