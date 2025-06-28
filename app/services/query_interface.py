from abc import ABC, abstractmethod
from typing import List

from app.markets.state import MarketState


class IMarketStateQuerier(ABC):
    """
    An abstract interface (a Port) for reading market state.
    Any service that needs to view the state of the markets can depend
    on this simple, stable interface instead of a complex concrete class.
    """
    @abstractmethod
    def get_all_market_states(self) -> List[MarketState]:
        """Returns a list of all current market state models."""
        pass