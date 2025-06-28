import logging

from app.message_bus import MessageBus
from app.domain.events import StoreTradeResults

# log

class BalanceService:
    """
    The BalanceService class is responsible for managing and updating the balances
    of different trading platforms, specifically Polymarket and Kalshi. It maintains
    the current USDC.e balance for Polymarket and the balance for Kalshi, and is
    initialized with a message bus for handling events and commands related to
    trade results.
    """

    def __init__(self, polymarket_usdc_e: float, kalshi_balance: float, bus: MessageBus):
        self.polymarket_usdc_e = polymarket_usdc_e
        self.kalshi_balance = kalshi_balance
        self.bus = bus
        self.logger = logging.getLogger(__name__)

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

