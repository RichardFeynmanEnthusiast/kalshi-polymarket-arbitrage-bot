import asyncio
import time
from typing import Optional, List
import logging
import copy

import pytest

from app.domain.events import OrderBookSnapshotReceived, MarketBookUpdated, PriceLevelData
from app.domain.primitives import Platform, SIDES
from app.markets.order_book import Orderbook
from app.markets.state import MarketOutcomes
from tests.sample_data import SAMPLE_POLY_ORDERBOOK_RECEIVED, SAMPLE_MARKET_STATES, SAMPLE_MARKET_STATE, \
    POLY_YES_ORDERBOOK

# -- simulate actual perform snapshot call

poly_snapshot = SAMPLE_POLY_ORDERBOOK_RECEIVED
logger = logging.getLogger(__name__)

def get_outcomes_for_platform(platform: Platform) -> Optional[MarketOutcomes]:
    """
    Safely retrieves the MarketOutcomes object for a given platform.
    """
    return SAMPLE_MARKET_STATE.platforms.get(platform)

def get_book(self, outcome: str) -> Optional[Orderbook]:
    """
    Safely retrieves the order book for a given outcome string.
    """
    if outcome.upper() == 'YES':
        return self.yes
    elif outcome.upper() == 'NO':
        return self.no
    return None

test_bus = asyncio.Queue()

async def _emit_book_update(source_event) -> None:
    """Creates a MarketBookUpdated event and publishes it back to the bus."""
    update_event = MarketBookUpdated(
        market_id=source_event.market_id,
        platform=source_event.platform
    )
    await test_bus.put(item=update_event)

async def _handle_snapshot(event: OrderBookSnapshotReceived) -> None:
    """Handles a full book snapshot, clearing the book first."""
    market_state = SAMPLE_MARKET_STATES
    if not market_state: return

    platform_outcomes = get_outcomes_for_platform(platform=event.platform)
    if not platform_outcomes: return

    book = platform_outcomes.get_book(event.outcome)
    if not book: return

    old_tob = book.get_top_of_book()

    # Clear the book before applying snapshot
    book.clear()

    for level in event.bids:
        book.apply_update(SIDES.BUY, level.price, level.size)
    for level in event.asks:
        book.apply_update(SIDES.SELL, level.price, level.size)
    if old_tob != book.get_top_of_book():
        logger.info(
            "Top-of-book changed for %s via snapshot on platform %s.",
            event.market_id,
            event.platform
        )
        await _emit_book_update(event)

@pytest.mark.asyncio
async def test_handle_snapshot_perf():

    start = time.perf_counter()
    await _handle_snapshot(event=SAMPLE_POLY_ORDERBOOK_RECEIVED)
    duration = time.perf_counter() - start

    print(f"duration: {duration}")

# --- Optimize apply updates bottleneck

# average naive update bids duration (35 bids) : 1.77e-05
# average optimized update bids duration (35 bids): 1.04e-05
# average naive update asks duration (29 asks): 2.357e-05
# average optimized update asks duration (35 asks): 1.426e-05


def test_average_optimized_bids_duration() -> None:
    results = []
    for _ in range(0,10000):
        test_value = def_optimized_apply_updates_perf(books_to_update="bids")
        results.append(test_value)
    print(f"average update bids optimized duration: {sum(results) / len(results)}")

def test_average_optimized_asks_duration() -> None:
    results = []
    for _ in range(0,10000):
        test_value = def_optimized_apply_updates_perf(books_to_update="asks")
        results.append(test_value)
    print(f"average update asks optimized duration: {sum(results) / len(results)}")

def test_average_unoptimized_bids_duration() -> None:
    results = []
    for _ in range(0,10000):
        test_value = test_naive_apply_updates_perf(books_to_update="bids")
        results.append(test_value)
    print(f"average update bids unoptimized duration: {sum(results) / len(results)}")

def test_average_unoptimized_asks_duration() -> None:
    results = []
    for _ in range(0,10000):
        test_value = test_naive_apply_updates_perf(books_to_update="asks")
        results.append(test_value)
    print(f"average update asks unoptimized duration: {sum(results) / len(results)}")

# --- time calls
# asks method doesn't have a lambda so speed is faster on avg then bids update

def def_optimized_apply_updates_perf(books_to_update: str):
    book = copy.deepcopy(POLY_YES_ORDERBOOK)
    start = time.perf_counter()
    if books_to_update == "asks":
        optimized_update_book(side=SIDES.SELL,bids_list=SAMPLE_POLY_ORDERBOOK_RECEIVED.asks, book=book)
    elif books_to_update == "bids":
        optimized_update_book(side=SIDES.BUY,bids_list=SAMPLE_POLY_ORDERBOOK_RECEIVED.bids, book=book)
    duration = time.perf_counter() - start
    return duration


def test_naive_apply_updates_perf(books_to_update: str):
    book = copy.deepcopy(POLY_YES_ORDERBOOK)
    start = time.perf_counter()
    if books_to_update == "asks":
        naive_update_book(side=SIDES.SELL,bids_list=SAMPLE_POLY_ORDERBOOK_RECEIVED.asks, book=book)
    elif books_to_update == "bids":
        naive_update_book(side=SIDES.BUY,bids_list=SAMPLE_POLY_ORDERBOOK_RECEIVED.bids, book=book)
    duration = time.perf_counter() - start
    return duration

# simulate calls by the market manager

def optimized_update_book(side: SIDES, bids_list : List[PriceLevelData], book = POLY_YES_ORDERBOOK ) -> None:
    updates = [(level.price, level.size) for level in bids_list]
    book.apply_updates(side, updates)

def naive_update_book(side: SIDES, bids_list : List[PriceLevelData], book = POLY_YES_ORDERBOOK) -> None:
    for level in bids_list:
        book.apply_update(side, level.price, level.size)