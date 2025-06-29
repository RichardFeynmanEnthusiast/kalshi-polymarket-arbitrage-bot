import logging
from decimal import Decimal

from app.gateways.balance_data_gateway import BalanceDataGateway
from app.domain.events import StoreTradeResults
from app.domain.types import Wallets
from shared_wallets.domain.types import Currency
from shared_wallets.domain.models import ExchangeWallet, Exchange


class BalanceService:
    """
    The BalanceService class is responsible for managing and updating the balances
    of different trading platforms, specifically Polymarket and Kalshi. It maintains
    the current USDC.e balance for Polymarket and the balance for Kalshi, and is
    initialized with a message bus for handling events and commands related to
    trade results.
    """

    def __init__(self, balance_data_gateway: BalanceDataGateway, minimum_balance):
        self.logger = logging.getLogger(__name__)
        self._balance_data_gateway = balance_data_gateway
        self._minimum_balance : Decimal = minimum_balance
        self._wallets = None

    def update_polymarket_balance(self, trade_result):
        """
        Update the Polymarket balance based on the trade result.
        This function will handle the logic to adjust the balance
        according to the details of the Polymarket trade.
        """
        pass

    def update_kalshi_balance(self, trade_result):
        """
        Update the Kalshi balance based on the trade result.
        This function will handle the logic to adjust the balance
        according to the details of the Kalshi trade.
        """
        pass

    async def handle_trade_results_received(self, command: StoreTradeResults):

        if command.arb_trade_results.polymarket_order is not None:
            self.update_polymarket_balance(command.arb_trade_results)
        else:
            self.logger.warning(f"Polymarket trade with message id {command.arb_trade_results.message_id} is empty; skipping balance update for polymarket")

        if command.arb_trade_results.kalshi_trade is not None:
            self.update_kalshi_balance(command.arb_trade_results)
        else:
            self.logger.warning(f"Kalshi trade with message id {command.arb_trade_results.message_id} is empty; skipping balance update for kalshi")

    def generate_new_wallets(self) -> Wallets:
        self.logger.info("Generating wallets...")
        try:
            # exception handles 0 balance or null case
            currencies = self._balance_data_gateway.get_venue_balances()
            kalshi_balance = {
                Currency.USD : currencies[Currency.USD],
            }
            polymarket_balance = {
                Currency.USDC_E : currencies[Currency.USDC_E],
                Currency.POL: currencies[Currency.POL],
            }
            return Wallets(kalshi_wallet=ExchangeWallet(Exchange.KALSHI, kalshi_balance),
                           polymarket_wallet=ExchangeWallet(Exchange.POLYMARKET, polymarket_balance))
        except Exception as e:
            raise e

    def update_wallets(self) -> Wallets:
        try:
            new_wallets = self.generate_new_wallets()
            self.set_wallets(new_wallets)
            return new_wallets
        except Exception as e:
            raise Exception(f"Failed to update wallets: {e}")

    def set_wallets(self, wallets: Wallets):
        """ """
        self._wallets = wallets

    def get_wallets(self):
        return self._wallets

    @property
    def kalshi_wallet (self) -> ExchangeWallet:
        if self._wallets.kalshi_wallet is None:
            raise RuntimeError("Kalshi wallet is not initialized")
        return self._wallets.kalshi_wallet

    @property
    def polymarket_wallet(self) -> ExchangeWallet:
        if self._wallets.polymarket_wallet is None:
            raise RuntimeError("Polymarket wallet is not initialized")
        return self._wallets.polymarket_wallet

    @property
    def has_enough_balance(self) -> bool:
        # exclusive to prevent triggering a trade failure due to insufficient balance
        has_enough_kalshi = self.kalshi_wallet.get_balance(Currency.USD).amount > self._minimum_balance
        has_enough_polymarket =  self.polymarket_wallet.get_balance(Currency.USDC_E).amount > self._minimum_balance
        return has_enough_kalshi and has_enough_polymarket