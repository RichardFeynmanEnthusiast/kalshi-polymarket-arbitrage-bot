from decimal import Decimal
from enum import Enum
from typing import NamedTuple

Money = Decimal

# This enum is used widely and has no dependencies.
class Platform(str, Enum):
    """A canonical enumeration of supported platforms."""
    POLYMARKET = 'POLYMARKET'
    KALSHI = 'KALSHI'

# This constant container has no dependencies.
class Side(NamedTuple):
    BUY: str = 'BUY'
    SELL: str = 'SELL'

SIDES = Side()

class KalshiSide(str, Enum):
    """Possible Kalshi positions one can enter into."""
    YES = "yes"
    NO = "no"

class PolySide(str, Enum):
    """Possible Polymarket positions one can enter into."""
    BUY = "BUY"
    SELL = "SELL"