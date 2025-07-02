from decimal import Decimal
from sortedcontainers import SortedDict
from typing import Dict

from app.domain.events import OrderBookSnapshotReceived, PriceLevelData
from app.domain.primitives import Money as pMoney
from shared_wallets.domain.types import Currency, Money
from shared_wallets.domain.models import ExchangeWallet, Exchange

from app.domain.models.opportunity import ArbitrageOpportunity
from app.domain.primitives import Platform
from app.domain.types import Wallets
from app.markets.order_book import Orderbook
from app.markets.state import MarketState, MarketOutcomes

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
            polymarket_no_token_id="no-token",
            kalshi_fees= pMoney("0.00")
        )

# --- Dummy wallet amounts

KALSHI_BALANCE : Dict[Currency, Money] = {
    Currency.USD: Money(Decimal("100.00"), Currency.USD),
}
POLYMARKET_BALANCE : Dict[Currency, Money] = {
    Currency.USDC_E: Money(Decimal("50.00"), Currency.USDC_E),
    Currency.POL: Money(Decimal("85.00"), Currency.POL),
}
POLYMARKET_WALLET = ExchangeWallet(exchange=Exchange.POLYMARKET, balances=POLYMARKET_BALANCE)
KALSHI_WALLET = ExchangeWallet(exchange=Exchange.KALSHI, balances=KALSHI_BALANCE)

VALID_WALLETS_LARGER_KALSHI= Wallets(
    kalshi_wallet=KALSHI_WALLET,
    polymarket_wallet=POLYMARKET_WALLET,
)

POLYMARKET_BALANCE : Dict[Currency, Money] = {
    Currency.USDC_E: Money(Decimal("1000.00"), Currency.USDC_E),
    Currency.POL: Money(Decimal("85.00"), Currency.POL),
}
POLYMARKET_WALLET = ExchangeWallet(exchange=Exchange.POLYMARKET, balances=POLYMARKET_BALANCE)

VALID_WALLETS_LARGER_POLY= Wallets(
    kalshi_wallet=KALSHI_WALLET,
    polymarket_wallet=POLYMARKET_WALLET,
)

POLYMARKET_BALANCE : Dict[Currency, Money] = {
    Currency.USDC_E: Money(Decimal("100.00"), Currency.USDC_E),
    Currency.POL: Money(Decimal("85.00"), Currency.POL),
}
POLYMARKET_WALLET = ExchangeWallet(exchange=Exchange.POLYMARKET, balances=POLYMARKET_BALANCE)

VALID_WALLETS_EQUAL= Wallets(
    kalshi_wallet=KALSHI_WALLET,
    polymarket_wallet=POLYMARKET_WALLET,
)

# --- Dummy Market book snapshot

