import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

from shared_wallets.domain.models import ExchangeWallet, Exchange
from shared_wallets.domain.types import Currency, Money

from app.domain.types import Wallets
from app.services.operational.balance_service import BalanceService


def make_wallet(balances):
    return ExchangeWallet(exchange=Exchange.KALSHI, balances=balances)

class TestBalanceService(unittest.TestCase):
    def setUp(self):
        self.mock_gateway = Mock()
        self.minimum_balance = Decimal("50.0")
        self.service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)

    def test_generate_new_wallets_success(self):
        # Arrange
        self.mock_gateway.get_venue_balances.return_value = {
            Currency.USD: Money(Decimal("100.00"), Currency.USD),
            Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E),
            Currency.POL: Money(Decimal("3.00"), Currency.POL),
        }
        # Act
        wallets = self.service.generate_new_wallets()
        # Assert
        self.assertIsInstance(wallets, Wallets)
        self.assertEqual(wallets.kalshi_wallet.get_balance(Currency.USD).amount, Decimal("100.00"))
        self.assertEqual(wallets.polymarket_wallet.get_balance(Currency.USDC_E).amount, Decimal("200.00"))
        self.assertEqual(wallets.polymarket_wallet.get_balance(Currency.POL).amount, Decimal("3.00"))

    def test_generate_new_wallets_raises_on_missing_currency(self):
        # Arrange
        self.mock_gateway.get_venue_balances.return_value = {
            Currency.USD: Money(Decimal("100.00"), Currency.USD),
            # Missing USDC_E
            Currency.POL: Money(Decimal("3.00"), Currency.POL),
        }
        # Assert
        with self.assertRaises(KeyError):
            self.service.generate_new_wallets()

    def test_update_wallets_sets_wallets(self):
        # Arrange
        wallets = Wallets(
            kalshi_wallet=make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)}),
            polymarket_wallet=make_wallet({Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E)})
        )
        self.service.generate_new_wallets = Mock(return_value=wallets)
        # Act
        result = self.service.update_wallets()
        # Assert
        self.assertEqual(result, wallets)

    def test_update_wallets_raises_and_wraps(self):
        # Arrange
        self.mock_gateway.get_venue_balances.side_effect = Exception("mock fail from gateway")
        # Assert
        with self.assertRaises(Exception) as ctx:
            self.service.update_wallets()
        self.assertIn("Failed to update wallets", str(ctx.exception))

    def test_kalshi_wallet_property_raises_if_none(self):
        # Arrange
        self.service._wallets = Mock(kalshi_wallet=None, polymarket_wallet=Mock())
        # Assert
        with self.assertRaises(RuntimeError):
            _ = self.service.kalshi_wallet

    def test_polymarket_wallet_property_raises_if_none(self):
        # Arrange
        self.service._wallets = Mock(kalshi_wallet=Mock(), polymarket_wallet=None)
        # Assert
        with self.assertRaises(RuntimeError):
            _ = self.service.polymarket_wallet

    def test_has_enough_balance_true(self):
        # Arrange
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E)})
        # Act
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # Assert
        self.assertTrue(self.service.has_enough_balance)

    def test_has_enough_balance_false_kalshi_low(self):

        # Arrange
        kalshi = make_wallet({Currency.USD: Money(Decimal("10.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("200.00"), Currency.USDC_E)})
        # Act
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # Assert
        # minium balance is set to 50
        self.assertFalse(self.service.has_enough_balance)

    def test_has_enough_balance_false_polymarket_low(self):
        # Arrange
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("5.00"), Currency.USDC_E)})
        # Act
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # Assert
        self.assertFalse(self.service.has_enough_balance)

    def test_has_enough_balance_balance_equal_to_minimum(self):
        # Arrange
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("50.00"), Currency.USDC_E)})
        # Act
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # Assert
        self.assertFalse(self.service.has_enough_balance)

    def test_has_enough_balance_valid_case(self):
        # Arrange
        kalshi = make_wallet({Currency.USD: Money(Decimal("100.00"), Currency.USD)})
        polymarket = make_wallet({Currency.USDC_E: Money(Decimal("50.01"), Currency.USDC_E)})
        # Act
        self.service.set_wallets(Wallets(kalshi_wallet=kalshi, polymarket_wallet=polymarket))
        # Assert
        self.assertTrue(self.service.has_enough_balance)

    @patch("app.services.operational.balance_service.settings")
    def test_maximum_spend_not_reached(self, mock_settings):
        # Adjust
        mock_settings.MINIMUM_WALLET_BALANCE = Decimal("100")
        mock_settings.SHUTDOWN_BALANCE = Decimal("20")
        service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)
        service.set_maximum_spend()
        self.assertFalse(service.maximum_spend_reached)

    @patch("app.services.operational.balance_service.settings")
    def test_maximum_spend_not_reached_with_adjusted_spend(self, mock_settings):
        # Adjust
        mock_settings.MINIMUM_WALLET_BALANCE = Decimal("100")
        mock_settings.SHUTDOWN_BALANCE = Decimal("20")
        service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)
        service.set_maximum_spend()
        service._total_spent = Decimal("50")
        self.assertFalse(service.maximum_spend_reached)

    @patch("app.services.operational.balance_service.settings")
    def test_maximum_spend_reached_with_adjusted_spend(self, mock_settings):
        # Adjust
        mock_settings.MINIMUM_WALLET_BALANCE = Decimal("50")
        mock_settings.SHUTDOWN_BALANCE = Decimal("20")
        service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)
        service.set_maximum_spend()
        # Act
        service._total_spent = Decimal("50")
        self.assertTrue(service.maximum_spend_reached)

    @patch("app.services.operational.balance_service.settings")
    def test_maximum_spend_cannot_start_with_negative_values(self, mock_settings):
        # Adjust
        mock_settings.MINIMUM_WALLET_BALANCE = Decimal("20")
        mock_settings.SHUTDOWN_BALANCE = Decimal("30")
        service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)
        # Assert
        with self.assertRaises(ValueError) as ctx:
            service.set_maximum_spend()

        self.assertIn("Invalid maximum spend", str(ctx.exception))

    @patch("app.services.operational.balance_service.settings")
    def test_update_total_spend_increments_total_spend(self, mock_settings):
        # Adjust
        mock_settings.MINIMUM_WALLET_BALANCE = Decimal("100")
        mock_settings.SHUTDOWN_BALANCE = Decimal("20")
        service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)
        service.set_maximum_spend() # 80
        # Act
        service.update_total_spend(trade_placed_size=Decimal("50"))
        # Assert
        self.assertEqual(service._total_spent, Decimal("50"))

    @patch("app.services.operational.balance_service.settings")
    def test_update_total_spend_changes_sets_max_spend_reached(self, mock_settings):
        # Adjust
        mock_settings.MINIMUM_WALLET_BALANCE = Decimal("100")
        mock_settings.SHUTDOWN_BALANCE = Decimal("20")
        service = BalanceService(balance_data_gateway=self.mock_gateway, minimum_balance=self.minimum_balance)
        service.set_maximum_spend()  # 80
        # Act
        service.update_total_spend(trade_placed_size=Decimal("50"))
        service.update_total_spend(trade_placed_size=Decimal("50"))
        # Assert
        self.assertTrue(service.maximum_spend_reached)