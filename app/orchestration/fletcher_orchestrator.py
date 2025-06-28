import asyncio
import logging
from typing import Dict, List, Coroutine, Optional

from app.bootstrap import bootstrap
from app.domain.events import ArbitrageTradeSuccessful
from app.ingestion.clob_wss import PolymarketWebSocketClient
from app.domain.models.match_models import MarketPair, MatchedMarketBase
from app.domain.models.platform_models import PolymarketMarket, KalshiMarket
from app.gateways.kalshi_gateway import KalshiGateway
from app.gateways.polymarket_gateway import PolymarketGateway
from app.ingestion.kalshi_wss_client import KalshiWebSocketClient
from app.markets.manager import MarketManager
from app.message_bus import MessageBus
from app.repositories.matches_repository import MatchesRepository
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.gateways.trade_gateway import TradeGateway
from app.services.operational.diagnostic_printer import DiagnosticPrinter
from app.services.trade_storage import TradeStorage


class FletcherOrchestrator:
    """
    The main application orchestrator. It configures the markets,
    bootstraps the core services, and manages the runtime lifecycle of all tasks.
    """

    def __init__(
        self,
        poly_wss_client: PolymarketWebSocketClient,
        kalshi_wss: KalshiWebSocketClient,
        matches_repo: MatchesRepository,
        attempted_opps_repo: AttemptedOpportunitiesGateway,
        trade_repo: TradeGateway,
        poly_gateway: PolymarketGateway,
        kalshi_gateway: KalshiGateway,
        bus: MessageBus,
        printer: Optional[DiagnosticPrinter],
        trade_storage: TradeStorage,
        market_manager: MarketManager,
    ):
        self.logger = logging.getLogger(__name__)
        # --- Dependencies ---
        self.matches_repo = matches_repo
        self.attempted_opps_repo = attempted_opps_repo
        self.trade_repo = trade_repo
        self.poly_wss_client = poly_wss_client
        self.kalshi_wss = kalshi_wss
        self.poly_gateway = poly_gateway
        self.kalshi_gateway = kalshi_gateway
        self.bus = bus
        self.printer = printer
        self.trade_storage = trade_storage
        # Use the provided MarketManager instance, don't create a new one.
        self.market_manager = market_manager

        # --- State ---
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self.markets_config: List[Dict] = []
        self.market_pairs: List[MarketPair] = []
        self.cool_down_seconds: int = 5
        self.shutdown_event = asyncio.Event()

    async def run_live_trading_service(self, market_tuples: List[tuple], dry_run: bool = True, cool_down_seconds: int = 5):
        """The main entry point to configure and run the application."""
        self.cool_down_seconds = cool_down_seconds

        # Step 1: Dynamically configure markets using gateways
        await self._configure_markets(market_tuples)

        # Step 2: The Bootstrap process configures and returns the core coroutines
        core_coroutines = bootstrap(
            bus=self.bus,
            market_manager=self.market_manager,
            kalshi_client=self.kalshi_wss,
            polymarket_client=self.poly_wss_client,
            markets_config=self.markets_config,
            trade_repo=self.trade_repo,
            trade_storage=self.trade_storage,
            dry_run=dry_run,
            shutdown_event=self.shutdown_event,
        )

        self.bus.subscribe(ArbitrageTradeSuccessful, self._handle_successful_trade_and_reset)

        # Step 3: Start and manage the application tasks
        await self._start(core_coroutines)

    async def _handle_successful_trade_and_reset(self, event: ArbitrageTradeSuccessful):
        """
        Coordinates a "soft reset" of the application after a successful trade,
        including a cool-down period.
        """
        self.logger.info(
            f"Successful trade detected. Initiating {self.cool_down_seconds}-second cool-down and reset."
        )

        # 1. Stop current WebSocket listeners by cancelling their tasks
        self.logger.info("Stopping WebSocket listeners...")
        if "kalshi_connect" in self._tasks and not self._tasks["kalshi_connect"].done():
            self._tasks["kalshi_connect"].cancel()
        if "poly_connect" in self._tasks and not self._tasks["poly_connect"].done():
            self._tasks["poly_connect"].cancel()

        # Give a moment for the cancellations to be processed
        await asyncio.sleep(2)

        # 2. Enforce cool-down period
        self.logger.info(f"Beginning {self.cool_down_seconds} second cool-down...")
        await asyncio.sleep(self.cool_down_seconds)
        self.logger.info("Cool-down complete. Resetting application state...")

        # 3. Clear existing market state (all order books)
        self.market_manager.reset()

        # 4. Get and log updated balances
        #  get_venue_balance()

        # 5. Restart WebSocket listeners to fetch fresh snapshots
        self.logger.info("Restarting WebSocket clients to fetch fresh order books...")
        self._tasks["kalshi_connect"] = asyncio.create_task(self.kalshi_wss.connect_forever())
        self._tasks["poly_connect"] = asyncio.create_task(
            self.poly_wss_client.connect_forever(channel_path=self.poly_wss_client.MARKET_PATH)
        )
        self.logger.info("Reset complete. Resuming normal operation.")

    async def _configure_markets(self, market_tuples: List[tuple]):
        """
        Configures markets based on the pairs provided at runtime.
        """
        self.logger.info("Configuring markets...")

        # 1. Get market pairs to trade from the repository
        self.market_pairs = self.matches_repo.get_market_pairs(market_tuples)
        if not self.market_pairs:
            raise ValueError("No market pairs configured in MatchesRepository.")

        # 2. Fetch live data for these pairs using the gateways
        poly_ids = [pair.poly_id for pair in self.market_pairs]
        kalshi_tickers = [pair.kalshi_ticker for pair in self.market_pairs]

        poly_task = self.poly_gateway.get_markets_by_id(poly_ids)
        kalshi_task = self.kalshi_gateway.get_markets_by_id(kalshi_tickers)
        poly_results, kalshi_results = await asyncio.gather(poly_task, kalshi_task)

        # 3. Validate and create matched market objects
        matched_markets = self._create_matched_markets(poly_results, kalshi_results)

        # 4. Prepare the final configuration for the WebSocket clients
        self.markets_config = []
        for match in matched_markets:
            config_item = {
                "id": match.kalshi_ticker,
                "kalshi_ticker": match.kalshi_ticker,
                "polymarket_yes_token_id": match.poly_clobTokenIds[0],
                "polymarket_no_token_id": match.poly_clobTokenIds[1]
            }
            self.markets_config.append(config_item)
            # Register the market with the manager
            self.market_manager.register_market(config_item['id'])

        self.kalshi_wss.set_market_config(self.markets_config)
        self.poly_wss_client.set_market_config(self.markets_config)

        all_poly_token_ids = []
        for config in self.markets_config:
            all_poly_token_ids.append(config['polymarket_yes_token_id'])
            all_poly_token_ids.append(config['polymarket_no_token_id'])
        self.poly_wss_client.set_asset_ids(all_poly_token_ids)

        self.logger.info("Market configuration complete.")

    def _create_matched_markets(self, polymarkets: List, kalshi_markets: List) -> List[MatchedMarketBase]:
        """Helper method to create MatchedMarketBase objects from raw API data."""
        matched_markets = []
        # This simple loop assumes the lists from the gateways are in the same order
        # as the market_pairs requested.
        for _, pair in enumerate(self.market_pairs):
            # Find the corresponding poly market
            poly_market_data = next((p[0] for p in polymarkets if p and p[0]['id'] == pair.poly_id), None)
            # Find the corresponding kalshi market
            kalshi_market_data = next((k for k in kalshi_markets if k['ticker'] == pair.kalshi_ticker), None)

            if not poly_market_data or not kalshi_market_data:
                self.logger.warning(f"Could not find full data for pair {pair}. Skipping.")
                continue

            polymarket = PolymarketMarket(**poly_market_data)
            kalshi_market = KalshiMarket(**kalshi_market_data)

            if not polymarket.active or kalshi_market.status != "active":
                self.logger.warning(f"Market pair {pair} is not active. Skipping.")
                continue

            matched_market_base = MatchedMarketBase.from_markets(poly=polymarket, kalshi=kalshi_market)
            matched_markets.append(matched_market_base)

        return matched_markets

    async def _shutdown_monitor(self):
        """Waits for the shutdown event and then stops all tasks."""
        await self.shutdown_event.wait()
        self.logger.critical("Shutdown signal received. Stopping all services.")
        await self.stop()

    async def _start(self, core_coroutines: List[Coroutine]):
        """Creates and manages all runtime tasks from the bootstrapped coroutines."""
        if self._running:
            self.logger.warning("Orchestrator is already running.")
            return
        self._running = True

        task_names = ["kalshi_connect", "poly_connect", "message_bus"]
        for i, coro in enumerate(core_coroutines):
            task_name = task_names[i] if i < len(task_names) else f"core_task_{i}"
            self._tasks[task_name] = asyncio.create_task(coro)

        if self.printer:
            self._tasks["printer_task"] = asyncio.create_task(self.printer.run_printer_service())
        self._tasks["flush_task"] = asyncio.create_task(self.trade_storage.start())
        self._tasks["shutdown_monitor"] = asyncio.create_task(self._shutdown_monitor())

        self.logger.info(f"Fletcher Orchestrator started all tasks: {list(self._tasks.keys())}")

        tasks_to_await = [
            task for name, task in self._tasks.items()
            if name not in ("kalshi_connect", "poly_connect")
        ]

        try:
            # We only await the critical tasks. The WSS tasks can be managed separately.
            await asyncio.gather(*tasks_to_await)
        except asyncio.CancelledError:
            self.logger.info("Orchestrator's main tasks were cancelled.")
        finally:
            # If any of the critical tasks stop, initiate a full shutdown.
            await self.stop()

    async def stop(self):
        """Stops all running tasks gracefully."""
        if not self._running:
            return
        self.logger.info("Stopping Fletcher Orchestrator...")
        self._running = False
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                self.logger.info(f"Cancelled task: {name}")
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self.logger.info("Fletcher Orchestrator stopped.")