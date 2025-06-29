import asyncio
import logging
from typing import List, Coroutine

from app.ingestion.clob_wss import PolymarketWebSocketClient
from app.domain.events import OrderBookSnapshotReceived, OrderBookDeltaReceived, MarketBookUpdated, \
    ArbitrageOpportunityFound, ExecuteTrade, StoreTradeResults, TradeFailed, TradeAttemptCompleted
from app.services.execution import executor
from app.ingestion.kalshi_wss_client import KalshiWebSocketClient
from app.markets.manager import MarketManager
from app.message_bus import MessageBus
from app.gateways.trade_gateway import TradeGateway
from app.services.operational.balance_service import BalanceService
from app.services.unwind import unwinder
from app.strategies import arbitrage_monitor
from app.services.trade_storage import TradeStorage

logger = logging.getLogger(__name__)


def bootstrap(
        bus: MessageBus,
        market_manager: MarketManager,
        balance_service: BalanceService,
        kalshi_client: KalshiWebSocketClient,
        polymarket_client: PolymarketWebSocketClient,
        markets_config: List[dict],
        trade_repo: TradeGateway,
        trade_storage: TradeStorage,
        dry_run: bool,
        shutdown_event: asyncio.Event,
) -> List[Coroutine]:
    """
    The Composition Root. Wires together the application's components.

    Returns:
        A list of long-running coroutines (tasks) that should be run by the orchestrator.
    """
    logger.info("Bootstrapping application...")

    # Initialize dependencies for the service-layer handlers
    arbitrage_monitor.initialize_arbitrage_handlers(
        market_manager=market_manager,
        bus=bus,
        markets_config=markets_config,
        wallets=balance_service.get_wallets(),
    )
    executor.initialize_trade_executor(
        trade_repo=trade_repo,
        dry_run=dry_run,
        bus=bus,
        shutdown_event=shutdown_event,
    )
    unwinder.initialize_unwinder(
        trade_gateway=trade_repo,
        bus=bus,
        shutdown_event=shutdown_event,
    )

    # Start background task for service
    # Subscribe handlers to events and commands on the message bus
    bus.subscribe(OrderBookSnapshotReceived, market_manager._handle_snapshot)
    bus.subscribe(OrderBookDeltaReceived, market_manager._handle_delta)
    bus.subscribe(MarketBookUpdated, arbitrage_monitor.handle_market_book_update)
    bus.subscribe(ArbitrageOpportunityFound, arbitrage_monitor.handle_arbitrage_opportunity_found)
    bus.subscribe(ExecuteTrade, executor.handle_execute_trade)
    bus.subscribe(StoreTradeResults, trade_storage.handle_trade_results_received)
    bus.subscribe(TradeFailed, unwinder.handle_trade_failed)
    bus.subscribe(TradeAttemptCompleted, arbitrage_monitor.handle_trade_attempt_completed)

    # Configure clients to publish to the bus
    kalshi_client.set_message_bus(bus)
    polymarket_client.set_message_bus(bus)

    # Return the primary, long-running tasks for the orchestrator to run
    return [
        kalshi_client.connect_forever(),
        polymarket_client.connect_forever(channel_path=polymarket_client.MARKET_PATH),
        bus.run(),
    ]