# data below based on snapshot: 2025-07-01 11:49:35 - app.markets.manager - INFO - Handling full book snapshot: message_id=UUID('8cdfa34f-c496-4ecc-945c-9e369c26ea4a') timestamp=datetime.datetime(2025, 7, 1, 15, 49, 35, 563918, tzinfo=datetime.timezone.utc)
# platform=<Platform.POLYMARKET: 'POLYMARKET'> market_id='KXNEWPARTYMUSK-26' outcome='NO'
# bids=[PriceLevelData(price=Decimal('0.01'), size=Decimal('8350.12')), PriceLevelData(price=Decimal('0.02'), size=Decimal('3000')), PriceLevelData(price=Decimal('0.03'), size=Decimal('35172.96')), PriceLevelData(price=Decimal('0.04'), size=Decimal('1500')), PriceLevelData(price=Decimal('0.08'), size=Decimal('11111')), PriceLevelData(price=Decimal('0.09'), size=Decimal('51000')), PriceLevelData(price=Decimal('0.11'), size=Decimal('5500')), PriceLevelData(price=Decimal('0.12'), size=Decimal('350')), PriceLevelData(price=Decimal('0.13'), size=Decimal('2460')), PriceLevelData(price=Decimal('0.15'), size=Decimal('2181')), PriceLevelData(price=Decimal('0.24'), size=Decimal('5000')), PriceLevelData(price=Decimal('0.25'), size=Decimal('5016')), PriceLevelData(price=Decimal('0.28'), size=Decimal('100')), PriceLevelData(price=Decimal('0.3'), size=Decimal('10')), PriceLevelData(price=Decimal('0.36'), size=Decimal('100')), PriceLevelData(price=Decimal('0.37'), size=Decimal('80')), PriceLevelData(price=Decimal('0.39'), size=Decimal('5555')), PriceLevelData(price=Decimal('0.4'), size=Decimal('200')), PriceLevelData(price=Decimal('0.41'), size=Decimal('650')), PriceLevelData(price=Decimal('0.42'), size=Decimal('29.8')), PriceLevelData(price=Decimal('0.44'), size=Decimal('150.11')), PriceLevelData(price=Decimal('0.45'), size=Decimal('999')), PriceLevelData(price=Decimal('0.47'), size=Decimal('450')), PriceLevelData(price=Decimal('0.48'), size=Decimal('50')), PriceLevelData(price=Decimal('0.49'), size=Decimal('141.44')), PriceLevelData(price=Decimal('0.5'), size=Decimal('60')), PriceLevelData(price=Decimal('0.51'), size=Decimal('760')), PriceLevelData(price=Decimal('0.52'), size=Decimal('508.06')), PriceLevelData(price=Decimal('0.54'), size=Decimal('18'))]
# asks=[PriceLevelData(price=Decimal('0.99'), size=Decimal('50026.17')), PriceLevelData(price=Decimal('0.98'), size=Decimal('15200')), PriceLevelData(price=Decimal('0.97'), size=Decimal('5000')), PriceLevelData(price=Decimal('0.96'), size=Decimal('2400')), PriceLevelData(price=Decimal('0.95'), size=Decimal('51500')), PriceLevelData(price=Decimal('0.94'), size=Decimal('1533')), PriceLevelData(price=Decimal('0.93'), size=Decimal('900')), PriceLevelData(price=Decimal('0.92'), size=Decimal('2223.86')), PriceLevelData(price=Decimal('0.91'), size=Decimal('310')), PriceLevelData(price=Decimal('0.9'), size=Decimal('16118.83')), PriceLevelData(price=Decimal('0.89'), size=Decimal('300')), PriceLevelData(price=Decimal('0.88'), size=Decimal('15000')), PriceLevelData(price=Decimal('0.87'), size=Decimal('1230')), PriceLevelData(price=Decimal('0.86'), size=Decimal('176.52')), PriceLevelData(price=Decimal('0.8'), size=Decimal('60')), PriceLevelData(price=Decimal('0.79'), size=Decimal('500')), PriceLevelData(price=Decimal('0.78'), size=Decimal('215')), PriceLevelData(price=Decimal('0.77'), size=Decimal('3694.06')), PriceLevelData(price=Decimal('0.76'), size=Decimal('400.16')), PriceLevelData(price=Decimal('0.75'), size=Decimal('266.28')), PriceLevelData(price=Decimal('0.74'), size=Decimal('29.8')), PriceLevelData(price=Decimal('0.72'), size=Decimal('41.62')), PriceLevelData(price=Decimal('0.71'), size=Decimal('320.16')), PriceLevelData(price=Decimal('0.7'), size=Decimal('100')), PriceLevelData(price=Decimal('0.69'), size=Decimal('50')), PriceLevelData(price=Decimal('0.67'), size=Decimal('65')), PriceLevelData(price=Decimal('0.65'), size=Decimal('100')), PriceLevelData(price=Decimal('0.64'), size=Decimal('10077.75')), PriceLevelData(price=Decimal('0.63'), size=Decimal('857.01')), PriceLevelData(price=Decimal('0.6'), size=Decimal('513')), PriceLevelData(price=Decimal('0.59'), size=Decimal('333')), PriceLevelData(price=Decimal('0.58'), size=Decimal('333')), PriceLevelData(price=Decimal('0.57'), size=Decimal('376.29')), PriceLevelData(price=Decimal('0.56'), size=Decimal('273.56')), PriceLevelData(price=Decimal('0.55'), size=Decimal('415.9'))]

