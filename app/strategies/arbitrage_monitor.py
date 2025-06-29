import logging
from datetime import timedelta
from decimal import getcontext, Decimal, ROUND_CEILING
from typing import Dict, List, Optional

from shared_wallets.domain.types import Currency

from app.domain.events import MarketBookUpdated, ArbitrageOpportunityFound, ExecuteTrade, TradeAttemptCompleted
from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Money, Platform, SIDES
from app.markets.manager import MarketManager
from app.markets.state import MarketState
from app.message_bus import MessageBus
from app.domain.types import Wallets
# --- Module Setup ---

getcontext().prec = 18
logger = logging.getLogger(__name__)
PROFITABILITY_BUFFER = Decimal("0.01")
STALENESS_THRESHOLD = timedelta(seconds=5)

# Dependencies are stored at the module level and injected once at startup.
_market_manager: MarketManager
_bus: MessageBus
_market_config_map: Dict[str, Dict[str, str]] = {}
_is_trade_in_progress: bool = False
_wallets : Wallets


def initialize_arbitrage_handlers(
    market_manager: MarketManager,
    bus: MessageBus,
    wallets: Wallets,
    markets_config: List[Dict[str, str]],
):
    """Injects dependencies into the strategy handlers module."""
    global _market_manager, _bus, _market_config_map, _wallets
    _market_manager = market_manager
    _bus = bus
    _wallets = wallets
    _market_config_map = {m["id"]: m for m in markets_config}
    logger.debug(f"Arbitrage handler starting kalshi wallet amount: ${wallets.kalshi_wallet.get_balance(Currency.USD)}")
    logger.debug(f"Arbitrage handler starting polymarket wallet USDC.e amount: {wallets.polymarket_wallet.get_balance(Currency.USDC_E)}")
    logger.info("Arbitrage monitor handlers initialized.")


# --- Event and Command Handlers ---

async def handle_market_book_update(event: MarketBookUpdated):
    """
    This handler is the entry point for our strategy. It's triggered when a
    market's state changes, and it checks for an arbitrage opportunity.
    """
    global _is_trade_in_progress
    if _is_trade_in_progress:
        logger.debug("Skipping opportunity check: trade already in progress.")
        return

    logger.debug(f"Handling MarketBookUpdated for {event.market_id}")
    market_state = _market_manager.get_market_state(event.market_id)
    if not market_state:
        return

    opportunity = _check_for_buy_both_arb(market_state)

    if opportunity:
        logger.info(
            "Arbitrage opportunity detected, locking strategy until execution is complete.",
            extra={
                "opportunity_details": opportunity.model_dump(mode='json')
            }
        )
        _is_trade_in_progress = True
        await _bus.publish(ArbitrageOpportunityFound(opportunity=opportunity))
    else:
        logger.debug(
            "No arbitrage opportunity found on market update",
            extra={"market_id": event.market_id}
        )


async def handle_arbitrage_opportunity_found(event: ArbitrageOpportunityFound):
    """
    This handler consumes the event created by our own strategy. It's responsible
    for the decision to act on the opportunity by issuing a command.
    """
    logger.info(f"Handling ArbitrageOpportunityFound for {event.opportunity.market_id}. Issuing ExecuteTrade command.")
    await _bus.publish(ExecuteTrade(opportunity=event.opportunity, wallets=_wallets))


async def handle_trade_attempt_completed(event: TradeAttemptCompleted):
    """Resets the trade-in-progress flag, re-enabling opportunity checks."""
    global _is_trade_in_progress
    _is_trade_in_progress = False
    logger.info("Trade attempt completed. Re-enabling arbitrage checks.")


# --- Strategy Logic ---

def _kalshi_fee(contracts: Money, price: Money, rate: Decimal = Decimal("0.07")) -> Money:
    """Calculates the Kalshi trading fee."""
    if price <= Decimal("0") or price >= Decimal("1"):
        return Money("0.00")
    raw_decimal = rate * contracts * price * (Decimal("1") - price)
    cents = raw_decimal * Decimal("100")
    rounded_cents = cents.to_integral_value(rounding=ROUND_CEILING)
    return rounded_cents / Decimal("100")


