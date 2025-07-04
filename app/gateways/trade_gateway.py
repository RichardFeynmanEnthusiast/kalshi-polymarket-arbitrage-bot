from decimal import Decimal
from typing import Dict, Any, Optional

from py_clob_client.clob_types import OrderType
from pydantic import ValidationError

from app.clients.kalshi.kalshi_http_client import KalshiHttpClient
from app.clients.polymarket.clob_http import PolymClobHttpClient
from app.domain.primitives import KalshiSide, PolySide
from app.domain.types import KalshiOrder, PolymarketOrder

class TradeGateway:
    """
    A repository for handling the low-level placement of trades on exchanges.
    This class translates our internal models into specific API calls.
    """
    def __init__(self, kalshi_http: KalshiHttpClient, polymarket_http: PolymClobHttpClient):
        self.kalshi = kalshi_http
        self.polymarket = polymarket_http

    async def place_kalshi_order(
            self,
            ticker: str,
            side: KalshiSide,
            count: int,
            price_in_cents: int,
            client_order_id: str,
            action: str = "buy"
    ) -> KalshiOrder:
        """
        Places a limit order on Kalshi.
        Kalshi requires order sizes to be whole integers and prices in cents.
        """
        price_param = {"yes_price": price_in_cents} if side == KalshiSide.YES else {"no_price": price_in_cents}
        resp = await self.kalshi.create_order(
            action=action,
            side=side.value,
            type="limit",
            ticker=ticker,
            count=count,
            client_order_id=client_order_id,
            **price_param
        )

        return self.process_raw_kalshi_order(resp, trade_size=Decimal(count))

    async def place_polymarket_order(
            self,
            token_id: str,
            price: Decimal,
            size: float,
            side: PolySide
    ) -> PolymarketOrder:
        """
        Places a Fill-Or-Kill (FOK) limit order on Polymarket.
        """

        resp = await self.polymarket.place_order(
            token_id=token_id,
            price=float(price),
            size=size,
            side=side.value,
            order_type=OrderType.FOK
        )

        return self.process_raw_polymarket_order(resp, token_id)

    async def place_kalshi_market_order(
            self,
            ticker: str,
            side: KalshiSide,
            count: int,
            client_order_id: str,
            action: str,
            buy_max_cost: Optional[int] = None
    ) -> KalshiOrder:
        """
        Places a true market order on Kalshi.
        """
        if action == "buy" and buy_max_cost is None:
            raise ValueError("buy_max_cost is required for a market buy order.")

        resp = await self.kalshi.create_order(
            action=action,
            side=side.value,
            type="market",
            ticker=ticker,
            count=count,
            client_order_id=client_order_id,
            buy_max_cost=buy_max_cost
        )
        return self.process_raw_kalshi_order(resp, trade_size=Decimal(count))

    async def place_polymarket_market_order(self, token_id: str, size: float, side: PolySide) -> PolymarketOrder:
        """
        Places a market order on Polymarket using an aggressive-priced FOK limit order,
        as per the official documentation.
        """
        # For a market SELL, set a very low price to guarantee it crosses the spread
        aggressive_price = 0.01 if side == PolySide.SELL else 0.99
        resp = await self.polymarket.place_order(
            token_id=token_id,
            price=float(aggressive_price),
            size=size,
            side=side.value,
            order_type=OrderType.FOK
        )
        return self.process_raw_polymarket_order(resp, token_id)


    @staticmethod
    def process_raw_kalshi_order(raw_data: Dict[str, Any], trade_size: Decimal) -> KalshiOrder:
        """
        Processes a raw Kalshi response and turns it into the KalshiOrder type.
        """
        try:
            order = raw_data.get("order", {})
            order = KalshiOrder.model_validate(order)
            order.trade_size = trade_size
            return order
        except (KeyError, ValidationError) as e:
            raise ValueError(f"Failed to process Kalshi order response: {e}") from e

    @staticmethod
    def process_raw_polymarket_order(raw_data: Dict[str, Any], token_id_to_add: str) -> PolymarketOrder:
        """
        Processes a raw Polymarket response and turns it into the PolymarketOrder type.
        """
        try:
            order = PolymarketOrder.model_validate(raw_data)
            order.trade_size = Decimal(raw_data.get("takerAmount", "0"))
            order.token_id = token_id_to_add
            return order
        except (KeyError, ValidationError) as e:
            raise ValueError(f"Failed to process Polymarket order response: {e}") from e