# 2025-07-01 11:49:35 - app.markets.manager - INFO - Corresponding market state:
# market_id='KXNEWPARTYMUSK-26' platforms={<Platform.KALSHI: 'KALSHI'>:
# MarketOutcomes(yes=<app.markets.order_book.Orderbook object at 0x10706ce50>, no=None),
# <Platform.POLYMARKET: 'POLYMARKET'>: MarketOutcomes(yes=<app.markets.order_book.Orderbook object at 0x10739dd10>, no=<app.markets.order_book.Orderbook object at 0x1073b6550>)}

# 2025-07-01 11:49:35 - app.markets.manager - INFO - Platform outcomes:
# yes={'market_id': 'KXNEWPARTYMUSK-26-POLY-YES',
# 'bids': SortedDict(<function Orderbook.__init__.<locals>.<lambda> at 0x10737a5c0>, {Decimal('0.45'): Decimal('415.9'), Decimal('0.44'): Decimal('273.56'), Decimal('0.43'): Decimal('376.29'), Decimal('0.42'): Decimal('333'), Decimal('0.41'): Decimal('333'), Decimal('0.4'): Decimal('513'), Decimal('0.37'): Decimal('857.01'), Decimal('0.36'): Decimal('10077.75'), Decimal('0.35'): Decimal('100'), Decimal('0.33'): Decimal('65'), Decimal('0.31'): Decimal('50'), Decimal('0.3'): Decimal('100'), Decimal('0.29'): Decimal('320.16'), Decimal('0.28'): Decimal('41.62'), Decimal('0.26'): Decimal('29.8'), Decimal('0.25'): Decimal('266.28'), Decimal('0.24'): Decimal('400.16'), Decimal('0.23'): Decimal('3694.06'), Decimal('0.22'): Decimal('215'), Decimal('0.21'): Decimal('500'), Decimal('0.2'): Decimal('60'), Decimal('0.14'): Decimal('176.52'), Decimal('0.13'): Decimal('1230'), Decimal('0.12'): Decimal('15000'), Decimal('0.11'): Decimal('300'), Decimal('0.1'): Decimal('16118.83'), Decimal('0.09'): Decimal('310'), Decimal('0.08'): Decimal('2223.86'), Decimal('0.07'): Decimal('900'), Decimal('0.06'): Decimal('1533'), Decimal('0.05'): Decimal('51500'), Decimal('0.04'): Decimal('2400'), Decimal('0.03'): Decimal('5000'), Decimal('0.02'): Decimal('15200'), Decimal('0.01'): Decimal('50026.17')}),
# 'asks': SortedDict({Decimal('0.46'): Decimal('18'), Decimal('0.48'): Decimal('508.06'), Decimal('0.49'): Decimal('760'), Decimal('0.5'): Decimal('60'), Decimal('0.51'): Decimal('141.44'), Decimal('0.52'): Decimal('50'), Decimal('0.53'): Decimal('450'), Decimal('0.55'): Decimal('999'), Decimal('0.56'): Decimal('150.11'), Decimal('0.58'): Decimal('29.8'), Decimal('0.59'): Decimal('650'), Decimal('0.6'): Decimal('200'), Decimal('0.61'): Decimal('5555'), Decimal('0.63'): Decimal('80'), Decimal('0.64'): Decimal('100'), Decimal('0.7'): Decimal('10'), Decimal('0.72'): Decimal('100'), Decimal('0.75'): Decimal('5016'), Decimal('0.76'): Decimal('5000'), Decimal('0.85'): Decimal('2181'), Decimal('0.87'): Decimal('2460'), Decimal('0.88'): Decimal('350'), Decimal('0.89'): Decimal('5500'), Decimal('0.91'): Decimal('51000'), Decimal('0.92'): Decimal('11111'), Decimal('0.96'): Decimal('1500'), Decimal('0.97'): Decimal('35172.96'), Decimal('0.98'): Decimal('3000'), Decimal('0.99'): Decimal('8350.12')}), 'last_update': datetime.datetime(2025, 7, 1, 15, 49, 35, 568105, tzinfo=datetime.timezone.utc)},
# no={'no': <app.markets.order_book.Orderbook object at 0x1073b6550>}