def _check_for_buy_both_arb(market_state: MarketState) -> Optional[ArbitrageOpportunity]:
    """
    Checks for a "buy both" opportunity using the MarketState domain model.
    If an opportunity is found, it returns an ArbitrageOpportunity object.
    """
    market_id = market_state.market_id
    market_config = _market_config_map.get(market_id)
    if not market_config:
        return None

    # --- Get prices by asking the domain model ---
    kalshi_yes_ask_price = market_state.get_price(Platform.KALSHI, "YES", SIDES.SELL)
    poly_no_ask_price = market_state.get_price(Platform.POLYMARKET, "NO", SIDES.SELL)
    poly_yes_ask_price = market_state.get_price(Platform.POLYMARKET, "YES", SIDES.SELL)
    kalshi_no_ask_price = market_state.get_kalshi_derived_no_ask_price()

    # --- Get available liquidity (size) ---
    kalshi_outcomes = market_state.get_outcomes_for_platform(Platform.KALSHI)
    poly_outcomes = market_state.get_outcomes_for_platform(Platform.POLYMARKET)

    kalshi_yes_tob = kalshi_outcomes.get_book("YES").get_top_of_book() if kalshi_outcomes and kalshi_outcomes.get_book("YES") else (None, None)
    poly_yes_tob = poly_outcomes.get_book("YES").get_top_of_book() if poly_outcomes and poly_outcomes.get_book("YES") else (None, None)
    poly_no_tob = poly_outcomes.get_book("NO").get_top_of_book() if poly_outcomes and poly_outcomes.get_book("NO") else (None, None)

    kalshi_yes_ask_size = kalshi_yes_tob[1][1] if kalshi_yes_tob[1] else Decimal("0")
    kalshi_yes_bid_size = kalshi_yes_tob[0][1] if kalshi_yes_tob[0] else Decimal("0")
    poly_yes_ask_size = poly_yes_tob[1][1] if poly_yes_tob[1] else Decimal("0")
    poly_no_ask_size = poly_no_tob[1][1] if poly_no_tob[1] else Decimal("0")

    # +++ ADDED FOR DIAGNOSTICS +++
    logger.info(
        "--- Arbitrage Price Check ---",
        extra={
            "market_id": market_id,
            "kalshi_yes_ask_price": f"{kalshi_yes_ask_price!r}",
            "kalshi_yes_ask_size": f"{kalshi_yes_ask_size!r}",
            "poly_no_ask_price": f"{poly_no_ask_price!r}",
            "poly_no_ask_size": f"{poly_no_ask_size!r}",
        }
    )
    # +++ END DIAGNOSTICS +++

    # --- Opportunity 1: Buy YES on Kalshi, Buy NO on Polymarket ---
    if kalshi_yes_ask_price is not None and poly_no_ask_price is not None:
        is_stale = False
        if kalshi_outcomes and poly_outcomes:
            kalshi_book = kalshi_outcomes.get_book("YES")
            poly_book = poly_outcomes.get_book("NO")
            if kalshi_book and poly_book and (abs(kalshi_book.last_update - poly_book.last_update) > STALENESS_THRESHOLD):
                logger.debug("Skipping opportunity 1 check for %s due to stale books.", market_id)
                is_stale = True

        if not is_stale:
            cost1 = kalshi_yes_ask_price + poly_no_ask_price
            trade_size1 = min(kalshi_yes_ask_size, poly_no_ask_size)
            if trade_size1 > 0 and (cost1 + (_kalshi_fee(trade_size1, kalshi_yes_ask_price) / trade_size1)) < Decimal("1.0") - PROFITABILITY_BUFFER:
                profit_margin = Decimal("1.0") - (cost1 + (_kalshi_fee(trade_size1, kalshi_yes_ask_price) / trade_size1))
                return ArbitrageOpportunity(
                    market_id=market_id, buy_yes_platform=Platform.KALSHI, buy_yes_price=kalshi_yes_ask_price,
                    buy_no_platform=Platform.POLYMARKET, buy_no_price=poly_no_ask_price, profit_margin=profit_margin,
                    potential_trade_size=trade_size1, kalshi_ticker=market_config["kalshi_ticker"],
                    polymarket_yes_token_id=market_config["polymarket_yes_token_id"], polymarket_no_token_id=market_config["polymarket_no_token_id"],
                )

    # --- Opportunity 2: Buy YES on Polymarket, Buy NO on Kalshi ---
    if poly_yes_ask_price is not None and kalshi_no_ask_price is not None:
        is_stale = False
        if kalshi_outcomes and poly_outcomes:
            # Kalshi "NO" is derived from "YES" book, so we check the YES book's timestamp
            kalshi_book = kalshi_outcomes.get_book("YES")
            poly_book = poly_outcomes.get_book("YES")
            if kalshi_book and poly_book and (abs(kalshi_book.last_update - poly_book.last_update) > STALENESS_THRESHOLD):
                 logger.debug("Skipping opportunity 2 check for %s due to stale books.", market_id)
                 is_stale = True

        if not is_stale:
            cost2 = poly_yes_ask_price + kalshi_no_ask_price
            trade_size2 = min(poly_yes_ask_size, kalshi_yes_bid_size)
            if trade_size2 > 0 and (cost2 + (_kalshi_fee(trade_size2, kalshi_no_ask_price) / trade_size2)) < Decimal("1.0") - PROFITABILITY_BUFFER:
                profit_margin = Decimal("1.0") - (cost2 + (_kalshi_fee(trade_size2, kalshi_no_ask_price) / trade_size2))
                return ArbitrageOpportunity(
                    market_id=market_id, buy_yes_platform=Platform.POLYMARKET, buy_yes_price=poly_yes_ask_price,
                    buy_no_platform=Platform.KALSHI, buy_no_price=kalshi_no_ask_price, profit_margin=profit_margin,
                    potential_trade_size=trade_size2, kalshi_ticker=market_config["kalshi_ticker"],
                    polymarket_yes_token_id=market_config["polymarket_yes_token_id"], polymarket_no_token_id=market_config["polymarket_no_token_id"],
                )

    return None