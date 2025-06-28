import unittest
from app.utils.infra import polygon_net
import os

class TestPolyNet(unittest.TestCase):
    def setUp(self):
        self.utils = polygon_net
        self.valid_wallet_addr = os.getenv("POLYMARKET_WALLET_ADDR")
        pass
    def tearDown(self):
        pass
    def test_valid_address_returns_true(self):
        assert self.utils.valid_eth_wallet_addr(self.valid_wallet_addr)
    def test_get_matic_balance_return_balance_with_valid_address(self):
        balance_in_wei = self.utils.get_matic_balance(self.valid_wallet_addr)
        pol = balance_in_wei / 1e18 # amount of polygon's gas token (POL, previously Matic)
        print(f"{pol:.5f} POL") # no error, test passes
    def test_get_usdc_e_balance_return_balance(self):
        usdc_e_balance = self.utils.get_usdc_e_balance(self.valid_wallet_addr)
        print(f"USDC_e Balance: {usdc_e_balance}")
    def test_get_usdc_balance_returns_balance(self):
        usdc_balance = self.utils.get_usdc_balance(self.valid_wallet_addr)
        print(f"USDC Balance: {usdc_balance}")
    def test_estimate_gas_returns_gas_estimate(self):
        amount_to_send = 5.00
        estimated_gas = self.utils.estimate_gas(amount_to_send, self.valid_wallet_addr)
        print(f"Gas Estimate: {estimated_gas}")