# 2025-07-01 11:49:35 - app.markets.manager - INFO - Book outcome:
# {'market_id': 'KXNEWPARTYMUSK-26-POLY-NO',
# 'bids': SortedDict(<function Orderbook.__init__.<locals>.<lambda> at 0x10737a700>, {Decimal('0.54'): Decimal('18'), Decimal('0.52'): Decimal('508.06'), Decimal('0.51'): Decimal('760'), Decimal('0.5'): Decimal('60'), Decimal('0.49'): Decimal('141.44'), Decimal('0.48'): Decimal('50'), Decimal('0.47'): Decimal('450'), Decimal('0.45'): Decimal('999'), Decimal('0.44'): Decimal('150.11'), Decimal('0.42'): Decimal('29.8'), Decimal('0.41'): Decimal('650'), Decimal('0.4'): Decimal('200'), Decimal('0.39'): Decimal('5555'), Decimal('0.37'): Decimal('80'), Decimal('0.36'): Decimal('100'), Decimal('0.3'): Decimal('10'), Decimal('0.28'): Decimal('100'), Decimal('0.25'): Decimal('5016'), Decimal('0.24'): Decimal('5000'), Decimal('0.15'): Decimal('2181'), Decimal('0.13'): Decimal('2460'), Decimal('0.12'): Decimal('350'), Decimal('0.11'): Decimal('5500'), Decimal('0.09'): Decimal('51000'), Decimal('0.08'): Decimal('11111'), Decimal('0.04'): Decimal('1500'), Decimal('0.03'): Decimal('35172.96'), Decimal('0.02'): Decimal('3000'), Decimal('0.01'): Decimal('8350.12')}),
# 'asks': SortedDict({Decimal('0.55'): Decimal('415.9'), Decimal('0.56'): Decimal('273.56'), Decimal('0.57'): Decimal('376.29'), Decimal('0.58'): Decimal('333'), Decimal('0.59'): Decimal('333'), Decimal('0.6'): Decimal('513'), Decimal('0.63'): Decimal('857.01'), Decimal('0.64'): Decimal('10077.75'), Decimal('0.65'): Decimal('100'), Decimal('0.67'): Decimal('65'), Decimal('0.69'): Decimal('50'), Decimal('0.7'): Decimal('100'), Decimal('0.71'): Decimal('320.16'), Decimal('0.72'): Decimal('41.62'), Decimal('0.74'): Decimal('29.8'), Decimal('0.75'): Decimal('266.28'), Decimal('0.76'): Decimal('400.16'), Decimal('0.77'): Decimal('3694.06'), Decimal('0.78'): Decimal('215'), Decimal('0.79'): Decimal('500'), Decimal('0.8'): Decimal('60'), Decimal('0.86'): Decimal('176.52'), Decimal('0.87'): Decimal('1230'), Decimal('0.88'): Decimal('15000'), Decimal('0.89'): Decimal('300'), Decimal('0.9'): Decimal('16118.83'), Decimal('0.91'): Decimal('310'), Decimal('0.92'): Decimal('2223.86'), Decimal('0.93'): Decimal('900'), Decimal('0.94'): Decimal('1533'), Decimal('0.95'): Decimal('51500'), Decimal('0.96'): Decimal('2400'), Decimal('0.97'): Decimal('5000'), Decimal('0.98'): Decimal('15200'), Decimal('0.99'): Decimal('50026.17')}), 'last_update': datetime.datetime(2025, 7, 1, 15, 49, 35, 568777, tzinfo=datetime.timezone.utc)}

