import asyncio
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock
import uuid

from app.domain.primitives import KalshiSide
from app.domain.types import KalshiOrder
from app.gateways.trade_gateway import TradeGateway


class TestTradeRepository(unittest.TestCase):

    def setUp(self):
        """
        Set up mock clients and the repository instance before each test.
        This is now consistent with the other test files.
        """
        self.mock_kalshi_http = AsyncMock()
        self.mock_polymarket_http = MagicMock()
        self.trade_repository = TradeGateway(self.mock_kalshi_http, self.mock_polymarket_http)
        self.client_order_id = str(uuid.uuid4())

    def test_place_kalshi_order_happy_path(self):
        """
        Tests that place_kalshi_order calls the underlying client with correct parameters.
        """
        asyncio.run(self.async_test_place_kalshi_order_happy_path())

    async def async_test_place_kalshi_order_happy_path(self):
        # Arrange
        ticker = "TEST-TICKER-24"
        price_in_cents = 68
        expected_response_data = {
            'order': {
                'ticker': ticker,
                'status': 'resting',
                'yes_price': price_in_cents
            }
        }
        self.mock_kalshi_http.create_order.return_value = expected_response_data

        # Act
        await self.trade_repository.place_kalshi_order(
            ticker=ticker,
            side=KalshiSide.YES,
            count=10,
            price_in_cents=price_in_cents,
            client_order_id=self.client_order_id
        )

        # Assert
        self.mock_kalshi_http.create_order.assert_called_once_with(
            action="buy",
            side="yes",
            type="limit",
            ticker=ticker,
            count=10,
            client_order_id=self.client_order_id,
            yes_price=price_in_cents
        )

    def test_kalshi_create_order_raises_exception(self):
        """
        Tests that an exception from the client is propagated.
        """
        asyncio.run(self.async_test_kalshi_create_order_raises_exception())

    async def async_test_kalshi_create_order_raises_exception(self):
        # Arrange
        from requests.exceptions import HTTPError
        self.mock_kalshi_http.create_order.side_effect = HTTPError("400 Client Error: Bad Request")

        # Act & Assert
        with self.assertRaises(HTTPError):
            await self.trade_repository.place_kalshi_order(
                ticker="TEST-TICKER-24",
                side=KalshiSide.NO,
                count=1,
                price_in_cents=30,
                client_order_id=self.client_order_id
            )

    def test_process_raw_kalshi_order_returns_valid_object(self):
        """
        Tests that the raw dictionary from Kalshi is correctly parsed into a KalshiOrder object.
        """
        # Arrange
        raw_data = {
            'order': {
                'order_id': '0155b151-0659-42a1-af85-52096518e4e6',
                'ticker': 'TEST-TICKER-24',
                'status': 'executed',
                'side': 'yes',
            }
        }

        # Act
        result = self.trade_repository.process_raw_kalshi_order(raw_data, trade_size=Decimal("1.00"))

        # Assert
        self.assertIsInstance(result, KalshiOrder)
        self.assertEqual(result.status, 'executed')
        self.assertEqual(result.ticker, 'TEST-TICKER-24')


if __name__ == '__main__':
    unittest.main()