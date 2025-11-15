import unittest
from decimal import Decimal
from unittest.mock import Mock

from shared_wallets.domain.types import Currency, Money

from app.gateways.balance_data_gateway import BalanceDataGateway  # adjust the path as needed


class TestBalanceDataGateway(unittest.TestCase):

    def setUp(self):
        self.mock_clob = Mock()
        self.mock_kalshi = Mock()
        self.gateway = BalanceDataGateway(self.mock_clob, self.mock_kalshi)
        self.gateway.logger = Mock()  # mock logger to suppress output

    def test_returns_correct_balances(self):
        self.mock_clob.get_starting_balances.return_value = (1000, 2 * 10**18)
        self.mock_kalshi.get_balance.return_value = {"balance": 20000}

        balances = self.gateway.get_venue_balances()

        self.assertEqual(balances[Currency.USDC_E], Money(Decimal("1000"), Currency.USDC_E))
        self.assertEqual(balances[Currency.POL], Money(Decimal("2"), Currency.POL))
        self.assertEqual(balances[Currency.USD], Money(Decimal("200"), Currency.USD))  # 20000 / 100

    def test_raises_if_usdc_e_is_zero(self):
        self.mock_clob.get_starting_balances.return_value = (0, 2 * 10**18)
        self.mock_kalshi.get_balance.return_value = {"balance": 20000}

        with self.assertRaises(ValueError) as ctx:
            self.gateway.get_venue_balances()
        self.assertIn("must be greater than zero", str(ctx.exception))

    def test_raises_if_matic_is_none(self):
        self.mock_clob.get_starting_balances.return_value = (1000, None)
        self.mock_kalshi.get_balance.return_value = {"balance": 20000}

        with self.assertRaises(ValueError) as ctx:
            self.gateway.get_venue_balances()
        self.assertIn("not found", str(ctx.exception))

    def test_raises_if_kalshi_balance_zero(self):
        self.mock_clob.get_starting_balances.return_value = (1000, 2 * 10**18)
        self.mock_kalshi.get_balance.return_value = {"balance": 0}

        with self.assertRaises(ValueError) as ctx:
            self.gateway.get_venue_balances()
        self.assertIn("Kalshi balance must be greater than zero", str(ctx.exception))

    def test_raises_if_kalshi_balance_none(self):
        self.mock_clob.get_starting_balances.return_value = (1000, 2 * 10**18)
        self.mock_kalshi.get_balance.return_value = {"balance": None}

        with self.assertRaises(ValueError) as ctx:
            self.gateway.get_venue_balances()
        self.assertIn("Kalshi balance not found", str(ctx.exception))

    def test_balance_values_are_money_with_correct_currency(self):
        self.mock_clob.get_starting_balances.return_value = (1000, 2 * 10 ** 18)
        self.mock_kalshi.get_balance.return_value = {"balance": 20000}

        balances = self.gateway.get_venue_balances()

        expected_currencies = {Currency.USD, Currency.POL, Currency.USDC_E}
        self.assertEqual(set(balances.keys()), expected_currencies)

        for currency in expected_currencies:
            value = balances[currency]
            self.assertIsInstance(value, Money, f"Value for {currency} is not a Money instance")
            self.assertEqual(value.currency, currency, f"Money object for {currency} has incorrect currency")


if __name__ == "__main__":
    unittest.main()