DUMMY_POLY_BIDS = [PriceLevelData(price=Decimal('0.01'), size=Decimal('8350.12')), PriceLevelData(price=Decimal('0.02'), size=Decimal('3000')), PriceLevelData(price=Decimal('0.03'), size=Decimal('35172.96')), PriceLevelData(price=Decimal('0.04'), size=Decimal('1500')), PriceLevelData(price=Decimal('0.08'), size=Decimal('11111')), PriceLevelData(price=Decimal('0.09'), size=Decimal('51000')), PriceLevelData(price=Decimal('0.11'), size=Decimal('5500')), PriceLevelData(price=Decimal('0.12'), size=Decimal('350')), PriceLevelData(price=Decimal('0.13'), size=Decimal('2460')), PriceLevelData(price=Decimal('0.15'), size=Decimal('2181')), PriceLevelData(price=Decimal('0.24'), size=Decimal('5000')), PriceLevelData(price=Decimal('0.25'), size=Decimal('5016')), PriceLevelData(price=Decimal('0.28'), size=Decimal('100')), PriceLevelData(price=Decimal('0.3'), size=Decimal('10')), PriceLevelData(price=Decimal('0.36'), size=Decimal('100')), PriceLevelData(price=Decimal('0.37'), size=Decimal('80')), PriceLevelData(price=Decimal('0.39'), size=Decimal('5555')), PriceLevelData(price=Decimal('0.4'), size=Decimal('200')), PriceLevelData(price=Decimal('0.41'), size=Decimal('650')), PriceLevelData(price=Decimal('0.42'), size=Decimal('29.8')), PriceLevelData(price=Decimal('0.44'), size=Decimal('150.11')), PriceLevelData(price=Decimal('0.45'), size=Decimal('999')), PriceLevelData(price=Decimal('0.47'), size=Decimal('450')), PriceLevelData(price=Decimal('0.48'), size=Decimal('50')), PriceLevelData(price=Decimal('0.49'), size=Decimal('141.44')), PriceLevelData(price=Decimal('0.5'), size=Decimal('60')), PriceLevelData(price=Decimal('0.51'), size=Decimal('760')), PriceLevelData(price=Decimal('0.52'), size=Decimal('508.06')), PriceLevelData(price=Decimal('0.54'), size=Decimal('18'))]
DUMMY_POLY_ASKS = [PriceLevelData(price=Decimal('0.99'), size=Decimal('50026.17')), PriceLevelData(price=Decimal('0.98'), size=Decimal('15200')), PriceLevelData(price=Decimal('0.97'), size=Decimal('5000')), PriceLevelData(price=Decimal('0.96'), size=Decimal('2400')), PriceLevelData(price=Decimal('0.95'), size=Decimal('51500')), PriceLevelData(price=Decimal('0.94'), size=Decimal('1533')), PriceLevelData(price=Decimal('0.93'), size=Decimal('900')), PriceLevelData(price=Decimal('0.92'), size=Decimal('2223.86')), PriceLevelData(price=Decimal('0.91'), size=Decimal('310')), PriceLevelData(price=Decimal('0.9'), size=Decimal('16118.83')), PriceLevelData(price=Decimal('0.89'), size=Decimal('300')), PriceLevelData(price=Decimal('0.88'), size=Decimal('15000')), PriceLevelData(price=Decimal('0.87'), size=Decimal('1230')), PriceLevelData(price=Decimal('0.86'), size=Decimal('176.52')), PriceLevelData(price=Decimal('0.8'), size=Decimal('60')), PriceLevelData(price=Decimal('0.79'), size=Decimal('500')), PriceLevelData(price=Decimal('0.78'), size=Decimal('215')), PriceLevelData(price=Decimal('0.77'), size=Decimal('3694.06')), PriceLevelData(price=Decimal('0.76'), size=Decimal('400.16')), PriceLevelData(price=Decimal('0.75'), size=Decimal('266.28')), PriceLevelData(price=Decimal('0.74'), size=Decimal('29.8')), PriceLevelData(price=Decimal('0.72'), size=Decimal('41.62')), PriceLevelData(price=Decimal('0.71'), size=Decimal('320.16')), PriceLevelData(price=Decimal('0.7'), size=Decimal('100')), PriceLevelData(price=Decimal('0.69'), size=Decimal('50')), PriceLevelData(price=Decimal('0.67'), size=Decimal('65')), PriceLevelData(price=Decimal('0.65'), size=Decimal('100')), PriceLevelData(price=Decimal('0.64'), size=Decimal('10077.75')), PriceLevelData(price=Decimal('0.63'), size=Decimal('857.01')), PriceLevelData(price=Decimal('0.6'), size=Decimal('513')), PriceLevelData(price=Decimal('0.59'), size=Decimal('333')), PriceLevelData(price=Decimal('0.58'), size=Decimal('333')), PriceLevelData(price=Decimal('0.57'), size=Decimal('376.29')), PriceLevelData(price=Decimal('0.56'), size=Decimal('273.56')), PriceLevelData(price=Decimal('0.55'), size=Decimal('415.9'))]

