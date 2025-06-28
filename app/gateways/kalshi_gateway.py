import asyncio
from typing import List, Dict, Any

from app.clients.kalshi import KalshiHttpClient
from app.gateways.market_data_gateway import MarketDataGateway


class KalshiGateway(MarketDataGateway):
    def __init__(self, http_client: KalshiHttpClient):
        self.client = http_client

    async def get_markets_by_id(self, ids: List[str]) -> List[Dict[str, Any]]:
        tickers_str = ",".join(ids)
        response = await asyncio.to_thread(self.client.get_specific_markets, tickers_str)
        return response.get("markets", [])