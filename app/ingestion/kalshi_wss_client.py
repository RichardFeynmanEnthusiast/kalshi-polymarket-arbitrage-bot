import asyncio
import json
import logging
from decimal import Decimal
from typing import List, Dict, Optional

import websockets
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import ValidationError
from websockets.legacy.client import WebSocketClientProtocol

from app.clients.kalshi.base import KalshiBaseClient
from app.domain.events import OrderBookDeltaReceived, PriceLevelData, OrderBookSnapshotReceived
from app.domain.models.venue_data_schemas import KalshiSnapshotMessage, KalshiDeltaMessage
from app.domain.primitives import SIDES, Platform
from app.message_bus import MessageBus
from app.settings.env import Environment
from app.utils.web_socket_utils import require_initialized


class KalshiWebSocketClient(KalshiBaseClient):
    """
    An adapter that connects to Kalshi's WebSocket API and emits standardized Domain Events.
    It maintains an internal book state ONLY to correctly calculate the final size
    for Kalshi's delta messages, fulfilling its role as an adapter.
    """
    WS_URL_SUFFIX = "/trade-api/ws/v2"
    SHARED_SEQ_KEY = "shared_subscription_sequence"

    def __init__(
            self,
            key_id: str,
            private_key: rsa.RSAPrivateKey,
            *,
            environment: Environment = Environment.DEMO,
            connection_timeout_seconds: int = 10,
            reconnect_delay_seconds: int = 5,
    ) -> None:
        """
        Initializes the KalshiWebSocketClient.

        Args:
            key_id: Your Kalshi API Key ID.
            private_key: Your RSA private key object.
            environment: The Kalshi environment (DEMO or PROD).
            connection_timeout_seconds: Timeout for establishing a connection.
            reconnect_delay_seconds: Delay before attempting to reconnect.
        """
        super().__init__(key_id, private_key, environment)
        self._ws: Optional[WebSocketClientProtocol] = None
        self._connection_timeout_seconds = connection_timeout_seconds
        self._reconnect_delay_seconds = reconnect_delay_seconds
        self.bus = None
        self.market_map: Optional[Dict[str, str]] = None
        self.market_tickers: Optional[List[str]] = None
        self._last_seq: Dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._msg_id = 1
        # Internal state required by this adapter to correctly process Kalshi delta messages.
        self._books_state: Dict[str, Dict[str, Dict[int, int]]] = {}
        self.logger = logging.getLogger(__name__)

    def set_market_config(self, markets_config: List[Dict[str, str]]) -> None:
        self.market_map = {m['kalshi_ticker']: m['id'] for m in markets_config if 'kalshi_ticker' in m}
        self.market_tickers = list(self.market_map.keys())
        self._last_seq = {self.SHARED_SEQ_KEY: 0}
        self._books_state = {ticker: {"yes": {}, "no": {}} for ticker in self.market_tickers}

    def set_message_bus(self, bus: MessageBus):
        """
        Sets the message bus for publishing events.
        """
        self.bus = bus

    async def connect_forever(self) -> None:
        """Runs an infinite loop to maintain a connection, reconnecting on failure."""
        host = f"{self.WS_BASE_URL}{self.WS_URL_SUFFIX}"
        while True:
            self.logger.info("[Kalshi] Attempting to connect to %s...", host)
            try:
                headers = self.request_headers("GET", self.WS_URL_SUFFIX)
                async with websockets.connect(
                        host, additional_headers=headers, open_timeout=self._connection_timeout_seconds,
                        ping_interval=15, ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self.logger.info("[Kalshi] WebSocket connection established.")
                    await self._on_open()
                    await self._listen()
            except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError) as e:
                self.logger.warning("[Kalshi] Connection closed: %s. Reconnecting in %ss...", e,
                                    self._reconnect_delay_seconds)
            except RuntimeError as e:
                self.logger.error(
                    f"[Kalshi] Initialization error: {e}. The orchestrator may not have configured the client correctly. Retrying...")
            except Exception as exc:
                self.logger.error("[Kalshi] An unexpected error occurred: %s. Reconnecting in %ss...", exc,
                                  self._reconnect_delay_seconds)
            finally:
                self._ws = None
                await asyncio.sleep(self._reconnect_delay_seconds)

    # ------------------------------------------------------------------
    # Internal Connection & Message Handling
    # ------------------------------------------------------------------

    @require_initialized
    async def _on_open(self) -> None:
        """Subscribes to the configured market tickers upon connection."""
        if not self.market_tickers:
            raise RuntimeError("[Kalshi] No market_tickers configured – cannot subscribe.")
        await self._subscribe_orderbooks(self.market_tickers)

    @require_initialized
    async def _subscribe_orderbooks(self, tickers: List[str]) -> None:
        """Sends the subscription message to the Kalshi WebSocket server."""
        if not self._ws: return

        self.logger.info("[Kalshi] Resetting internal state for new subscription.")
        self._last_seq = {self.SHARED_SEQ_KEY: 0}
        self._books_state = {ticker: {"yes": {}, "no": {}} for ticker in self.market_tickers}

        msg = {"id": self._msg_id, "cmd": "subscribe",
               "params": {"channels": ["orderbook_delta"], "market_tickers": tickers}}
        await self._ws.send(json.dumps(msg))
        self.logger.info("[Kalshi] Sent subscription request for tickers: %s", tickers)
        self._msg_id += 1

    @require_initialized
    async def _listen(self) -> None:
        """Listens for, validates, and delegates normalization of incoming messages."""
        assert self._ws is not None
        self.logger.info("[Kalshi] Beginning listening process")
        async for raw_message in self._ws:
            self.logger.debug("[Kalshi] Received raw message", extra={'raw_message': raw_message})
            market_ticker = None  # Initialize to handle cases where parsing fails early
            try:
                data = json.loads(raw_message)
                msg_type = data.get("type")
                # Extract ticker early for better error logging and handling
                market_ticker = data.get("msg", {}).get("market_ticker")

                if not market_ticker or market_ticker not in self.market_map:
                    self.logger.debug(f"[Kalshi] Ignoring message for un-tracked or missing ticker: {market_ticker}")
                    continue

                # --- Sequence Number Validation ---
                if not await self._is_sequence_valid(data.get("seq")):
                    await self._request_resubscribe(market_ticker)
                    continue

                common_market_id = self.market_map[market_ticker]
                event = None

                if msg_type == "orderbook_snapshot":
                    msg = KalshiSnapshotMessage.model_validate(data).msg
                    # Reset internal state on snapshot
                    self._books_state[market_ticker] = {"yes": {}, "no": {}}
                    for price, size in msg.yes: self._books_state[market_ticker]['yes'][price] = size
                    for price, size in msg.no: self._books_state[market_ticker]['no'][price] = size

                    bids = [PriceLevelData(price=Decimal(str(p)) / 100, size=Decimal(str(s))) for p, s in msg.yes]
                    asks = [
                        PriceLevelData(price=Decimal("1") - (Decimal(str(p)) / Decimal("100")), size=Decimal(str(s)))
                        for p, s in msg.no]
                    event = OrderBookSnapshotReceived(
                        platform=Platform.KALSHI, market_id=common_market_id, outcome="YES", bids=bids, asks=asks
                    )
                elif msg_type == "orderbook_delta":
                    msg = KalshiDeltaMessage.model_validate(data).msg
                    current_size = self._books_state[market_ticker][msg.side].get(msg.price, 0)
                    new_size = current_size + msg.delta
                    self._books_state[market_ticker][msg.side][msg.price] = new_size
                    if new_size < 0:
                        self.logger.error(f"[Kalshi] Negative size calculated for {market_ticker}: {new_size}")
                        continue

                    price_decimal = Decimal(msg.price) / 100
                    if msg.side == 'yes':
                        side = SIDES.BUY
                    else:
                        side = SIDES.SELL
                        price_decimal = Decimal(1) - price_decimal

                    event = OrderBookDeltaReceived(
                        platform=Platform.KALSHI, market_id=common_market_id, outcome="YES",
                        side=side, price=price_decimal, size=Decimal(new_size)
                    )

                if event:
                    await self.bus.publish(event)

            except json.JSONDecodeError:
                self.logger.warning(
                    "[Kalshi] Failed to parse JSON message",
                    extra={"raw_message": raw_message},
                    exc_info=True
                )
            except ValidationError as e:
                self.logger.warning(
                    f"[Kalshi] Invalid message structure for {market_ticker}",
                    extra={"raw_message": raw_message, "error": str(e)},
                    exc_info=True
                )
                # If a snapshot is invalid, it corrupts our state.
                # The safest action is to request a fresh start for that market.
                if market_ticker and "KalshiSnapshotMessage" in str(e):
                    self.logger.error(
                        f"[Kalshi] Incomplete snapshot for {market_ticker}. "
                        "Requesting resubscription to ensure data integrity."
                    )
                    await self._request_resubscribe(market_ticker)
            except Exception:
                self.logger.exception("[Kalshi] Failed to process message", extra={"raw_message": raw_message})

    @require_initialized
    async def _is_sequence_valid(self, seq: Optional[int]) -> bool:
        """
        Checks if the message's sequence number is valid for the entire subscription.
        """
        if seq is None:
            self.logger.warning("[Kalshi] Message has no sequence number.")
            return False

        async with self._lock:
            last_seq = self._last_seq.get(self.SHARED_SEQ_KEY, 0)

            # The first message must have seq=1. After that, it must be strictly sequential.
            expected_seq = last_seq + 1
            if seq == expected_seq:
                self._last_seq[self.SHARED_SEQ_KEY] = seq
                return True

            # Allow the very first message to be a snapshot that sets the baseline.
            # This handles the initial connection where seq starts at 1.
            if last_seq == 0 and seq == 1:
                self._last_seq[self.SHARED_SEQ_KEY] = seq
                return True

            self.logger.error(f"[Kalshi] Sequence gap for subscription: got {seq}, expected {expected_seq}.")
            return False

    async def _request_resubscribe(self, ticker: str) -> None:
        """Handles a sequence gap by clearing the book and restarting the connection."""
        self.logger.warning(f"[Kalshi] Requesting resubscription for ALL markets due to sequence gap on {ticker}.")
        # Closing the connection will trigger the reconnection logic in connect_forever()
        if self._ws:
            try:
                await self._ws.close(code=4000, reason=f"subscription-seq-gap")
            except Exception as e:
                self.logger.error(f"[Kalshi] Error closing websocket: {e}")