SAMPLE_POLY_ORDERBOOK_RECEIVED = OrderBookSnapshotReceived(
    platform=Platform.POLYMARKET,
    market_id="test-market",
    outcome='YES',
    bids=DUMMY_POLY_BIDS,
    asks=DUMMY_POLY_ASKS,
)

POLY_YES_ORDERBOOK = Orderbook(
    market_id="KXNEWPARTYMUSK-26-POLY-YES",
)

POLY_YES_ORDERBOOK.bids = SortedDict({Decimal('0.45'): Decimal('415.9'), Decimal('0.44'): Decimal('273.56'), Decimal('0.43'): Decimal('376.29'), Decimal('0.42'): Decimal('333'), Decimal('0.41'): Decimal('333'), Decimal('0.4'): Decimal('513'), Decimal('0.37'): Decimal('857.01'), Decimal('0.36'): Decimal('10077.75'), Decimal('0.35'): Decimal('100'), Decimal('0.33'): Decimal('65'), Decimal('0.31'): Decimal('50'), Decimal('0.3'): Decimal('100'), Decimal('0.29'): Decimal('320.16'), Decimal('0.28'): Decimal('41.62'), Decimal('0.26'): Decimal('29.8'), Decimal('0.25'): Decimal('266.28'), Decimal('0.24'): Decimal('400.16'), Decimal('0.23'): Decimal('3694.06'), Decimal('0.22'): Decimal('215'), Decimal('0.21'): Decimal('500'), Decimal('0.2'): Decimal('60'), Decimal('0.14'): Decimal('176.52'), Decimal('0.13'): Decimal('1230'), Decimal('0.12'): Decimal('15000'), Decimal('0.11'): Decimal('300'), Decimal('0.1'): Decimal('16118.83'), Decimal('0.09'): Decimal('310'), Decimal('0.08'): Decimal('2223.86'), Decimal('0.07'): Decimal('900'), Decimal('0.06'): Decimal('1533'), Decimal('0.05'): Decimal('51500'), Decimal('0.04'): Decimal('2400'), Decimal('0.03'): Decimal('5000'), Decimal('0.02'): Decimal('15200'), Decimal('0.01'): Decimal('50026.17')})
POLY_YES_ORDERBOOK.asks = SortedDict({Decimal('0.46'): Decimal('18'), Decimal('0.48'): Decimal('508.06'), Decimal('0.49'): Decimal('760'), Decimal('0.5'): Decimal('60'), Decimal('0.51'): Decimal('141.44'), Decimal('0.52'): Decimal('50'), Decimal('0.53'): Decimal('450'), Decimal('0.55'): Decimal('999'), Decimal('0.56'): Decimal('150.11'), Decimal('0.58'): Decimal('29.8'), Decimal('0.59'): Decimal('650'), Decimal('0.6'): Decimal('200'), Decimal('0.61'): Decimal('5555'), Decimal('0.63'): Decimal('80'), Decimal('0.64'): Decimal('100'), Decimal('0.7'): Decimal('10'), Decimal('0.72'): Decimal('100'), Decimal('0.75'): Decimal('5016'), Decimal('0.76'): Decimal('5000'), Decimal('0.85'): Decimal('2181'), Decimal('0.87'): Decimal('2460'), Decimal('0.88'): Decimal('350'), Decimal('0.89'): Decimal('5500'), Decimal('0.91'): Decimal('51000'), Decimal('0.92'): Decimal('11111'), Decimal('0.96'): Decimal('1500'), Decimal('0.97'): Decimal('35172.96'), Decimal('0.98'): Decimal('3000'), Decimal('0.99'): Decimal('8350.12')})

