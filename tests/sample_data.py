from decimal import Decimal

from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform

""" This file stores simulated data from API responses to use for testing"""


# --- Valid order responses from venue API endpoints  ---

DUMMY_VALID_KALSHI_ORDER_RESPONSE = {'order': {'order_id': '0155b151-0659-42a1-af85-52096518e4e6',
                                                      'user_id': 'd6982648-9e12-4be6-9c73-759ca49fab21',
                                                      'ticker': 'KXNBAGAME-25JUN19OKCIND-OKC', 'status': 'executed',
                                                      'yes_price': 68, 'no_price': 32,
                                                      'created_time': '2025-06-19T18:11:40.012766Z',
                                                      'expiration_time': None, 'self_trade_prevention_type': '',
                                                      'action': 'buy', 'side': 'yes', 'type': 'limit',
                                                      'client_order_id': 'e4e307b6-0f5b-4426-9797-515b84fd0d59',
                                                      'order_group_id': ''}}

DUMMY_VALID_POLYMARKET_ORDER_RESPONSE = {'errorMsg': '',
                                          'orderID': '0x2edf84dfc54d8d60e1c4549f01cf2e8ea73f6d284c75ebe648c9e2c4ba7c8d51',
                                          'takingAmount': '2.140844', 'makingAmount': '1.519999', 'status': 'matched',
                                          'transactionsHashes': [
                                              '0x6a701d6af2f1a524a78b61bf96313e5efad066ba7016f151f9bbfc395400a9ab'],
                                          'success': True}

# --- Dummy arbitrage opportunities

DUMMY_ARB_OPPORTUNITY_BUY_BOTH = ArbitrageOpportunity(
            market_id="test-market",
            buy_yes_platform=Platform.KALSHI,
            buy_yes_price=Decimal("0.27"),
            buy_no_platform=Platform.POLYMARKET,
            buy_no_price=Decimal("0.25"),
            profit_margin=Decimal("0.50"),
            potential_trade_size=Decimal("100.000"),
            kalshi_ticker="KXFEDCHAIRNOM-29-KW",
            polymarket_yes_token_id="yes-token",
            polymarket_no_token_id="no-token"
        )