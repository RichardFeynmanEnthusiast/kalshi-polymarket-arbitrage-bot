import asyncio
import json
import logging
from decimal import Decimal
from typing import List, Dict, Optional, Any

import websockets
from pydantic import ValidationError
from websockets.legacy.client import WebSocketClientProtocol

from app.clients.polymarket.poly_market_base import PolymBaseClient
from app.domain.events import PriceLevelData, OrderBookSnapshotReceived, OrderBookDeltaReceived
from app.domain.primitives import Platform, SIDES
from app.domain.models.venue_data_schemas import PolyBookMessage, PolyPriceChangeMessage
from app.settings.env import Environment
from app.message_bus import MessageBus
from app.utils.web_socket_utils import require_initialized


class PolymarketWebSocketClient(PolymBaseClient):
    """
    Handles connection, subscription, and data normalization for Polymarket.
    Publishes standardized Domain Events to the Message Bus.
    """
    MARKET_PATH = "/market"
    PLATFORM_NAME = "polymarket"

    def __init__(
        self,
        *,
        polym_wallet_pk: str | None = None,
        polym_clob_api_key: str | None = None,
        environment: Environment = Environment.DEMO,
        connection_timeout_seconds: int = 10,
    ) -> None:
        super().__init__(
            polym_wallet_pk=polym_wallet_pk,
            polym_clob_api_key=polym_clob_api_key,
            environment=environment.value,
        )
        self.asset_ids: Optional[List[str]] = None
        self.connection_timeout_seconds = connection_timeout_seconds
        self.bus: Optional[MessageBus] = None
        self.market_map: Optional[Dict[str, Dict[str, str]]] = None

        # internal state from your version
        self._ws: Optional[WebSocketClientProtocol] = None
        self.logger = logging.getLogger(__name__)

    def set_market_config(self, markets_config: List[Dict[str, str]]) -> None:
        new_map = {}
        for m in markets_config:
            if 'polymarket_yes_token_id' in m:
                new_map[m['polymarket_yes_token_id']] = {'id': m['id'], 'outcome': 'YES'}
            if 'polymarket_no_token_id' in m:
                new_map[m['polymarket_no_token_id']] = {'id': m['id'], 'outcome': 'NO'}
        self.market_map = new_map

    def set_asset_ids(self, asset_ids: List[str]) -> None:
        self.asset_ids = asset_ids

    def set_message_bus(self, bus: MessageBus) -> None:
        """Sets the message bus for publishing events."""
        self.bus = bus

    async def _process_and_publish_event(self, data: Dict[str, Any]):
        """Parses a raw message, creates a domain event, and publishes it to the bus."""
        if not self.bus:
            self.logger.error("[Polymarket] Message bus not set on PolymarketWebSocketClient")
            return

        asset_id = data.get("asset_id") or data.get("market")
        if not asset_id or not self.market_map or asset_id not in self.market_map:
            return

        market_info = self.market_map[asset_id]
        common_market_id = market_info['id']
        outcome = market_info['outcome']

        assert outcome in ('YES', 'NO'), f"Invalid outcome '{outcome}' found in market_map"

        event_type = data.get("event_type")

        try:
            if event_type == "book":
                msg = PolyBookMessage.model_validate(data)
                bids = [PriceLevelData(price=Decimal(level.price), size=Decimal(level.size)) for level in msg.bids]
                asks = [PriceLevelData(price=Decimal(level.price), size=Decimal(level.size)) for level in msg.asks]
                event = OrderBookSnapshotReceived(
                    platform=Platform.POLYMARKET, market_id=common_market_id, outcome=outcome, bids=bids, asks=asks
                )
                await self.bus.publish(event)
            elif event_type == "price_change":
                msg = PolyPriceChangeMessage.model_validate(data)
                for change in msg.changes:
                    event = OrderBookDeltaReceived(
                        platform=Platform.POLYMARKET, market_id=common_market_id, outcome=outcome,
                        side=SIDES.BUY if change.side == "BUY" else SIDES.SELL,
                        price=Decimal(change.price), size=Decimal(change.size)
                    )
                    await self.bus.publish(event)
        except ValidationError as e:
            self.logger.debug(f"[Polymarket] Ignoring Polymarket message due to validation error: {e}")
        except Exception:
            self.logger.exception(f"[Polymarket] Failed to process Polymarket message: {data}")

    @require_initialized
    async def connect_forever(self, channel_path: str) -> None:
        """Run forever, reconnecting on any failure."""
        host = self.CLOB_WS_BASE_URL.rstrip("/") + channel_path
        self.logger.info(f"[Polymarket] Attempting connection to {host}")
        while True:
            try:
                async with websockets.connect(host, ping_interval=15, ping_timeout=10) as ws:
                    self.logger.info("[Polymarket] Polymarket websocket connected")
                    self._ws = ws
                    if self.asset_ids:
                        await self._ws.send(json.dumps({"assets_ids": self.asset_ids, "type": "market"}))
                        self.logger.info(f"[Polymarket] Sent subscription request for asset IDs: {self.asset_ids}")
                    await self._handle_subscription_confirmation() # Wait for confirmation
                    self.logger.info("[Polymarket] Beginning listening process")
                    await self._listen() # Start listening for data
            except RuntimeError as e:
                self.logger.error(f"[Polymarket] Initialization error: {e}. The orchestrator may not have configured the client correctly. Retrying...")
            except Exception as exc:
                self.logger.error("[Polymarket] Polymarket WS error %s; reconnecting in 3 seconds", exc, exc_info=True)
            finally:
                self._ws = None
                await asyncio.sleep(3)

    @require_initialized
    async def _handle_subscription_confirmation(self) -> None:
        """Handles initial snapshot messages on subscription."""
        if not self._ws: return
        try:
            # Wait for the first message, which should be the confirmation.
            sub_message_raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
            messages = json.loads(sub_message_raw)
            for data in messages:
                await self._process_and_publish_event(data)
        except asyncio.TimeoutError:
            self.logger.warning("[Polymarket] Did not receive subscription confirmation from Polymarket within 10 seconds.")
        except Exception as e:
            self.logger.error(f"[Polymarket] Error processing subscription confirmation: {e}", exc_info=True)

    @require_initialized
    async def _listen(self) -> None:
        """Listen for data messages and emit domain events."""
        assert self._ws is not None
        async for raw_message in self._ws:
            if raw_message in {"PING", "PONG"}: continue
            try:
                messages = json.loads(raw_message)
                for data in messages:
                    await self._process_and_publish_event(data)
            except json.JSONDecodeError:
                self.logger.warning(f"[Polymarket] Received non-JSON message: {raw_message}")