from decimal import Decimal
from typing import Dict
import math

from shared_wallets.domain.types import Currency, Money


class BalanceDataGateway:
    def __init__(self, clob_http_client, kalshi_http_client):
        self._clob_http_client = clob_http_client
        self._kalshi_http_client = kalshi_http_client

    def get_venue_balances(self) -> Dict[Currency, Money]:
        """ """
        try:
            usdc_e_bal, matic_bal = self._clob_http_client.get_starting_balances()
            raw_kalshi_balance = self._kalshi_http_client.get_balance()

            for balance in [usdc_e_bal, matic_bal]:
                if balance == 0:
                    raise ValueError(f"{balance} must be greater than zero")
                elif balance is None:
                    raise ValueError(f"{balance} not found")

            if raw_kalshi_balance.get('balance') == 0:
                raise ValueError(f"Kalshi balance must be greater than zero")
            elif raw_kalshi_balance.get('balance') is None:
                raise ValueError("Kalshi balance not found")

            return {
                # polymarket
                Currency.USDC_E: Money(Decimal(math.floor(usdc_e_bal)), Currency.USDC_E),
                Currency.POL: Money(Decimal(math.floor(matic_bal / 10 ** 18)), Currency.POL),
                # kalshi
                Currency.USD: Money(Decimal(math.floor(raw_kalshi_balance['balance']/100)), Currency.USD),
            }
        except Exception as e:
            raise e