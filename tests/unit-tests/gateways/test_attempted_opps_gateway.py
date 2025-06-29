import unittest
from unittest.mock import MagicMock

from decimal import Decimal
from datetime import datetime, timezone

from app.clients.supabase import SupabaseClient
from app.domain.primitives import Platform
from app.gateways.attempted_opportunities_gateway import AttemptedOpportunitiesGateway
from app.domain.models.opportunity import ArbitrageOpportunity, ArbitrageOpportunityRecord


class TestAttemptedOpportunityGateway(unittest.TestCase):
    def setUp(self):
        db_client = SupabaseClient()
        self.att_opp_gtwy = AttemptedOpportunitiesGateway(db_client.client)
        # test data
        self.dummy_opportunity = ArbitrageOpportunity(
            market_id="test-market",
            buy_yes_platform=Platform.KALSHI,
            buy_yes_price=Decimal("0.27"),
            buy_no_platform=Platform.POLYMARKET,
            buy_no_price=Decimal("0.25"),
            profit_margin=Decimal("0.50"),
            potential_trade_size=Decimal("100.000"),
            kalshi_ticker="KXFEDCHAIRNOM-29-KW",
            polymarket_yes_token_id="yes-token-test",
            polymarket_no_token_id="no-token-test",
            kalshi_fees=None,
        )

        self.dummy_opp_record =  ArbitrageOpportunityRecord(
            arbitrage_opportunity=self.dummy_opportunity,
            category="test_category",
            market_books_snapshot={"bids": [], "asks": []},
            detected_at=datetime.now(timezone.utc),
            poly_trade_executed=False,
            poly_order_id="1234",
            kalshi_trade_executed=False,
            kalshi_order_id="5678"
        )
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
        assert isinstance(res, list)

    def test_adding_one_attempted_opportunity_happy_path_returns_same_object(self):
        result = self.att_opp_gtwy.add_attempted_opportunities_repository([self.dummy_opp_record])
        assert result is not None
        assert hasattr(result, "data")
        assert result.data is not None
        assert len(result.data) == 1

        raw_data = result.data[0]

        try:
            arbitrage_opportunity = ArbitrageOpportunityRecord(**raw_data)
            print("test resulti is", arbitrage_opportunity.arbitrage_opportunity)
            assert arbitrage_opportunity.arbitrage_opportunity== self.dummy_opp_record.arbitrage_opportunity
        except Exception as e:
            raise e