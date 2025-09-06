import json
import unittest
from unittest.mock import MagicMock, AsyncMock

from app.ingestion.kalshi_wss_client import KalshiWebSocketClient


class TestKalshiWebSocketClient(unittest.IsolatedAsyncioTestCase):
    """
    Unit tests for the KalshiWebSocketClient, focusing on its ability to
    handle subscriptions and process messages.
    """

    def setUp(self):
        """Set up a client instance and its dependencies for each test"""
        # Create client instance
        self.private_key = MagicMock()
        self.bus = MagicMock()
        self.bus.publish = AsyncMock()
        self.client = KalshiWebSocketClient(
            key_id="test_key",
            private_key=self.private_key
        )
        self.client.set_message_bus(self.bus)

        # Configure client with two markets
        self.markets_config = [
            {'id': 'market-1-id', 'kalshi_ticker': 'MARKET-A'},
            {'id': 'market-2-id', 'kalshi_ticker': 'MARKET-B'}
        ]
        self.client.set_market_config(self.markets_config)

        # Mock the websocket connection object
        self.client._ws = AsyncMock()
        self.client.logger = MagicMock()

    def _create_snapshot_message(self, ticker: str, seq: int) -> str:
        """Helper to create a valid Kalshi snapshot message string."""
        return json.dumps({
            "type": "orderbook_snapshot",
            "seq": seq,
            "msg": {
                "market_ticker": ticker,
                "yes": [[90, 10], [80, 20]],
                "no": [[15, 30], [25, 40]]
            }
        })

    def _create_delta_message(self, ticker: str, side: str, price: int, delta: int, seq: int) -> str:
        """Helper to create a valid Kalshi delta message string."""
        return json.dumps({
            "type": "orderbook_delta",
            "seq": seq,
            "msg": {
                "market_ticker": ticker,
                "side": side,
                "price": price,  # price in cents
                "delta": delta
            }
        })

    async def test_set_market_config_initializ