POLY_NO_ORDERBOOK = Orderbook(
    market_id="KXNEWPARTYMUSK-26-POLY-NO",
)

POLY_NO_ORDERBOOK.bids = SortedDict({Decimal('0.54'): Decimal('18'), Decimal('0.52'): Decimal('508.06'), Decimal('0.51'): Decimal('760'), Decimal('0.5'): Decimal('60'), Decimal('0.49'): Decimal('141.44'), Decimal('0.48'): Decimal('50'), Decimal('0.47'): Decimal('450'), Decimal('0.45'): Decimal('999'), Decimal('0.44'): Decimal('150.11'), Decimal('0.42'): Decimal('29.8'), Decimal('0.41'): Decimal('650'), Decimal('0.4'): Decimal('200'), Decimal('0.39'): Decimal('5555'), Decimal('0.37'): Decimal('80'), Decimal('0.36'): Decimal('100'), Decimal('0.3'): Decimal('10'), Decimal('0.28'): Decimal('100'), Decimal('0.25'): Decimal('5016'), Decimal('0.24'): Decimal('5000'), Decimal('0.15'): Decimal('2181'), Decimal('0.13'): Decimal('2460'), Decimal('0.12'): Decimal('350'), Decimal('0.11'): Decimal('5500'), Decimal('0.09'): Decimal('51000'), Decimal('0.08'): Decimal('11111'), Decimal('0.04'): Decimal('1500'), Decimal('0.03'): Decimal('35172.96'), Decimal('0.02'): Decimal('3000'), Decimal('0.01'): Decimal('8350.12')})
POLY_NO_ORDERBOOK.asks = SortedDict({Decimal('0.55'): Decimal('415.9'), Decimal('0.56'): Decimal('273.56'), Decimal('0.57'): Decimal('376.29'), Decimal('0.58'): Decimal('333'), Decimal('0.59'): Decimal('333'), Decimal('0.6'): Decimal('513'), Decimal('0.63'): Decimal('857.01'), Decimal('0.64'): Decimal('10077.75'), Decimal('0.65'): Decimal('100'), Decimal('0.67'): Decimal('65'), Decimal('0.69'): Decimal('50'), Decimal('0.7'): Decimal('100'), Decimal('0.71'): Decimal('320.16'), Decimal('0.72'): Decimal('41.62'), Decimal('0.74'): Decimal('29.8'), Decimal('0.75'): Decimal('266.28'), Decimal('0.76'): Decimal('400.16'), Decimal('0.77'): Decimal('3694.06'), Decimal('0.78'): Decimal('215'), Decimal('0.79'): Decimal('500'), Decimal('0.8'): Decimal('60'), Decimal('0.86'): Decimal('176.52'), Decimal('0.87'): Decimal('1230'), Decimal('0.88'): Decimal('15000'), Decimal('0.89'): Decimal('300'), Decimal('0.9'): Decimal('16118.83'), Decimal('0.91'): Decimal('310'), Decimal('0.92'): Decimal('2223.86'), Decimal('0.93'): Decimal('900'), Decimal('0.94'): Decimal('1533'), Decimal('0.95'): Decimal('51500'), Decimal('0.96'): Decimal('2400'), Decimal('0.97'): Decimal('5000'), Decimal('0.98'): Decimal('15200'), Decimal('0.99'): Decimal('50026.17')})

KALSHI_YES_ORDERBOOK = Orderbook(market_id="KXNEWPARTYMUSK-26-Kalshi-YES")

SAMPLE_MARKET_STATES : Dict[str, MarketState] = {
    'KXNEWPARTYMUSK-26' : MarketState(
        market_id="KXNEWPARTYMUSK-26",
        platforms={
            Platform.KALSHI : MarketOutcomes(
                yes=KALSHI_YES_ORDERBOOK,
                no=None
            ),
            Platform.POLYMARKET : MarketOutcomes(
                yes=POLY_YES_ORDERBOOK,
                no=POLY_NO_ORDERBOOK,
            )
        }
    )
}

SAMPLE_MARKET_STATE = SAMPLE_MARKET_STATES['KXNEWPARTYMUSK-26']
