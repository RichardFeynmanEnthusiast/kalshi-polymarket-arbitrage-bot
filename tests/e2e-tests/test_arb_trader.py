import asyncio
import unittest
from unittest.mock import MagicMock
from decimal import Decimal

from app.message_bus import MessageBus
from app.services.execution.executor import handle_trade_response, initialize_trade_executor
from app.services.trade_storage import TradeStorage
from app.domain.events import ArbTradeResultReceived
from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform
from app.gateways.trade_gateway import TradeGateway
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway

class ArbitrageTraderTest(unittest.TestCase):
    """ User can pass in markets across venues and view the results of arbitrage trades placed"""
    async def asyncSetUp(self):
        # Shared test data
        self.dummy_opportunity = ArbitrageOpportunity(
            market_id="test-market",
            buy_yes_platform=Platform.KALSHI,
            buy_yes_price=Decimal("0.27"),
            buy_no_platform=Platform.POLYMARKET,
            buy_no_price=Decimal("0.25"),
            profit_margin=Decimal("0.50"),
            potential_trade_size=Decimal("100.000"),
            kalshi_ticker="KXFEDCHAIRNOM-29-KW",
            polymarket_yes_token_id="yes-token",
            polymarket_no_token_id="no-token"
        )
        # valid trades
        self.dummy_kalshi_order_response = {
            'order': {'order_id': '0155b151-0659-42a1-af85-52096518e4e6', 'user_id': 'd6982648-9e12-4be6-9c73-759ca49fab21',
                      'ticker': 'KXNBAGAME-25JUN19OKCIND-OKC', 'status': 'executed', 'yes_price': 68, 'no_price': 32,
                      'created_time': '2025-06-19T18:11:40.012766Z', 'expiration_time': None,
                      'self_trade_prevention_type': '', 'action': 'buy', 'side': 'yes', 'type': 'limit',
                      'client_order_id': 'e4e307b6-0f5b-4426-9797-515b84fd0d59', 'order_group_id': ''}}
        self.dummy_poly_order_response = {'errorMsg': '',
                                          'orderID': '0x2edf84dfc54d8d60e1c4549f01cf2e8ea73f6d284c75ebe648c9e2c4ba7c8d51',
                                          'takingAmount': '2.140844', 'makingAmount': '1.519999', 'status': 'matched',
                                          'transactionsHashes': [
                                              '0x6a701d6af2f1a524a78b61bf96313e5efad066ba7016f151f9bbfc395400a9ab'],
                                          'success': True}
        # Create real message bus
        self.bus = MessageBus()

        # Create mock dependencies
        self.mock_trade_repo = MagicMock(spec=TradeGateway)
        self.mock_attempted_opps_repo = MagicMock(spec=AttemptedOpportunitiesGateway)

        # Initialize trade storage service
        self.trade_storage = TradeStorage(
            bus=self.bus,
            trade_repo=self.mock_trade_repo,
            attempted_opportunities_repo=self.mock_attempted_opps_repo,
            batch_size=1,  # Small batch size for immediate processing
            flush_interval_seconds=1
        )

        # Initialize executor
        initialize_trade_executor(
            trade_repo=self.mock_trade_repo,
            bus=self.bus,
            dry_run=True
        )

        # Subscribe trade storage to ArbTradeResultReceived events
        self.bus.subscribe(ArbTradeResultReceived, self.trade_storage.handle_trade_results_received)

        # Start the message bus and trade storage
        self.bus_task = asyncio.create_task(self.bus.run())
        await asyncio.sleep(0.1)  # Give bus time to start

    async def asyncTearDown(self):
        """Clean up after the test"""
        # Cancel the bus task
        if hasattr(self, 'bus_task'):
            self.bus_task.cancel()
            try:
                await self.bus_task
            except asyncio.CancelledError:
                pass

    async def test_user_can_start_running_the_arbitrage_trader(self):

        self.fail("The database should return the same trade details of the executed trade")

        # Pirata passes in a tuple of matched markets
        # self.fail("The app should return a message that the app subscribed to the passed in web sockets")
        # Pirata gets notified when an arbitrage opportunity was found
        # self.fail("The app should return a message that an arbitrage opportunity was found and is attempting to trade")
        # Pirata gets notified when a trade gets executed
        # self.fail("The app should return a message notified him if both legs of the trade were placed")
        # Pirata should view the results of the trade in the database



    def test_user_gets_notified_when_trades_fail_due_to_low_balance(self):
        self.fail("The app should return a message that a trade can't be executed due to low balance")