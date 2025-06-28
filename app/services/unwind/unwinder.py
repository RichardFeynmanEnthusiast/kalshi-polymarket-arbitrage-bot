import logging
import uuid

from app.domain.events import TradeFailed
from app.domain.primitives import Platform, KalshiSide, PolySide
from app.domain.types import TradeDetails
from app.gateways.trade_gateway import TradeGateway
from app.message_bus import MessageBus

logger = logging.getLogger(__name__)

_trade_gateway: TradeGateway
_bus: MessageBus

def initialize_unwinder(trade_gateway: TradeGateway, bus: MessageBus):
    """
    Injects dependencies into the unwinder module.
    """
    global _trade_gateway, _bus
    _trade_gateway = trade_gateway
    _bus = bus
    logger.info("Unwinder handlers initialized.")

async def handle_trade_failed(event: TradeFailed):
    """
    Handles the unwinding of a trade by listening for a TradeFailed event
    and placing an opposing order for the successful leg.
    """
    logger.info(f"Unwinder processing TradeFailed event for opportunity: {event.opportunity.market_id}")
    successful_leg = event.successful_leg

    if successful_leg.platform == Platform.KALSHI:
        await _unwind_kalshi_trade(successful_leg)
    elif successful_leg.platform == Platform.POLYMARKET:
        await _unwind_polymarket_trade(successful_leg)

async def _unwind_kalshi_trade(successful_leg: TradeDetails):
    """
    Unwinds a successful Kalshi trade by placing an opposing market 'sell' order.
    """
    side_to_unwind = KalshiSide.YES if successful_leg.kalshi_side == 'yes' else KalshiSide.NO
    contracts_to_sell = int(successful_leg.trade_size)

    logger.warning(f"EMERGENCY UNWIND: Placing Kalshi MARKET SELL for {contracts_to_sell} of {successful_leg.kalshi_ticker} on {side_to_unwind.value} side.")
    try:
        await _trade_gateway.place_kalshi_market_order(
            ticker=successful_leg.kalshi_ticker,
            side=side_to_unwind,
            count=contracts_to_sell,
            client_order_id=str(uuid.uuid4()),
            action="sell"
        )
        logger.info("Successfully placed Kalshi emergency unwind order.")
    except Exception as e:
        logger.error(f"Failed to place Kalshi emergency unwind order: {e}", exc_info=True)


async def _unwind_polymarket_trade(successful_leg: TradeDetails):
    """
    Unwinds a successful Polymarket trade by placing an opposing market 'sell' order.
    """
    size_to_sell = float(successful_leg.trade_size)

    logger.warning(f"EMERGENCY UNWIND: Placing Polymarket MARKET SELL for {size_to_sell} of token {successful_leg.polymarket_token_id}")
    try:
        await _trade_gateway.place_polymarket_market_order(
            token_id=successful_leg.polymarket_token_id,
            size=size_to_sell,
            side=PolySide.SELL
        )
        logger.info("Successfully placed Polymarket emergency unwind order.")
    except Exception as e:
        logger.error(f"Failed to place Polymarket emergency unwind order: {e}", exc_info=True)