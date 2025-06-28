import asyncio
import unittest
from unittest.mock import MagicMock
from decimal import Decimal

from app.services.trade_storage import TradeStorage
from app.domain.types import KalshiOrder, PolymarketOrder
from app.domain.events import ArbTradeResultReceived, StoreTradeResults
from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform
from app.message_bus import MessageBus
from app.gateways.trade_gateway import TradeGateway
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.clients.supabase import SupabaseClient
from tests.sample_data import (DUMMY_VALID_KALSHI_ORDER_RESPONSE,
                               DUMMY_ARB_OPPORTUNITY_BUY_BOTH, DUMMY_VALID_POLYMARKET_ORDER_RESPONSE)

class TestTradeStorage(unittest.IsolatedAsyncioTestCase):
    """Test the TradeStorage service with actual database"""

    async def asyncSetUp(self):
        # Create real message bus
        self.bus = MessageBus()
        
        # Create real database connection
        self.supabase_client = SupabaseClient()
        self.attempted_opps_repo = AttemptedOpportunitiesGateway(self.supabase_client.client)

        # Create mock trade repository (since we don't need real trading)
        self.mock_trade_repo = MagicMock(spec=TradeGateway)

        # shared data
        # Create test opportunity
        self.opportunity = DUMMY_ARB_OPPORTUNITY_BUY_BOTH

        self.dummy_kalshi_order = KalshiOrder(
            **DUMMY_VALID_KALSHI_ORDER_RESPONSE['order']
        )
        self.dummy_poly_order = PolymarketOrder(
            **DUMMY_VALID_POLYMARKET_ORDER_RESPONSE
        )
        
        # Start the message bus
        self.bus_task = asyncio.create_task(self.bus.run())
        await asyncio.sleep(0.1)  # Give bus time to start

    async def asyncTearDown(self):
        """Clean up after test"""
        if hasattr(self, 'bus_task'):
            self.bus_task.cancel()
            try:
                await self.bus_task
            except asyncio.CancelledError:
                pass

    async def test_successful_trade_storage_increases_database_count(self):
        """Test that storing a trade result increases the database row count by 1"""
        # Create trade storage service with real database
        trade_storage = TradeStorage(
            bus=self.bus,
            trade_repo=self.mock_trade_repo,
            attempted_opportunities_repo=self.attempted_opps_repo,
            batch_size=1,  # Small batch for immediate processing
            flush_interval_seconds=1
        )

        # Get initial count from actual database
        starting_entries = self.attempted_opps_repo.get_attempted_opportunities()
        print(f"Initial database count: {len(starting_entries)}")

        
        # Create test trade result
        trade_result = ArbTradeResultReceived(
            category="buy_both",
            opportunity=self.opportunity,
            kalshi_order=self.dummy_kalshi_order,
            polymarket_order=self.dummy_poly_order
        )
        
        # Process the trade result
        await trade_storage.handle_trade_results_received(
            StoreTradeResults(arb_trade_results=trade_result)
        )
        
        # Wait for processing to complete
        await asyncio.sleep(0.5)
        
        # Get final count from actual database
        final_entries = self.attempted_opps_repo.get_attempted_opportunities()
        print(f"Final database count: {len(final_entries)}")
        
        # Verify that the count increased by exactly 1
        self.assertEqual(len(starting_entries) + 1, len(final_entries),
                        f"Database count should have increased by 1. Initial: {len(starting_entries)}, Final: {len(final_entries)}")
        
        # Optionally: Verify the specific record was created
        # You could add a method to fetch the latest record and verify its contents
        # latest_record = await self.attempted_opps_repo.get_latest_record()
        # if latest_record:
        #     self.assertEqual(latest_record.arbitrage_opportunity.market_id, "test_market_123")
        #     self.assertEqual(latest_record.category, "buy_both")
        #     self.assertTrue(latest_record.kalshi_trade_executed)
        #     self.assertTrue(latest_record.poly_trade_executed)

    async def test_succesful_trade_when_batch_size_reached(self):
        """Test that storing a trade result increases the database row count by batch size"""
        BATCH_SIZE = 3
        # Create trade storage service with real database
        trade_storage = TradeStorage(
            bus=self.bus,
            trade_repo=self.mock_trade_repo,
            attempted_opportunities_repo=self.attempted_opps_repo,
            batch_size=BATCH_SIZE,  # Small batch for immediate processing
            flush_interval_seconds=1
        )

        # Get initial count from actual database
        starting_entries = self.attempted_opps_repo.get_attempted_opportunities()
        print(f"Initial database count: {len(starting_entries)}")

        # Create test trade result
        trade_result = ArbTradeResultReceived(
            category="buy_both",
            opportunity=self.opportunity,
            kalshi_order=self.dummy_kalshi_order,
            polymarket_order=self.dummy_poly_order
        )

        # Process the trade result
        for i in range(BATCH_SIZE):
            await trade_storage.handle_trade_results_received(
                StoreTradeResults(arb_trade_results=trade_result)
            )
            # Wait for processing to complete
            await asyncio.sleep(0.5)

        # Get final count from actual database
        final_entries = self.attempted_opps_repo.get_attempted_opportunities()
        print(f"Final database count: {len(final_entries)}")

        # Verify that the count increased by exactly batch size
        self.assertEqual(len(starting_entries) + BATCH_SIZE, len(final_entries),
                         f"Database count should have increased by {BATCH_SIZE}. Initial: {len(starting_entries)}, Final: {len(final_entries)}")

    async def test_trades_placed_after_flush_interval_seconds(self):

        starting_entries = len(self.attempted_opps_repo.get_attempted_opportunities())

        BATCH_SIZE = 100 # purposefully large batch size
        # Create trade storage service with real database
        trade_storage = TradeStorage(
            bus=self.bus,
            trade_repo=self.mock_trade_repo,
            attempted_opportunities_repo=self.attempted_opps_repo,
            batch_size=BATCH_SIZE,  # Small batch for immediate processing
            flush_interval_seconds=1
        )

        # initialize sample trades

        trade_result_1 = ArbTradeResultReceived(
            category="buy_both_1",
            opportunity=self.opportunity,
            kalshi_order=self.dummy_kalshi_order,
            polymarket_order=self.dummy_poly_order
        )
        trade_result_2 = ArbTradeResultReceived(
            category="buy_both_2",
            opportunity=self.opportunity,
            kalshi_order=self.dummy_kalshi_order,
            polymarket_order=self.dummy_poly_order
        )

        trades_array = [trade_result_1, trade_result_2]
        trade_storage.trade_results = trades_array.copy()

        await trade_storage.start()

        await asyncio.sleep(3) # await flush tasks

        final_entries = len(self.attempted_opps_repo.get_attempted_opportunities())
        # Verify that the count increased by the length of the trade array
        self.assertEqual(starting_entries + len(trades_array), final_entries,
                         f"Database count should have increased by {len(trades_array)}. Initial: {starting_entries}, Final: {final_entries}")

    async def test_trades_stored_on_cancel(self):

        starting_entries = len(self.attempted_opps_repo.get_attempted_opportunities())

        BATCH_SIZE = 100  # purposefully large batch size
        # Create trade storage service with real database
        trade_storage = TradeStorage(
            bus=self.bus,
            trade_repo=self.mock_trade_repo,
            attempted_opportunities_repo=self.attempted_opps_repo,
            batch_size=BATCH_SIZE,
            flush_interval_seconds=30 * 60 # purposefully large wait time
        )

        # initialize sample trades

        trade_result = ArbTradeResultReceived(
            category="buy_both_1",
            opportunity=self.opportunity,
            kalshi_order=self.dummy_kalshi_order,
            polymarket_order=self.dummy_poly_order
        )

        trades_array = [trade_result]
        trade_storage.trade_results = trades_array.copy()

        await trade_storage.start()

        await trade_storage.handle_trade_results_received(
            StoreTradeResults(arb_trade_results=trade_result) # increases queue by another trade
        )

        entry_length_after_tasks_start = len(self.attempted_opps_repo.get_attempted_opportunities())

        self.assertEqual(starting_entries, entry_length_after_tasks_start, f"Database count should have not increased.")

        await trade_storage.stop()

        final_length = len(self.attempted_opps_repo.get_attempted_opportunities())

        self.assertEqual(starting_entries + 2, final_length,
                         f"Database count should have increased by 1. Initial: {starting_entries}, Final: {final_length}")