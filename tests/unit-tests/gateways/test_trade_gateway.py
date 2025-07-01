import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.kalshi import KalshiHttpClient
from app.clients.polymarket.clob_http import PolymClobHttpClient
from app.domain.primitives import KalshiSide, PolySide
from app.domain.types import KalshiOrder, PolymarketOrder
from app.gateways.trade_gateway import TradeGateway
from tests.sample_data import DUMMY_VALID_KALSHI_ORDER_RESPONSE, DUMMY_VALID_POLYMARKET_ORDER_RESPONSE


class TestTradeGateways(unittest.TestCase):
    def setUp(self):
        self.mock_kalshi: KalshiHttpClient = AsyncMock(spec=KalshiHttpClient)
        self.mock_poly : PolymClobHttpClient = AsyncMock(spec=PolymClobHttpClient)
        pass

    def tearDown(self):
        pass

    async def test_place_kalshi_market_order_awaits_create_order(self):
        # Setup
        self.mock_kalshi.create_order.return_value = DUMMY_VALID_KALSHI_ORDER_RESPONSE

        trade_gateway = TradeGateway(self.mock_kalshi, MagicMock())

        # Patch process_raw_kalshi_order to assert input is dict, not coroutine
        with patch.object(
                trade_gateway, "process_raw_kalshi_order", wraps=trade_gateway.process_raw_kalshi_order
        ) as mock_process:
            args, kwargs = mock_process.call_args
            raw_data_passed = args[0]
            # Act
            result = await trade_gateway.place_kalshi_market_order(
                ticker="TICKER",
                side=KalshiSide.YES,
                count=10,
                client_order_id="abc123",
                action="sell"
            )

            # Assert
            self.assertIsInstance(result, KalshiOrder)

            self.assertFalse(
                asyncio.iscoroutine(raw_data_passed),
                "You forgot to await create_order() — process_raw_kalshi_order got coroutine instead of dict"
            )
    async def test_place_polymarket_market_order_awaits_create_order(self):
        # Setup
        self.mock_poly.place_order.return_value = DUMMY_VALID_POLYMARKET_ORDER_RESPONSE

        trade_gateway = TradeGateway(MagicMock(), self.mock_poly)

        # Patch process_raw_kalshi_order to assert input is dict, not coroutine
        with patch.object(
                trade_gateway, "process_raw_polymarket_order", wraps=trade_gateway.process_raw_polymarket_order
        ) as mock_process:
            args, kwargs = mock_process.call_args
            raw_data_passed = args[0]
            # Act
            result = await trade_gateway.place_polymarket_market_order(
                token_id="test",
                side=PolySide.SELL,
                size=10,
            )

            # Assert
            self.assertIsInstance(result, PolymarketOrder)

            self.assertFalse(
                asyncio.iscoroutine(raw_data_passed),
                "You forgot to await create_order() — process_raw_kalshi_order got coroutine instead of dict"
            )