import asyncio
import logging.config
from decimal import Decimal
from typing import List

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
import yappi


async def run_live_opportunity_trader(orchestrator: FletcherOrchestrator, market_tuples: List[tuple]):
    """
    Starts the main application orchestrator for a specific set of markets.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting Fletcher Orchestrator...")
    await orchestrator.run_live_trading_service(market_tuples=market_tuples, dry_run=settings.DRY_RUN, cool_down_seconds=5)

def main(minimum_balance = settings.SHUTDOWN_BALANCE):
    # --- CONFIGURATION FLAG ---
    # Set this to False to disable the order book printer.
    ENABLE_DIAGNOSTIC_PRINTER = False
    # --- 1. Initialize core dependencies (clients, bus) ---
    db_con = supabase_client.SupabaseClient(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    gamma_client = PolymGammaClient()
    # use factories to create authenticated clients
    polymarket_factory = PolymarketClientFactory()
    clob_client, clob_wss_client = polymarket_factory.create_both_clients()

    factory = KalshiClientFactory()
    kalshi_http, kalshi_wss = factory.create_both_clients()

    balance_gtwy = BalanceDataGateway(clob_http_client=clob_client, kalshi_http_client=kalshi_http)
    balance_service = BalanceService(balance_gtwy, minimum_balance=Decimal(minimum_balance))
    try:
        balance_service.update_wallets()
        poly_usdc_balance = balance_service.polymarket_wallet.get_balance(Currency.USDC_E).amount
        poly_pol_balance = balance_service.polymarket_wallet.get_balance(Currency.POL).amount
        kalshi_balance = balance_service.kalshi_wallet.get_balance(Currency.USD).amount
        if not balance_service.has_enough_balance:
            raise Exception(f"Balance too low to execute trades. Poly balance {poly_usdc_balance}. Kalshi balance {kalshi_balance}")
    except Exception as e:
        raise f"Failed to generate new wallets. Service stopping: {e}"

    logger.info(
        f"Polymarket USDC.e balance: {poly_usdc_balance:.2f}, "
        f"matic balance: {poly_pol_balance:.2f}")
    logger.info(f"Kalshi balance: ${kalshi_balance:.2f}")

    # Create the central message bus
    bus = MessageBus()

    # --- 2. Initialize Gateways and Repositories ---
    # Gateways are for fetching external data
    poly_gateway = PolymarketGateway(http_client=gamma_client)
    kalshi_gateway = KalshiGateway(http_client=kalshi_http)

    # Repositories are for our own data and executing trades
    matches_repo = MatchesRepository(supabase_client=db_con.client)
    attempted_opps_repo = AttemptedOpportunitiesGateway(supabase_client=db_con.client)
    trade_repo = TradeGateway(kalshi_http, clob_client)

    # Create printer
    market_manager = MarketManager(bus)
    # Create trade storage service
    automatic_flush_minutes = 30
    trade_storage = TradeStorage(bus=bus, trade_repo=trade_repo, attempted_opportunities_repo=attempted_opps_repo,
                                 batch_size=100, flush_interval_seconds=automatic_flush_minutes * 60)

    printer = None
    if ENABLE_DIAGNOSTIC_PRINTER:
        printer = DiagnosticPrinter(market_state_querier=market_manager, interval_seconds=10)
        logger.info("Diagnostic printer is ENABLED.")
    else:
        logger.info("Diagnostic printer is DISABLED.")

    # --- 3. Instantiate the main Orchestrator with all dependencies ---
    live_trader_service = FletcherOrchestrator(
        poly_wss_client=clob_wss_client,
        kalshi_wss=kalshi_wss,
        matches_repo=matches_repo,
        attempted_opps_repo=attempted_opps_repo,
        trade_repo=trade_repo,
        poly_gateway=poly_gateway,
        kalshi_gateway=kalshi_gateway,
        bus=bus,
        printer=printer,
        trade_storage=trade_storage,
        market_manager=market_manager,
        balance_service=balance_service,
    )

    # --- 4. Run the application ---
    yappi.set_clock_type("CPU")
    with yappi.run():
        try:
            asyncio.run(run_live_opportunity_trader(live_trader_service, markets_to_trade))
            # log closing balances
            logger.info(
                f"Polymarket USDC.e balance: {balance_service.get_wallets().polymarket_wallet.get_balance(Currency.USDC_E).amount:.2f}, "
                f"matic balance: {balance_service.get_wallets().polymarket_wallet.get_balance(Currency.POL).amount:.2f}")
            logger.info(
                f"Kalshi balance: ${balance_service.get_wallets().kalshi_wallet.get_balance(Currency.USD).amount:.2f}")
        except (KeyboardInterrupt, SystemExit):
            logger.info("Application shutting down...")
    yappi.get_func_stats().print_all()
if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    markets_to_trade = [
        ("557390", "KXMLBGAME-25JUN30SDPHI-SD")
    ]
    main()