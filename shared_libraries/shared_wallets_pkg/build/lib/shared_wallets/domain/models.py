from decimal import Decimal
from enum import Enum
from typing import Dict
from types import MappingProxyType

from shared_wallets.domain.types import Money, Currency

class Exchange(str, Enum):
    KALSHI = "kalshi"
    POLYMARKET = "polymarket"

class ExchangeWallet:
    def __init__(self, exchange: Exchange, balances: Dict[Currency, Money]):
        self._exchange = exchange
        self._balances: Dict[Currency, Money] = balances   # key = currency code

    def get_balance(self, currency: Currency) -> Money:
        try:
            result = self._balances.get(currency)
            if result is None:
                raise KeyError
            return result
        except KeyError:
            raise KeyError(f"{self._exchange.value} wallet does not contain any {currency}")

    def get_amount(self, currency: Currency) -> Decimal:
        currency = self.get_balance(currency)
        return currency.amount

    def get_all_balances(self) -> MappingProxyType[Currency, Money]:
        """ Returns a read-only dictionary copy of balances """
        return MappingProxyType(self._balances)

    def increment(self, money: Money):
        current = self.get_balance(money.currency)
        self._balances[money.currency] = current.add(money)

    def decrement(self, money: Money):
        current = self.get_balance(money.currency)
        self._balances[money.currency] = current.subtract(money)

    def set_balances(self, new_balances: Dict[Currency, Money]):
        """For reconciliation: hard-set all balances."""
        self._balances = new_balances