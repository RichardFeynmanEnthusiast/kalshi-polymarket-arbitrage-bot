import unittest

from app.gateways.trade_gateway import TradeGateway
from app.utils.kalshi_client_factory import KalshiClientFactory
from app.utils.polymarket_client_factory import PolymarketClientFactory


class TestTradeGateways(unittest.TestCase):
    def setUp(self):
        http_kalshi, _ = KalshiClientFactory()
        http_poly, _ = PolymarketClientFactory()
        self.trade_gateway = TradeGateway(http_kalshi, http_poly)

    def tearDown(self):
        pass
