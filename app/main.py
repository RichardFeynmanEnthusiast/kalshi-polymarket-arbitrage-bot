import asyncio
import logging.config
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple, Optional

from shared_wallets.domain.models import Currency

from app.clients.polymarket.gamma_http import PolymGammaClient
from app.gateways.balance_data_gateway import BalanceDataGateway
from app.services.operational.balance_service import BalanceService
from shared_infra.supabase_setup import supabase_client
from app.gateways.kalshi_gateway import KalshiGateway
from app.gateways.polymarket_gateway import PolymarketGateway
from app.settings.logging_config import LOGGING_CONFIG
from app.settings.settings import settings
from app.markets.manager import MarketManager
from app.message_bus import MessageBus
from app.orchestration.fletcher_orchestrator import FletcherOrchestrator
from app.repositories.matches_repository import MatchesRepository
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.gateways.trade_gateway import TradeGateway
from app.services.operational.diagnostic_printer import DiagnosticPrinter
from app.services.trade_storage import TradeStorage
from app.utils.kalshi_client_factory import KalshiClientFactory
from app.utils.polymarket_client_factory import PolymarketClientFactory

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

@dataclass
class AppDependencies:
    # operational services
    balance_service : BalanceService
    # core
    fletcher : FletcherOrchestrator

class DoubleTimeHFTApp:
    """ Start up the entire HFT application"""
    def __init__(self, markets_to_trade: List[Tuple], shutdown_balance: Decimal, dependencies : AppDependencies,
                 ):
        self.markets_to_trade = markets_to_trade
        self.shutdown_balance = shutdown_balance
        self.logger = logging.getLogger(__name__)
        self._setup_dependencies(dependencies)

    def _setup_dependencies(self, dependencies: AppDependencies):
        self.balance_service = dependencies.balance_service
        self.fletcher_orchestrator = dependencies.fletcher

    async def run_double_time_hft(self):
        """
        Starts the main application orchestrator for a specific set of markets.
        """
        logger.info("Starting Fletcher Orchestrator...")
        await self.fletcher_orchestrator.run_live_trading_service(market_tuples=self.markets_to_trade, dry_run=settings.DRY_RUN,
                                                    cool_down_seconds=5)

    def check_balance(self):
        try:
            self.balance_service.update_wallets()
            poly_usdc_balance = self.balance_service.polymarket_wallet.get_balance(Currency.USDC_E).amount
            poly_pol_balance = self.balance_service.polymarket_wallet.get_balance(Currency.POL).amount
            kalshi_balance = self.balance_service.kalshi_wallet.get_balance(Currency.USD).amount
            if not self.balance_service.has_enough_balance:
                raise Exception(
                    f"Balance too low to execute trades. Poly balance {poly_usdc_balance}. Kalshi balance {kalshi_balance}")
            else:
                logger.info(
                    f"Polymarket USDC.e balance: {poly_usdc_balance:.2f}, "
                    f"matic balance: {poly_pol_balance:.2f}")
                logger.info(f"Kalshi balance: ${kalshi_balance:.2f}")
        except Exception as e:
            raise f"Failed to generate new wallets. Service stopping: {e}"

    async def start(self):
        self.check_balance()
        try:
            await self.run_double_time_hft()
            # log closing balances
            logger.info(
                f"Polymarket USDC.e balance: {self.balance_service.get_wallets().polymarket_wallet.get_balance(Currency.USDC_E).amount:.2f}, "
                f"matic balance: {self.balance_service.get_wallets().polymarket_wallet.get_balance(Currency.POL).amount:.2f}")
            logger.info(
                f"Kalshi balance: ${self.balance_service.get_wallets().kalshi_wallet.get_balance(Currency.USD).amount:.2f}")
        except (KeyboardInterrupt, SystemExit):
            logger.info("Application shutting down...")

async def main(enable_diagnostic_printer: bool):

    markets_to_trade = [
        ("552975", "KXNATHANDOGS-25-70")
    ]

    # low-level dependencies
    polymarket_factory = PolymarketClientFactory()
    clob_client, clob_wss_client = polymarket_factory.create_both_clients()

    factory = KalshiClientFactory()
    kalshi_http, kalshi_wss = factory.create_both_clients()

    db_con = supabase_client.SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)

    # Repositories are for our own data and executing trades
    matches_repo = MatchesRepository(supabase_client=db_con.client)
    attempted_opps_repo = AttemptedOpportunitiesGateway(supabase_client=db_con.client)
    trade_repo = TradeGateway(kalshi_http, clob_client)

    # Services
    bus : MessageBus = MessageBus()
    market_manager = MarketManager(bus)
    automatic_flush_minutes = 30
    trade_storage = TradeStorage(bus=bus, trade_repo=trade_repo, attempted_opportunities_repo=attempted_opps_repo,
                                 batch_size=1, flush_interval_seconds=automatic_flush_minutes * 60)
    balance_service = BalanceService(BalanceDataGateway(clob_http_client=clob_client, kalshi_http_client=kalshi_http),
                                     minimum_balance=Decimal(settings.SHUTDOWN_BALANCE))

    printer = None
    if enable_diagnostic_printer:
        printer = DiagnosticPrinter(market_state_querier=market_manager, interval_seconds=10)
    logger.info("Diagnostic printer is %s.", "ENABLED" if printer else "DISABLED")


    orchestrator = FletcherOrchestrator(
        poly_wss_client=clob_wss_client,
        kalshi_wss=kalshi_wss,
        matches_repo=matches_repo,
        attempted_opps_repo=attempted_opps_repo,
        trade_repo=trade_repo,
        poly_gateway=PolymarketGateway(http_client=PolymGammaClient()),
        kalshi_gateway=KalshiGateway(http_client=kalshi_http),
        bus=bus,
        printer=printer,
        trade_storage=trade_storage,
        market_manager=market_manager,
        balance_service=balance_service,
    )

    app_dependencies = AppDependencies(
        balance_service = balance_service,
        fletcher = orchestrator
    )

    double_time = DoubleTimeHFTApp(markets_to_trade=markets_to_trade, shutdown_balance=settings.SHUTDOWN_BALANCE,
                                   dependencies=app_dependencies)
    await double_time.start()



if __name__ == "__main__":
    try:
        asyncio.run(main(enable_diagnostic_printer=False))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application shutting down...")