# This repository handles any DB or API regarding matches or market pairs (user matches)

import logging
from typing import List

from app.domain.models.match_models import MarketPair
from app.utils.exceptions import NoDataFound


class MatchesRepository:
    def __init__(self, supabase_client):
        self.logger = logging.getLogger(__name__)
        self.db_client = supabase_client
        self._table_name = "matched_markets"

    def get_market_pairs(self, market_tuples: List[tuple]) -> List[MarketPair]:
        """
        Constructs a list of MarketPair objects from a list of tuples
        provided at runtime.
        """
        if not market_tuples:
            raise NoDataFound(message="No market pairs were provided to trade.")

        # Convert the raw tuples into our domain model
        return [MarketPair(poly_id=t[0], kalshi_ticker=t[1]) for t in market_tuples]