import asyncio
import logging
import uuid
from decimal import Decimal

from app.domain.events import ExecuteTrade, ArbTradeResultReceived, StoreTradeResults, TradeFailed, \
    TradeAttemptCompleted
from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform, KalshiSide, PolySide
from app.domain.types import TradeDetails
from app.gateways.trade_gateway import TradeGateway
from app.message_bus import MessageBus

# --- Module Setup ---

logger = logging.getLogger(__name__)

# Dependencies are stored at the module level and injected once at startup.
_trade_repo: TradeGateway
_bus: MessageBus
_dry_run: bool = False
_max_trade_size: int = 50


def initialize_trade_executor(
        trade_repo: TradeGateway,
        bus: MessageBus,
        dry_run: bool = False,
        max_trade_size: int = 50,
):
    """Injects dependencies into the trade execution handlers module."""
    global _trade_repo, _dry_run, _max_trade_size, _bus
    _bus = bus
    _trade_repo = trade_repo
    _dry_run = dry_run
    _max_trade_size = max_trade_size
    if _dry_run:
        logger.warning("TradeExecutor is in DRY RUN mode. No real orders will be placed.")
    logger.info("Trade executor handlers initialized.")


# --- Command Handler ---

async def handle_execute_trade(command: ExecuteTrade):
    """
    This is the command handler for executing a trade. It contains the logic
    from the old execute_buy_both_arbitrage method.
    """
    opportunity = command.opportunity
    log_prefix = "[DRY RUN] " if _dry_run else ""
    trade_size = int(min(Decimal(_max_trade_size), opportunity.potential_trade_size))

    if trade_size <= 0:
        logger.info(f"Arbitrage opportunity for {opportunity.market_id} found, but with zero potential trade size.")
        # If we don't trade, we must unlock the monitor
        await _bus.publish(TradeAttemptCompleted())
        return

    logger.info(
        f"{log_prefix}Executing arbitrage",
        extra={
            "market_id": opportunity.market_id,
            "trade_size": trade_size,
            "buy_yes_platform": opportunity.buy_yes_platform.value,
            "buy_no_platform": opportunity.buy_no_platform.value,
        }
    )

    if opportunity.buy_yes_platform == Platform.KALSHI:
        kalshi_task = _execute_kalshi_buy_yes(opportunity, trade_size)
        polymarket_task = _execute_polymarket_buy_no(opportunity, trade_size)
    else:
        kalshi_task = _execute_kalshi_buy_no(opportunity, trade_size)
        polymarket_task = _execute_polymarket_buy_yes(opportunity, trade_size)

    kalshi_result, polymarket_result = await asyncio.gather(kalshi_task, polymarket_task, return_exceptions=True)

    # Publish arbitrage trade results to the bus
    await handle_trade_response(kalshi_result, polymarket_result, category="buy both", opportunity=opportunity)


# --- Execution Logic ---

async def _execute_kalshi_buy_yes(opportunity: ArbitrageOpportunity, size: int):
    price_in_cents = int(opportunity.buy_yes_price * 100)
    if _dry_run:
        log_msg = f"Would place Kalshi order: BUY YES @ {opportunity.buy_yes_price} on {opportunity.kalshi_ticker}"
        logger.info(log_msg)
        return {"status": "dry_run", "ticker": opportunity.kalshi_ticker}

    logger.info(f"Placing Kalshi order: BUY YES @ {opportunity.buy_yes_price}")
    return await _trade_repo.place_kalshi_order(
        ticker=opportunity.kalshi_ticker, side=KalshiSide.YES,
        count=size, price_in_cents=price_in_cents, client_order_id=str(uuid.uuid4())
    )


async def _execute_kalshi_buy_no(opportunity: ArbitrageOpportunity, size: int):
    price_in_cents = int(opportunity.buy_no_price * 100)
    if _dry_run:
        log_msg = f"Would place Kalshi order: BUY NO @ {opportunity.buy_no_price} on {opportunity.kalshi_ticker}"
        logger.info(log_msg)
        return {"status": "dry_run", "ticker": opportunity.kalshi_ticker}

    logger.info(f"Placing Kalshi order: BUY NO @ {opportunity.buy_no_price}")
    return await _trade_repo.place_kalshi_order(
        ticker=opportunity.kalshi_ticker, side=KalshiSide.NO,
        count=size, price_in_cents=price_in_cents, client_order_id=str(uuid.uuid4())
    )


