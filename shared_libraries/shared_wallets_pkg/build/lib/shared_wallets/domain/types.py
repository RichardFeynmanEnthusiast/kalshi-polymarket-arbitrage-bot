from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

class Currency(str, Enum):
    USD = "USD"
    USDC_E = "USDC_e"
    POL = "POL"
    USDC = "USDC" # for possible reconciliation purposes

@dataclass
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self):
        assert self.amount >= Decimal(0), "Amount cannot be negative"

    def add(self, other: "Money") -> "Money":
        assert self.currency == other.currency
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def subtract(self, other: "Money") -> "Money":
        assert self.currency == other.currency
        assert self.amount >= other.amount, "Insufficient funds"
        return Money(amount=self.amount - other.amount, currency=self.currency)