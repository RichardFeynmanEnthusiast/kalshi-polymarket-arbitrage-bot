from abc import ABC, abstractmethod
from typing import List, Dict, Any


class MarketDataGateway(ABC):
    @abstractmethod
    async def get_markets_by_id(self, ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetches market details for a list of platform-specific IDs
        """
        pass
