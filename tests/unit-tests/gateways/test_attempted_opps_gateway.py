import unittest
from unittest.mock import MagicMock

from decimal import Decimal
from datetime import datetime, timezone

from app.clients.supabase import SupabaseClient
from app.domain.primitives import Platform
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.domain.models.opportunity import ArbitrageOpportunity, ArbitrageOpportunityRecord
from tests.sample_data import DUMMY_ARB_OPPORTUNITY_BUY_BOTH, DUMMY_ARB_OPP_RECORD_ERROR_CASE


class TestAttemptedOpportunityGateway(unittest.TestCase):
    def setUp(self):
        db_client = SupabaseClient()
        self.att_opp_gtwy = AttemptedOpportunitiesGateway(db_client.client)
        self.att_opp_gtwy._table_name = "attempted_opportunities_test"
        # test data
        self.dummy_opportunity = DUMMY_ARB_OPPORTUNITY_BUY_BOTH

        self.dummy_opp_record = DUMMY_ARB_OPP_RECORD_ERROR_CASE

    def tearDown(self):
        pass

    def test_serialize_attempted_arb_opportunities(self):
        mock_opportunity_1 = MagicMock(spec=ArbitrageOpportunityRecord)
        mock_opportunity_2 = MagicMock(spec=ArbitrageOpportunityRecord)

        mock_opportunity_1.serialize.return_value = {"id": 1}
        mock_opportunity_2.serialize.return_value = {"id": 2}

        result = AttemptedOpportunitiesGateway.serialize_opportunities([mock_opportunity_1, mock_opportunity_2])

        assert result == [{"id": 1}, {"id": 2}]
        mock_opportunity_1.serialize.assert_called_once()
        mock_opportunity_2.serialize.assert_called_once()

    def test_basic_fetch_returns_proper_type(self):
        res = self.att_opp_gtwy.get_attempted_opportunities()
        print("response is ", res)
        assert isinstance(res, list)

    def test_adding_one_attempted_opportunity_happy_path_returns_same_object(self):
        # act
        result = self.att_opp_gtwy.add_attempted_opportunities_repository([self.dummy_opp_record])
        raw_data = result.data[0]
        # assert
        assert result is not None
        assert hasattr(result, "data")
        assert result.data is not None
        assert len(result.data) == 1
        try:
            arbitrage_opportunity = ArbitrageOpportunityRecord(**raw_data)
            assert arbitrage_opportunity.arbitrage_opportunity== self.dummy_opp_record.arbitrage_opportunity
        except Exception as e:
            raise e