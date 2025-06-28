import unittest
from decimal import Decimal
import asyncio
from tests.sample_data import (DUMMY_VALID_KALSHI_ORDER_RESPONSE, DUMMY_VALID_POLYMARKET_ORDER_RESPONSE,
                               DUMMY_ARB_OPPORTUNITY_BUY_BOTH)

from app.clients.supabase import SupabaseClient
from app.domain.events import ExecuteTrade, StoreTradeResults
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.gateways.trade_gateway import TradeGateway
from app.services.trade_storage import TradeStorage
from app.message_bus import MessageBus
from app.services.execution import executor

class TestMessageBus(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.db_client = SupabaseClient()
        self.trade_gateway = TradeGateway(kalshi_http=None, polymarket_http=None) # not needed
        self.attempted_opps_gtwy = AttemptedOpportunitiesGateway(self.db_client.client)

        # test data
        self.dummy_opportunity = DUMMY_ARB_OPPORTUNITY_BUY_BOTH
        dummy_raw_kalshi_order_response = DUMMY_VALID_KALSHI_ORDER_RESPONSE
        self.dummy_valid_kalshi_response = self.trade_gateway.process_raw_kalshi_order(dummy_raw_kalshi_order_response,trade_size=Decimal("3.00"))
        self.dummy_poly_order_response = DUMMY_VALID_POLYMARKET_ORDER_RESPONSE

    async def asyncTearDown(self):
        if hasattr(self, 'bus_task'):
            self.bus_task.cancel()
            try:
                await self.bus_task
            except asyncio.CancelledError:
                pass

    # test trade alert to data storage pipeline

    async def customTestReceivedTradeSetup(self, batch_size : int, flush_interval_seconds = 30*60):
        """ Mocks setup from main """
        # Start background task for service
        self.bus = MessageBus()
        self.trade_storage = TradeStorage(bus=self.bus, trade_repo=None,
                                          attempted_opportunities_repo=self.attempted_opps_gtwy, batch_size=batch_size, flush_interval_seconds=flush_interval_seconds)
        await self.trade_storage.start()
        executor.initialize_trade_executor(
            trade_repo=None,  # Not needed for this test
            bus=self.bus,
            dry_run=False,
            max_trade_size=100
        )

        self.bus.subscribe(ExecuteTrade, executor.handle_execute_trade)
        self.bus.subscribe(StoreTradeResults, self.trade_storage.handle_trade_results_received)

        # Start the message bus run loop
        self.bus_task = asyncio.create_task(self.bus.run())

    async def customTestReceivedTradeCleanup(self):
        """ Mocks cleanup from main with an additional unsubscribe to reset further tests"""
        self.bus_task.cancel()
        try:
            await self.bus_task
        except asyncio.CancelledError:
            pass
        self.bus.unsubscribe_all()

    async def simulate_valid_trade_received(self, batch_size : int, number_of_trades: int):
        """
            Simulates the reception of valid trade responses for a given batch size.

            This method is designed to test the behavior of the TradeStorage service when
            processing a specified number of valid trade responses. It ensures that the
            service correctly handles the accumulation and storage of trade results in
            batches after the executor calls trade response.

            Args:
                batch_size (int): The number of trades to accumulate before triggering a batch flush.
                number_of_trades (int): The total number of trade responses to simulate.

            Returns:
                tuple: A tuple containing the initial and final count of attempted opportunities
                       in the database, allowing verification of the expected increase in count
                       after processing the trades.
        """
        await self.customTestReceivedTradeSetup(batch_size=batch_size)
        initial_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())

        for i in range(number_of_trades):
            # Simulate executor call
            await executor.handle_trade_response(
                kalshi_result=self.dummy_valid_kalshi_response,
                polymarket_result=self.dummy_poly_order_response,
                category="buy both",
                opportunity=self.dummy_opportunity
            )
            # Allow some time for async operations to complete
            await asyncio.sleep(0.2)

        # Get final count
        final_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        await self.customTestReceivedTradeCleanup()
        return initial_count, final_count

    async def assert_all_trades_were_inserted(self, batch_size : int, number_of_trades: int):
        """ helper method to call tests to assure number of trades stored matches the number_of_trades param """
        initial_count, final_count = await self.simulate_valid_trade_received(batch_size=batch_size, number_of_trades=number_of_trades)
        self.assertEqual(initial_count + number_of_trades, final_count,
                         f"initial count: {initial_count}, received final count: {final_count}")
        await self.trade_storage.stop()

    async def assert_no_new_trades_were_inserted(self, batch_size : int, number_of_trades: int):
        """ helper method to call tests when number of trades < batch_size """
        initial_count, final_count = await self.simulate_valid_trade_received(batch_size=batch_size, number_of_trades=number_of_trades)
        self.assertEqual(initial_count, final_count,
                         f"initial count: {initial_count}, received final count: {final_count}")
        await self.trade_storage.stop()

    async def test_singe_batch_and_single_trade(self):
        """ Tests that with a single batch & single trade capacity,
          app places all trades into the db"""
        await self.assert_all_trades_were_inserted(batch_size=1, number_of_trades=1)

    async def test_multiple_batches_and_equivalent_sized_trades(self):
        """ Test when batch size and number of trades are equal,
        app places all trades into the db """
        await self.assert_all_trades_were_inserted(batch_size=2, number_of_trades=2)
        await self.assert_all_trades_were_inserted(batch_size=3, number_of_trades=3)
        await self.assert_all_trades_were_inserted(batch_size=4, number_of_trades=4)

    async def test_batch_length_greater_than_trades(self):
        """ Test when batch size is greater than the number of trades,
        coroutine process inserts no new trade results into the db """
        await self.assert_no_new_trades_were_inserted(batch_size=2, number_of_trades=1)
        await self.assert_no_new_trades_were_inserted(batch_size=3, number_of_trades=2)
        await self.assert_no_new_trades_were_inserted(batch_size=4, number_of_trades=3)

    async def test_number_of_trades_greater_than_batch_size_with_no_remainder(self):
        """ Test when batch size is a multiple of trades, eventually
        coroutine process inserts all trades into the db """
        await self.assert_all_trades_were_inserted(batch_size=1, number_of_trades=2)
        await self.assert_all_trades_were_inserted(batch_size=2, number_of_trades=4)

    async def test_number_of_trades_greater_than_batch_size_with_remainder_on_cancel(self):
        """ Test that when app process is cancelled trade storage service flushes remaining tasks """
        number_of_trades = 8
        batch_size = 3
        initial_count, trades_stored_before_stop_method = await self.simulate_valid_trade_received(batch_size=batch_size,
                                                                                                   number_of_trades=number_of_trades)
        greatest_multiple_of_batch_size = (number_of_trades // batch_size) * batch_size
        self.assertEqual(initial_count + greatest_multiple_of_batch_size, trades_stored_before_stop_method,
                         f"initial count: {initial_count}, count after core service completed: {trades_stored_before_stop_method}")
        # simulate service being cancelled
        await self.trade_storage.stop()
        final_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        self.assertEqual(initial_count + number_of_trades, final_count,
                         f"initial count: {initial_count}, received final count: {final_count}")

    async def test_trades_placed_after_flush_interval_seconds(self):
        """ Test that the service flushes after the predefined period """
        flush_interval_seconds = 3
        number_of_trades = 2
        await self.customTestReceivedTradeSetup(batch_size=500, flush_interval_seconds=flush_interval_seconds)
        initial_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        for i in range(number_of_trades):  # trades received << batch size
            # Simulate executor call
            await executor.handle_trade_response(
                kalshi_result=self.dummy_valid_kalshi_response,
                polymarket_result=self.dummy_poly_order_response,
                category="buy both",
                opportunity=self.dummy_opportunity
            )
            # Allow some time for async operations to complete
            await asyncio.sleep(0.2)

        await asyncio.sleep(flush_interval_seconds * (number_of_trades + 0.2))  # await flush tasks

        final_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        self.assertEqual(initial_count + number_of_trades, final_count,
                         f"initial count: {initial_count}, received final count: {final_count}")

    async def test_most_likely_production_scenario_for_trade_service(self):
        """ Simulate the service with parameters used in production as well as most
         Trades will be stored on service cancellation """
        flush_interval_seconds = 30*60
        number_of_trades = 6
        batch_size = 100
        initial_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        await self.customTestReceivedTradeSetup(batch_size=batch_size, flush_interval_seconds=flush_interval_seconds)
        for i in range(number_of_trades//2):  # trades received << batch size
            # Simulate executor call
            await executor.handle_trade_response(
                kalshi_result=self.dummy_valid_kalshi_response,
                polymarket_result=self.dummy_poly_order_response,
                category="buy both",
                opportunity=self.dummy_opportunity
            )
        await asyncio.sleep(2) # other tasks
        for i in range(number_of_trades//2):  # trades received << batch size
            # Simulate executor call
            await executor.handle_trade_response(
                kalshi_result=self.dummy_valid_kalshi_response,
                polymarket_result=self.dummy_poly_order_response,
                category="buy both",
                opportunity=self.dummy_opportunity
            )

        await asyncio.sleep(2)  # other tasks
        intermediate_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        self.assertEqual(initial_count, intermediate_count,f"Expected no trades to be placed got {initial_count} but received {intermediate_count}")
        await self.trade_storage.stop()
        final_count = len(self.attempted_opps_gtwy.get_attempted_opportunities())
        self.assertEqual(initial_count + number_of_trades, final_count,
                         f"initial count: {initial_count}, received final count: {final_count}")