async def _execute_polymarket_buy_yes(opportunity: ArbitrageOpportunity, size: int):
    if _dry_run:
        log_msg = f"Would place Polymarket order: BUY YES @ {opportunity.buy_yes_price} on token {opportunity.polymarket_yes_token_id}"
        logger.info(log_msg)
        return {"status": "dry_run", "details": log_msg}

    logger.info(f"Placing Polymarket order: BUY YES @ {opportunity.buy_yes_price}")
    return await _trade_repo.place_polymarket_order(
        token_id=opportunity.polymarket_yes_token_id, price=opportunity.buy_yes_price,
        size=float(size), side=PolySide.BUY
    )


async def _execute_polymarket_buy_no(opportunity: ArbitrageOpportunity, size: int):
    if _dry_run:
        log_msg = f"Would place Polymarket order: BUY NO @ {opportunity.buy_no_price} on token {opportunity.polymarket_no_token_id}"
        logger.info(log_msg)
        return {"status": "dry_run", "details": log_msg}

    logger.info(f"Placing Polymarket order: BUY NO @ {opportunity.buy_no_price}")
    return await _trade_repo.place_polymarket_order(
        token_id=opportunity.polymarket_no_token_id, price=opportunity.buy_no_price,
        size=float(size), side=PolySide.BUY
    )


async def handle_trade_response(kalshi_result, polymarket_result, category, opportunity: ArbitrageOpportunity):
    """
    This handler processes the data and publishes the processed data to the bus.
    """
    print("handle trade response called")
    is_kalshi_error = isinstance(kalshi_result, Exception)
    is_polymarket_error = isinstance(polymarket_result, Exception)

    # Store results in database
    arb_trade_result = ArbTradeResultReceived(
        category=category,
        opportunity=opportunity,
        kalshi_order=None if is_kalshi_error else kalshi_result,
        polymarket_order=None if is_polymarket_error else polymarket_result,
        kalshi_error_message=str(kalshi_result) if is_kalshi_error else None,
        polymarket_error=str(polymarket_result) if is_polymarket_error else None
    )
    await store_trade(StoreTradeResults(arb_trade_results=arb_trade_result))

    # Unwind Logic
    if is_kalshi_error and not is_polymarket_error:
        logger.warning("Kalshi trade leg failed, Polymarket succeeded. Triggering unwind.")
        successful_leg = TradeDetails(
            platform=Platform.POLYMARKET,
            trade_size=polymarket_result.trade_size,
            order_id=polymarket_result.id,
            polymarket_token_id=polymarket_result.token_id
        )
        event = TradeFailed(
            failed_leg_platform=Platform.KALSHI,
            successful_leg=successful_leg,
            opportunity=opportunity,
            error_message=str(kalshi_result)
        )
        await publish_trade_failed(event)

    elif not is_kalshi_error and is_polymarket_error:
        logger.warning("Polymarket trade leg failed, Kalshi succeeded. Triggering unwind.")
        successful_leg = TradeDetails(
            platform=Platform.KALSHI,
            trade_size=kalshi_result.trade_size,
            order_id=kalshi_result.order_id,
            kalshi_ticker=kalshi_result.ticker,
            kalshi_side=kalshi_result.side
        )
        event = TradeFailed(
            failed_leg_platform=Platform.POLYMARKET,
            successful_leg=successful_leg,
            opportunity=opportunity,
            error_message=str(polymarket_result)
        )
        await publish_trade_failed(event)

    # Signal that the entire trade execution process is complete, unlocking the arbitrage monitor
    await _bus.publish(TradeAttemptCompleted())


async def publish_trade_failed(event: TradeFailed):
    """
    This helper informs the message bus that a trade leg has failed.
    """
    logger.warning(
        f"Publishing TradeFailed event. Failed leg: {event.failed_leg_platform.value}, "
        f"Successful leg: {event.successful_leg.platform.value}."
    )
    await _bus.publish(event)


async def store_trade(command: StoreTradeResults):
    """
    This handler informs the message bus that the trade results are ready to be stored.
    """
    logger.info(f"Handling Arbitrage Trade Results for {command.arb_trade_results}. Issuing StoreTradeResults command.")
    await _bus.publish(command)
