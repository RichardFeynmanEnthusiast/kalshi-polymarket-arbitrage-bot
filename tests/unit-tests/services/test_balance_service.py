import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

from app.services.operational.balance_service import BalanceService
from shared_wallets.domain.types import Currency, Money
from shared_wallets.domain.models import ExchangeWallet, Exchange
from app.domain.types import Wallets

def make_wallet(balances):
    return ExchangeWallet(exchange=Exchange.KALSHI, balances=balances)

class TestBalanceService(unittest.TestCase):
    def setUp(self):
        self.mock_gateway = Mock()
        self.minimum_balance = Decimal("50.0")
        self.service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)

    def test_generate_new_wallets_success(self):
        self.mock_gateway.get_venue_balances.return_value = {
            Currency.USD: Money(Decimal("100.00"), Currency.USD),
            Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E),
            Currency.POL: Money(Decimal("3.00"), Currency.POL),
        }

        wallets = self.service.generate_new_wallets()

        self.assertIsInstance(wallets, Wallets)
        self.assertEqual(wallets.kalshi_wallet.get_balance(Currency.USD).amount, Decimal("100.00"))
        self.assertEqual(wallets.polymarket_wallet.get_balance(Currency.USDC_E).amount, Decimal("200.00"))
        self.assertEqual(wallets.polymarket_wallet.get_balance(Currency.POL).amount, Decimal("3.00"))

    def test_generate_new_wallets_raises_on_missing_currency(self):
        self.mock_gateway.get_venue_balances.return_value = {
            Currency.USD: Money(Decimal("100.00"), Currency.USD),
            # Missing USDC_E
            Currency.POL: Money(Decimal("3.00"), Currency.POL),
        }

        with self.assertRaises(KeyError):
            self.service.generate_new_wallets()

    def test_update_wallets_sets_wallets(self):
        wallets = Wallets(
            kalshi_wallet=make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)}),
            polymarket_wallet=make_wallet({Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E)})
        )

        self.service.generate_new_wallets = Mock(return_value=wallets)
        result = self.service.update_wallets()

        self.assertEqual(result, wallets)
        self.assertEqual(self.service.get_wallets(), wallets)

    def test_update_wallets_raises_and_wraps(self):
        self.mock_gateway.get_venue_balances.side_effect = Exception("mock fail from gateway")
        with self.assertRaises(Exception) as ctx:
            self.service.update_wallets()
        self.assertIn("Failed to update wallets", str(ctx.exception))

    def test_kalshi_wallet_property_raises_if_none(self):
        self.service._wallets = Mock(kalshi_wallet=None, polymarket_wallet=Mock())
        with self.assertRaises(RuntimeError):
            _ = self.service.kalshi_wallet

    def test_polymarket_wallet_property_raises_if_none(self):
        self.service._wallets = Mock(kalshi_wallet=Mock(), polymarket_wallet=None)
        with self.assertRaises(RuntimeError):
            _ = self.service.polymarket_wallet

    def test_has_enough_balance_true(self):
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E)})
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))

        self.assertTrue(self.service.has_enough_balance)

    def test_has_enough_balance_false_kalshi_low(self):

        # SETUP
        kalshi = make_wallet({Currency.USD: Money(Decimal("10.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E)})
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # ASSERT
        # minium balance is set to 50
        self.assertFalse(self.service.has_enough_balance)

    def test_has_enough_balance_false_polymarket_low(self):
        # SETUP
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("5.00"), Currency.USDC_E)})
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # ASSERT
        self.assertFalse(self.service.has_enough_balance)

    def test_has_enough_balance_balance_equal_to_minimum(self):
        # SETUP
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("50.00"), Currency.USDC_E)})
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # ASSERT
        self.assertFalse(self.service.has_enough_balance)

    def test_has_enough_balance_valid_case(self):
        # SETUP
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("50.01"), Currency.USDC_E)})
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # ASSERT
        self.assertTrue(self.service.has_enough_balance)