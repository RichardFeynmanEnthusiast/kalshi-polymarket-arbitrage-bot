import unittest
from decimal import Decimal

from app.domain.primitives import Money
from app.strategies.trade_prct_size import calculate_trade_size, get_trade_size
from tests.sample_data import VALID_WALLETS_LARGER_KALSHI


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
        self.assertEqual(calculate_trade_size(Decimal('9.9')), 1)
        self.assertEqual(calculate_trade_size(Decimal('16')), 2)
        self.assertEqual(calculate_trade_size(Decimal('0')), 0)
        self.assertEqual(calculate_trade_size(Decimal('1.0')), 0)
        self.assertEqual(calculate_trade_size(Decimal('100.00')), 15)
        self.assertEqual(calculate_trade_size(Decimal('10000.92')), 1500)

    def test_get_trade_size_min_of_all_factors_with_larger_opp_size_than_budget(self):
        """
        Test that get_trade_size returns the minimum of all factors when the trade opportunity size is larger.
        Verifies the function's behavior when the trade opportunity size is greater than the minimum wallet balance.
        """
        # SETUP
        trade_opportunity_size = Decimal('10000.32')  # returns 1500

        # Wallet min = min(95-1, 50) = 50
        # Final result = min(50, 1500) = 1500 > wallet budget => 0
        result = get_trade_size(self.wallets, trade_opportunity_size, kalshi_fees=self.kalshi_fees)

        # ASSERT
        self.assertEqual(result, 0)

    def test_get_trade_size_min_of_all_factors_with_smaller_opp_size_than_budget(self):
        """
        Test that get_trade_size returns the minimum of all factors when the trade opportunity size is larger.
        Verifies the function's behavior when the trade opportunity size is greater than the minimum wallet balance.
        """
        # SETUP
        trade_opportunity_size = Decimal('100.32')  # returns 1500

        # Wallet min = min(95-1, 50) = 50
        # Final result = min(50, 15) = 15
        result = get_trade_size(self.wallets, trade_opportunity_size, kalshi_fees=self.kalshi_fees)

        # ASSERT
        self.assertEqual(result, 15)