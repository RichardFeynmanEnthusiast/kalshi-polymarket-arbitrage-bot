""" Stores opportunities we have executed trades """
import logging
from typing import List

from app.domain.models.opportunity import ArbitrageOpportunityRecord
from app.settings.settings import settings


class AttemptedOpportunitiesGateway:
    def __init__(self, supabase_client):
        self.logger = logging.getLogger(__name__)
        self.db_client = supabase_client
        self._table_name = "attempted_opportunities" if settings.DRY_RUN else "attempted_opportunities_dry"

    @staticmethod
    def serialize_opportunities(arb_opportunities: List[ArbitrageOpportunityRecord]) -> List[dict]:
        return [arb_opp.serialize() for arb_opp in arb_opportunities]

    def add_attempted_opportunities_repository(self, attempted_opportunities: List[ArbitrageOpportunityRecord]):
        """ Handles adding multiple attempted arbitrage opportunities """
        try:
            res = self.db_client.table(self._table_name).insert(self.serialize_opportunities(attempted_opportunities)).execute()
            return res
        except Exception as e:
            self.logger.error(f"Failed to insert opportunities. Detail: {e}")
    
    def get_attempted_opportunities(self) -> List[ArbitrageOpportunityRecord]:
        """ Get all attempted opportunities """
        try:
            res = self.db_client.table(self._table_name).select("*").execute()
            return [ArbitrageOpportunityRecord(**item) for item in res.data]
        except Exception as e:
            self.logger.error(f"Failed to get attempted opportunities. Detail: {e}")
            raise e