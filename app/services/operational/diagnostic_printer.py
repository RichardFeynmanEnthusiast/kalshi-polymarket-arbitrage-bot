import asyncio
import logging

from app.domain.primitives import Platform
from app.markets.order_book import Orderbook
from app.services.query_interface import IMarketStateQuerier


class DiagnosticPrinter:
    """
    A simple service that periodically prints a multi-level snapshot of the
    order book for all tracked markets for verification and debugging purposes.
    """

    def __init__(self, market_state_querier: IMarketStateQuerier, interval_seconds: int = 5, depth: int = 3):
        """
        Initializes the DiagnosticPrinter.
        Args:
            market_state_querier: An object that can query for market states.
            interval_seconds: How often to print the book state.
            depth: The number of order book levels to display.
        """
        self.querier = market_state_querier
        self.interval = interval_seconds
        self.depth = depth
        self.logger = logging.getLogger(__name__)

    def _print_book(self, title: str, book: Orderbook | None):
        """Helper method to format and print a single order book."""
        print(f"  {title}:")
        if not book:
            print("    (Book not available)")
            return

        snapshot = book.get_book_snapshot(depth=self.depth)
        bids = snapshot.get('bids', [])
        asks = snapshot.get('asks', [])

        # Header
        print("    BIDS              |  ASKS")
        print("    Price | Size      |  Price | Size")
        print("    ------+---------  |  ------+---------")

        max_rows = max(len(bids), len(asks))
        if max_rows == 0:
            print("    (Book is empty)")
            return

        for i in range(max_rows):
            bid_str = " " * 17  # Empty bid string
            if i < len(bids):
                bid_price, bid_size = bids[i]
                bid_str = f"{bid_price:<5.2f} | {bid_size:<8.2f}"

            ask_str = ""  # Empty ask string
            if i < len(asks):
                ask_price, ask_size = asks[i]
                ask_str = f"{ask_price:<5.2f} | {ask_size:<8.2f}"

            print(f"    {bid_str}  |  {ask_str}")

    async def run_printer_service(self):
        """Runs an infinite loop, printing the book states."""
        self.logger.info(f"Starting diagnostic printer service (depth={self.depth}, interval={self.interval}s)...")
        while True:
            await asyncio.sleep(self.interval)
            print("\n" + "=" * 50)
            print(f"|          ORDER BOOK SNAPSHOT (Top {self.depth} Levels)      |")
            print("=" * 50)

            market_state = self.querier.get_all_market_states()

            if not market_state:
                print("| No markets registered yet.                   |")
                print("=" * 50)
                continue

            for market_state in market_state:
                print(f"\n--- Market: {market_state.market_id} ---")

                # Get book objects from the state model
                kalshi_outcomes = market_state.get_outcomes_for_platform(Platform.KALSHI)
                poly_outcomes = market_state.get_outcomes_for_platform(Platform.POLYMARKET)

                # Print each book using the helper method
                if kalshi_outcomes:
                    self._print_book("Kalshi - YES Book", kalshi_outcomes.yes)

                if poly_outcomes:
                    print()  # Add spacing
                    self._print_book("Polymarket - YES Book", poly_outcomes.yes)
                    print()  # Add spacing
                    self._print_book("Polymarket - NO Book", poly_outcomes.no)

            print("\n" + "=" * 50 + "\n")