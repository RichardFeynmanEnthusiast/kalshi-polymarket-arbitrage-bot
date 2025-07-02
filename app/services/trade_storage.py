import asyncio
import logging
from typing import List, Optional

from app.domain.events import ArbTradeResultReceived, StoreTradeResults
from app.domain.models.opportunity import ArbitrageOpportunityRecord
from app.message_bus import MessageBus
from app.gateways.trade_gateway import TradeGateway
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.settings.settings import settings

logger = logging.getLogger(__name__)

class TradeStorage:
    """
    Accumulates trade results for all trades involved in an arbitrage opportunity and periodically 
    flushes the group trade results to the database.
    """
    FLUSH_MINUTES = 5 # frequency of flushing if batch size is not reached
    
    def __init__(
        self, 
        bus: MessageBus, 
        trade_repo: TradeGateway,
        attempted_opportunities_repo: AttemptedOpportunitiesGateway ,
        batch_size: int = 100,
        flush_interval_seconds: int = FLUSH_MINUTES * 60
    ):
        self.bus = bus
        self.attempted_opp_repo = attempted_opportunities_repo
        self.trade_repo = trade_repo
        # Flushing parameters 
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        
        # Accumulate trade results
        self.trade_results: List[ArbTradeResultReceived] = []
        self._lock = asyncio.Lock()
        
        # The trade storage service now subscribes its own handler to the bus.
        # bus.subscribe(StoreTradeResults, self.handle_trade_results_received)

        # Start periodic flush task
        self._flush_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the periodic flush task"""
        self._flush_task = asyncio.create_task(self.handle_periodic_flush())
        logger.info(f"Trade batch storage started with batch_size={self.batch_size}, flush_interval={self.flush_interval_seconds}s")
    
    async def stop(self):
        """Stop the periodic flush task and flush remaining results"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining results
        await self._flush_batch()
        logger.info("Trade batch storage stopped")
    
    async def handle_periodic_flush(self):
        """Periodically flush results even if batch size isn't reached"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval_seconds)
                async with self._lock:
                    if self.trade_results:
                        await self._flush_batch()
            except asyncio.CancelledError:
                logger.info("Flushing trade batches before cancelling service")
                await self._flush_batch()
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}", exc_info=True)
        
# --- Event and Command Handlers ---

    async def handle_trade_results_received(self, command: StoreTradeResults):
        """ Handle trade results received from the execution service"""
        if settings.DRY_RUN:
            return
        async with self._lock:
            self.trade_results.append(command.arb_trade_results)

            # Check if we've reached the batch size
            if len(self.trade_results) >= self.batch_size:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush the current batch to the database"""
        if not self.trade_results:
            logger.info("No trade results to flush")
            return
        batch_to_flush = self.trade_results.copy()
        self.trade_results.clear()
        
        try:
            # Store the batch in the database
            result = await self._store_trade_results(trade_results=batch_to_flush)

            if isinstance(result, list):
                logger.info(f"Flushed {len(result)} trade results to database")
            else:
                logger.info(f"Something went wrong flushing to the database")

        except Exception as e:
            logger.error(f"Failed to flush trade batch: {e}", exc_info=True)
            # Put the results back in the queue for retry
            async with self._lock:
                self.trade_results.extend(batch_to_flush)

    async def _store_trade_results(self, trade_results: List[ArbTradeResultReceived]):
        """Store trade results in the database"""
        # Create arb opp records
        records : List[ArbitrageOpportunityRecord] = []

        for trade_result in trade_results:
            # Determine trade execution status based on order results
            poly_trade_executed = trade_result.polymarket_order is not None and trade_result.polymarket_error is None
            kalshi_trade_executed = trade_result.kalshi_order is not None and trade_result.kalshi_error_message is None

            # Extract order IDs if available
            poly_order_id = None
            if poly_trade_executed and trade_result.polymarket_order:
                # Extract order ID from PolymarketOrder - adjust based on actual structure
                poly_order_id = getattr(trade_result.polymarket_order, 'order_id', None)

            kalshi_order_id = None
            if kalshi_trade_executed and trade_result.kalshi_order:
                # Extract order ID from KalshiOrder - adjust based on actual structure
                kalshi_order_id = getattr(trade_result.kalshi_order, 'order_id', None)

            # Create the record
            record = ArbitrageOpportunityRecord(
                arbitrage_opportunity=trade_result.opportunity,
                category=trade_result.category,
                detected_at=trade_result.timestamp,  # Use current time or extract from trade_result
                poly_trade_executed=poly_trade_executed,
                poly_order_id=poly_order_id,
                kalshi_trade_executed=kalshi_trade_executed,
                kalshi_order_id=kalshi_order_id
            )

            records.append(record)
        self.attempted_opp_repo.add_attempted_opportunities_repository(records)