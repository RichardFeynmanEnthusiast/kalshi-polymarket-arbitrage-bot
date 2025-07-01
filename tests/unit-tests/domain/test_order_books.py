import copy
import unittest
from decimal import Decimal

from sortedcontainers import SortedDict

from app.domain.events import PriceLevelData
from app.domain.primitives import Side, SIDES
from app.markets.order_book import Orderbook
from tests.sample_data import POLY_YES_ORDERBOOK


class TestOrderBooks(unittest.TestCase):
    def setUp(self) -> None:
        pass
    def tearDown(self) -> None:
        pass

    def test_apply_updates_updates_book_correctly_for_one_new_entry(self):
        # adjust
        orderbook = Orderbook(market_id="dummy")
        orderbook.bids =  copy.deepcopy(POLY_YES_ORDERBOOK.bids)
        POLY_NEW_BIDS = [PriceLevelData(price=Decimal('0.45'), size=Decimal('8350.12'))]
        # act
        orderbook.apply_update(side=SIDES.BUY, price=POLY_NEW_BIDS[0].price, size=POLY_NEW_BIDS[0].size)
        # assert
        self.assertEqual(POLY_NEW_BIDS[0].size,orderbook.bids[Decimal('0.45')])

    def test_apply_update_bids_updates_book_correctly_for_multiple_entries(self):
        # adjust
        orderbook = Orderbook(market_id="dummy")
        orderbook.bids =  copy.deepcopy(POLY_YES_ORDERBOOK.bids)
        POLY_NEW_BIDS = [PriceLevelData(price=Decimal('0.45'), size=Decimal('8350.12')), PriceLevelData(price=Decimal('0.03'), size=Decimal('8300.12'))]
        # act
        for bid in POLY_NEW_BIDS:
            orderbook.apply_update(side=SIDES.BUY, price=bid.price, size=bid.size)
        # assert
        self.assertEqual(POLY_NEW_BIDS[0].size,orderbook.bids[Decimal('0.45')])
        self.assertEqual(POLY_NEW_BIDS[1].size, orderbook.bids[Decimal('0.03')])

    def test_apply_updates_updates_single_bid_book_currectly(self):
        # adjust
        orderbook = Orderbook(market_id="dummy")
        orderbook.bids =  copy.deepcopy(POLY_YES_ORDERBOOK.bids)
        POLY_NEW_BIDS = [PriceLevelData(price=Decimal('0.45'), size=Decimal('8350.12'))]
        # act
        updates = [(level.price, level.size) for level in POLY_NEW_BIDS]
        orderbook.apply_updates(side=SIDES.BUY, updates=updates)
        # assert
        self.assertEqual(POLY_NEW_BIDS[0].size,orderbook.bids[Decimal('0.45')])

    def test_apply_updates_updates_multiple_bid_books_correctly(self):
        # adjust
        orderbook = Orderbook(market_id="dummy")
        orderbook.bids =  copy.deepcopy(POLY_YES_ORDERBOOK.bids)
        POLY_NEW_BIDS = [PriceLevelData(price=Decimal('0.45'), size=Decimal('8350.12')), PriceLevelData(price=Decimal('0.03'), size=Decimal('8300.12'))]
        # act
        updates = [(level.price, level.size) for level in POLY_NEW_BIDS]
        orderbook.apply_updates(side=SIDES.BUY, updates=updates)
        # assert
        self.assertEqual(POLY_NEW_BIDS[0].size,orderbook.bids[Decimal('0.45')])
        self.assertEqual(POLY_NEW_BIDS[1].size, orderbook.bids[Decimal('0.03')])

    def test_apply_updates_updates_multiple_asks_books_correctly(self):
        # adjust
        orderbook = Orderbook(market_id="dummy")
        orderbook.asks =  copy.deepcopy(POLY_YES_ORDERBOOK.asks)
        POLY_NEW_ASKS = [PriceLevelData(price=Decimal('0.46'), size=Decimal('8350.12')), PriceLevelData(price=Decimal('0.48'), size=Decimal('8300.12'))]
        # act
        updates = [(level.price, level.size) for level in POLY_NEW_ASKS]
        orderbook.apply_updates(side=SIDES.SELL, updates=updates)
        # assert
        self.assertEqual(POLY_NEW_ASKS[0].size,orderbook.asks[Decimal('0.46')])
        self.assertEqual(POLY_NEW_ASKS[1].size, orderbook.asks[Decimal('0.48')])