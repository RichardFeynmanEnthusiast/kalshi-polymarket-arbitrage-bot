import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

from app.domain.events import ArbitrageTradeSuccessful
from app.orchestration.fletcher_orchestrator import FletcherOrchestrator


class TestFletcherOrchestrator(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for the FletcherOrchestrator, focusing on its lifecycle management
    for soft resets and hard shutdowns.
    """

    def setUp(self):
        """Set up all necessary mocks for the orchestrator's dependencies."""

        # This function will create a new, pending Future for each call,
        # simulating independent, long-running tasks.
        async def new_long_running_task(*args, **kwargs):
            await asyncio.Future()

        self.mock_poly_wss = MagicMock()
        self.mock_poly_wss.connect_forever = AsyncMock(side_effect=new_long_running_task)
        self.mock_kalshi_wss = MagicMock()
        self.mock_kalshi_wss.connect_forever = AsyncMock(side_effect=new_long_running_task)

        self.mock_matches_repo = MagicMock()
        mock_pair = MagicMock()
        mock_pair.poly_id = '1'
        self.mock_matches_repo.get_market_pairs.return_value = [mock_pair]

        self.mock_poly_gateway = MagicMock()
        self.mock_poly_gateway.get_markets_by_id = AsyncMock(return_value=[[{'id': '1'}]])

        self.mock_kalshi_gateway = MagicMock()
        self.mock_kalshi_gateway.get_markets_by_id = AsyncMock(return_value=[{'ticker': 'TICKER'}])

        self.mock_bus = MagicMock()
        self.subscription_event = asyncio.Event()
        self.successful_trade_handler = None

        def capture_handler(event_type, handler):
            if event_type == ArbitrageTradeSuccessful:
                self.successful_trade_handler = handler
                self.subscription_event.set()

        self.mock_bus.subscribe.side_effect = capture_handler
        self.mock_bus.run = AsyncMock(side_effect=new_long_running_task)

        self.mock_market_manager = MagicMock()
        self.mock_market_manager.reset = MagicMock()

        self.mock_trade_storage = MagicMock()
        self.mock_trade_storage.start = AsyncMock(side_effect=new_long_running_task)

        self.bootstrap_patcher = patch('app.orchestration.fletcher_orchestrator.bootstrap')
        self.mock_bootstrap = self.bootstrap_patcher.start()
        # The bootstrap mock should return the coroutines themselves, not their results
        self.mock_bootstrap.return_value = [
            self.mock_kalshi_wss.connect_forever(),
            self.mock_poly_wss.connect_forever(),
            self.mock_bus.run()
        ]

        self.market_base_patcher = patch('app.orchestration.fletcher_orchestrator.MatchedMarketBase')
        self.mock_market_base = self.market_base_patcher.start()
        self.mock_market_base.from_markets.return_value = MagicMock(
            poly_clobTokenIds=['1', '2'], kalshi_ticker='TICKER'
        )
        self.kalshi_market_patcher = patch('app.orchestration.fletcher_orchestrator.KalshiMarket')
        self.mock_kalshi_market = self.kalshi_market_patcher.start()
        self.mock_kalshi_market.return_value = MagicMock(status='active')
        self.polymarket_market_patcher = patch('app.orchestration.fletcher_orchestrator.PolymarketMarket')
        self.mock_polymarket_market = self.polymarket_market_patcher.start()
        self.mock_polymarket_market.return_value = MagicMock(active=True)

        self.orchestrator = FletcherOrchestrator(
            poly_wss_client=self.mock_poly_wss,
            kalshi_wss=self.mock_kalshi_wss,
            matches_repo=self.mock_matches_repo,
            attempted_opps_repo=MagicMock(),
            trade_repo=MagicMock(),
            poly_gateway=self.mock_poly_gateway,
            kalshi_gateway=self.mock_kalshi_gateway,
            bus=self.mock_bus,
            printer=None,
            trade_storage=self.mock_trade_storage,
            market_manager=self.mock_market_manager,
        )

    def tearDown(self):
        """Stop all patches."""
        self.bootstrap_patcher.stop()
        self.market_base_patcher.stop()
        self.kalshi_market_patcher.stop()
        self.polymarket_market_patcher.stop()

    async def test_successful_trade_triggers_soft_reset(self):
        """
        Verify that a successful trade triggers the soft reset procedure
        without stopping the orchestrator.
        """
        # Patch asyncio.sleep to avoid long waits in the test
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            orchestrator_task = asyncio.create_task(
                self.orchestrator.run_live_trading_service(market_tuples=[('1', 'TICKER')])
            )

            try:
                await asyncio.wait_for(self.subscription_event.wait(), timeout=1)
            except asyncio.TimeoutError:
                orchestrator_task.cancel()
                self.fail("Orchestrator did not subscribe the successful trade handler in time.")

            # Simulate the successful trade event
            self.assertIsNotNone(self.successful_trade_handler)
            await self.successful_trade_handler(ArbitrageTradeSuccessful())

            # Allow the handler to proceed past the sleeps
            await asyncio.sleep(0)

            # Assert that the reset actions occurred
            self.mock_market_manager.reset.assert_called_once()
            self.assertEqual(self.mock_kalshi_wss.connect_forever.call_count, 2)
            self.assertEqual(self.mock_poly_wss.connect_forever.call_count, 2)

            # Assert that the orchestrator is still running after the soft reset.
            self.assertTrue(self.orchestrator._running, "Orchestrator should still be running after a soft reset.")

            # Clean up the test by cancelling the main task
            orchestrator_task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await orchestrator_task

    async def test_shutdown_event_triggers_hard_shutdown(self):
        """
        Verify that setting the shutdown_event correctly triggers a full, hard
        shutdown of all orchestrator tasks.
        """
        orchestrator_task = asyncio.create_task(
            self.orchestrator.run_live_trading_service(market_tuples=[('1', 'TICKER')])
        )
        # Give the orchestrator a moment to set its _running flag to True
        await asyncio.sleep(0.01)
        self.assertTrue(self.orchestrator._running)

        # Trigger the shutdown
        self.orchestrator.shutdown_event.set()

        # Await the orchestrator task, which should now complete gracefully
        try:
            await asyncio.wait_for(orchestrator_task, timeout=1)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

        # Assert that the orchestrator's state is now "not running".
        self.assertFalse(self.orchestrator._running, "Orchestrator should be stopped after shutdown event.")


if __name__ == '__main__':
    unittest.main()
