from decimal import Decimal

from app.domain.primitives import PolySide
from app.gateways.trade_gateway import TradeGateway
from app.utils.kalshi_client_factory import KalshiClientFactory
from app.utils.polymarket_client_factory import PolymarketClientFactory


def place_polymarket_trade(token_id : str):
    http_kalshi, _ = KalshiClientFactory()
    http_poly, _ = PolymarketClientFactory()
    trade_gateway = TradeGateway(http_kalshi, http_poly)
    trade_gateway.place_polymarket_order(token_id=token_id, price=Decimal("0.73"), size=2, side=PolySide.BUY)

if __name__ == '__main__':
    place_polymarket_trade(token_id="")
