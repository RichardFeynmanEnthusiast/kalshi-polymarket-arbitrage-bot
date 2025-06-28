from typing import List, Dict, Any

from app.clients.polymarket.gamma_http import PolymGammaClient
from app.gateways.market_data_gateway import MarketDataGateway

class PolymarketGateway(MarketDataGateway):
    def __init__(self, http_client: PolymGammaClient):
        self.client = http_client

    async def get_markets_by_id(self, ids: List[str]) -> List[Dict[str, Any]]:
        params = [{"id": market_id} for market_id in ids]
        response = await self.client.async_get_markets(params)
        return response