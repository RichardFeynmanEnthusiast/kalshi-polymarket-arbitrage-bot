import asyncio
import logging.config
from typing import List

from app.clients.polymarket.gamma_http import PolymGammaClient
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


async def run_live_opportunity_trader(orchestrator: FletcherOrchestrator, market_tuples: List[tuple]):
    """
    Starts the main application orchestrator for a specific set of markets.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting Fletcher Orchestrator...")
    await orchestrator.run_live_trading_service(market_tuples=market_tuples, dry_run=True, cool_down_seconds=5)


def get_venue_balances(clob_http_client, kalshi_http_client) -> dict:
    try:
        usdc_e_bal, matic_bal = clob_http_client.get_starting_balances()
        raw_kalshi_balance = kalshi_http_client.get_balance()
        return {
            "poly_usdc_e_bal": usdc_e_bal,
            "poly_matic_bal": matic_bal / 10 ** 18,
            "kalshi_balance": raw_kalshi_balance['balance'] / 100,
        }
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")


if __name__ == "__main__":
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)

    markets_to_trade = [
        ("538932", "KXMAYORNYCPARTY-25-D")
    ]

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

    balance_dict = get_venue_balances(clob_client, kalshi_http)
    logger.info(
        f"Polymarket USDC.e balance: {balance_dict['poly_usdc_e_bal']:.2f}, matic balance: {balance_dict['poly_matic_bal']:.4f}")
    logger.info(f"Kalshi balance: ${balance_dict['kalshi_balance']:.2f}")

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
        market_manager=market_manager
    )

    # --- 4. Run the application ---
    try:
        asyncio.run(run_live_opportunity_trader(live_trader_service, markets_to_trade))
        # log closing balances
        balance_dict = get_venue_balances(clob_client, kalshi_http)
        logger.info(
            f"Closing Polymarket USDC.e balance: {balance_dict['poly_usdc_e_bal']:.2f}, matic balance: {balance_dict['poly_matic_bal']:.4f}")
        logger.info(f"Closing Kalshi balance: ${balance_dict['kalshi_balance']:.2f}")
    except (KeyboardInterrupt,  SystemExit):
        logger.info("Application shutting down...")
