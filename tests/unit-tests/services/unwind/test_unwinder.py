import asyncio
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch

from app.domain.events import TradeFailed, TradeAttemptCompleted
from app.domain.primitives import Platform, KalshiSide, PolySide
from app.domain.types import TradeDetails
from app.services.unwind import unwinder
from tests.sample_data import DUMMY_ARB_OPPORTUNITY_BUY_BOTH


class TestUnwinder(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        """
        This method is called before each test function is executed.
        """
        # Mock trade gateway
        self.trade_gateway = MagicMock()
        self.trade_gateway.place_kalshi_market_order = AsyncMock()
        self.trade_gateway.place_polymarket_market_order = AsyncMock()

        # Mock message bus
        self.bus = MagicMock()
        self.bus.publish = AsyncMock()

        # Mock shutdown event
        self.shutdown_event = MagicMock(spec=asyncio.Event)
        self.shutdown_event.set = MagicMock()

        unwinder.initialize_unwinder(
            trade_gateway=self.trade_gateway,
            bus=self.bus,
            shutdown_event=self.shutdown_event
        )

        # Import stub
        self.dummy_opportunity = DUMMY_ARB_OPPORTUNITY_BUY_BOTH

    def _create_trade_failed_event(
            self,
            successful_platform: Platform,
            failed_platform: Platform,
            trade_size: Decimal = Decimal("25"),
            kalshi_side: str = None,
            polymarket_token_id: str = None
    ) -> TradeFailed:
        """
        Helper function to create a TradeFailed event.
        """
        successful_leg = TradeDetails(
            platform=successful_platform,
            trade_size=trade_size,
            order_id="order-123",
            kalshi_ticker="TICKER-69",
            kalshi_side=kalshi_side,
            polymarket_token_id=polymarket_token_id
        )

        return TradeFailed(
            failed_leg_platform=failed_platform,
            successful_leg=successful_leg,
            opportunity=self.dummy_opportunity,
            error_message=f"{failed_platform.value} trade failed."
        )

    async def test_unwind_successful_kalshi_leg_triggers_shutdown(self):
        """
        Verify that a successful Kalshi 'yes' leg is unwound correctly.
        """
        # Arrange
        trade_failed_event = self._create_trade_failed_event(
            successful_platform=Platform.KALSHI,
            failed_platform=Platform.POLYMARKET,
            kalshi_side="yes"
        )

        # Act
        await unwinder.handle_trade_failed(trade_failed_event)

        # Assert
        self.trade_gateway.place_kalshi_market_order.assert_called_once()
        self.trade_gateway.place_polymarket_market_order.assert_not_called()

        call_args, call_kwargs = self.trade_gateway.place_kalshi_market_order.call_args

        self.assertEqual(call_kwargs['ticker'], "TICKER-69")
        self.assertEqual(call_kwargs['count'], 25)
        self.assertEqual(call_kwargs['action'], "sell")
        self.assertEqual(call_kwargs['side'], KalshiSide.YES)


    async def test_unwind_successful_kalshi_no_leg(self):
        """
        Verify that a successful Kalshi 'no' leg is unwound correctly.
        """
        # Arrange
        trade_failed_event = self._create_trade_failed_event(
            successful_platform=Platform.KALSHI,
            failed_platform=Platform.POLYMARKET,
            trade_size=Decimal("50"),
            kalshi_side="no"
        )

        # Act
        await unwinder.handle_trade_failed(trade_failed_event)

        # Assert
        self.trade_gateway.place_kalshi_market_order.assert_called_once()
        self.trade_gateway.place_polymarket_market_order.assert_not_called()

        call_args, call_kwargs = self.trade_gateway.place_kalshi_market_order.call_args

        self.assertEqual(call_kwargs['ticker'], "TICKER-69")
        self.assertEqual(call_kwargs['count'], 50)
        self.assertEqual(call_kwargs['action'], "sell")
        self.assertEqual(call_kwargs['side'], KalshiSide.NO)

    async def test_unwind_successful_polymarket_leg(self):
        """
        Verify that a successful Polymarket leg is unwound correctly.
        """
        # Arrange
        trade_failed_event = self._create_trade_failed_event(
            successful_platform=Platform.POLYMARKET,
            failed_platform=Platform.KALSHI,
            trade_size=Decimal("100.5"),
            polymarket_token_id="0xPOLYTOKEN123"
        )

        # Act
        await unwinder.handle_trade_failed(trade_failed_event)

        # Assert
        self.trade_gateway.place_polymarket_market_order.assert_called_once()
        self.trade_gateway.place_kalshi_market_order.assert_not_called()

        call_args, call_kwargs = self.trade_gateway.place_polymarket_market_order.call_args

        self.assertEqual(call_kwargs['token_id'], "0xPOLYTOKEN123")
        self.assertEqual(call_kwargs['size'], 100.5)
        self.assertEqual(call_kwargs['side'], PolySide.SELL)

    @patch('app.services.unwind.unwinder.logger.error')
    async def test_unwind_triggers_shutdown_even_if_unwind_fails(self, mock_logger_error):
        """
        Verify that the shutdown event is triggered even if the unwind
        trade itself fails.
        """
        # Arrange
        self.trade_gateway.place_kalshi_market_order.side_effect = Exception("Network Error")

        trade_failed_event = self._create_trade_failed_event(
            successful_platform=Platform.KALSHI,
            failed_platform=Platform.POLYMARKET,
            kalshi_side="yes"
        )

        # Act
        await unwinder.handle_trade_failed(trade_failed_event)

        # Assert
        self.trade_gateway.place_kalshi_market_order.assert_called_once()
        mock_logger_error.assert_called_once()
        self.bus.publish.assert_not_called()
        self.shutdown_event.set.assert_called_once()


if __name__ == '__main__':
    unittest.main()