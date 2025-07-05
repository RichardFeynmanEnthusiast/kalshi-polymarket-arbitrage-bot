import logging
from decimal import Decimal, ROUND_FLOOR

from app.gateways.balance_data_gateway import BalanceDataGateway
from app.domain.events import StoreTradeResults
from app.domain.types import Wallets
from shared_wallets.domain.types import Currency, Money
from shared_wallets.domain.models import ExchangeWallet, Exchange
from app.settings.settings import settings

logger = logging.getLogger(__name__)


class BalanceService:
    """
    The BalanceService class is responsible for managing and updating the balances
    of different trading platforms, specifically Polymarket and Kalshi. It maintains
    the current USDC.e balance for Polymarket and the balance for Kalshi, and is
    initialized with a message bus for handling events and commands related to
    trade results.
    """

    def __init__(self, balance_data_gateway: BalanceDataGateway, minimum_balance):
        self._balance_data_gateway = balance_data_gateway
        self._minimum_balance : Decimal = minimum_balance
        self._wallets = None
        self._total_spent : Decimal = Decimal("0.00")
        self._maximum_spend : Decimal

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

    def set_maximum_spend(self):
        """
            Calculates and sets the maximum allowable spend based on the configured
            MINIMUM_WALLET_BALANCE and SHUTDOWN_BALANCE from settings.

            This should be called before the application starts to ensure that
            sufficient funds are available to operate safely. If the resulting
            maximum spend is invalid (negative or too close to shutdown threshold),
            a ValueError is raised.

            Raises:
                ValueError: If the calculated maximum spend is less than or equal
                            to the shutdown balance or negative.
         """
        try:
            self._maximum_spend = settings.MINIMUM_WALLET_BALANCE - settings.SHUTDOWN_BALANCE
            if self._maximum_spend < 0 or self._maximum_spend <= settings.SHUTDOWN_BALANCE:
                raise ValueError(
                    f"Invalid maximum spend: {self._maximum_spend}. "
                )
        except ValueError as e:
            logger.error(f"Failed to set maximum spend: {e}")
            raise

    async def handle_trade_results_received(self, command: StoreTradeResults):

        if command.arb_trade_results.polymarket_order is not None:
            self.update_polymarket_balance(command.arb_trade_results)
        else:
            logger.warning(f"Polymarket trade with message id {command.arb_trade_results.message_id} is empty; skipping balance update for polymarket")

        if command.arb_trade_results.kalshi_trade is not None:
            self.update_kalshi_balance(command.arb_trade_results)
        else:
            logger.warning(f"Kalshi trade with message id {command.arb_trade_results.message_id} is empty; skipping balance update for kalshi")

    def generate_new_wallets(self) -> Wallets:
        logger.info("Generating wallets...")
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
            logger.info(f"Found kalshi balance: ${kalshi_balance[Currency.USD]} & polymarket balance: USDCE.e {polymarket_balance[Currency.USDC_E]}"
                             f"with pol: ${polymarket_balance[Currency.POL]}")
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

    def update_total_spend(self, trade_placed_size : Decimal):
        """ Conservatively update total spent regardless of which venues got updated """
        self._total_spent += trade_placed_size

    def set_wallets(self, wallets: Wallets):
        """ """
        self._wallets = wallets

    def get_wallets(self) -> Wallets:
        polymarket_usdc_e_amount : Decimal = settings.MINIMUM_WALLET_BALANCE - self._total_spent # cannot trust chain coin data
        polymarket_internal_state_wallet : ExchangeWallet = ExchangeWallet(exchange=Exchange.POLYMARKET,
                                                                           balances={
                                                                               Currency.USDC_E : Money(
                                                                                   amount=polymarket_usdc_e_amount,
                                                                                   currency=Currency.USDC_E
                                                                               ),
                                                                               Currency.POL : Money(
                                                                                   amount=self.polymarket_wallet.get_balance(
                                                                                       Currency.POL
                                                                                   ).amount,
                                                                                   currency=Currency.POL
                                                                               )
                                                                           })

        return_wallet = Wallets(
            polymarket_wallet=polymarket_internal_state_wallet,
            kalshi_wallet=self.kalshi_wallet, # trust kalshi
        )
        return return_wallet

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
    @property
    def maximum_spend_reached(self) -> bool:
        maximum_spend_reached = self._total_spent >= self._maximum_spend
        return maximum_spend_reached