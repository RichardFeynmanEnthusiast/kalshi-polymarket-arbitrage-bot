from decimal import Decimal

from app.domain.primitives import Money
from app.domain.types import Wallets
from app.strategies.trade_sqrt_size import calculate_minimum_wallet_budget


def get_trade_size(wallets: Wallets, trade_opportunity_size: Decimal, kalshi_fees: Money) -> int:
    """
    Determine a potential trade size by calculating the minimum of the Kalshi wallet balance,
    Polymarket wallet balance, and the square root of the total opportunity size.

    Args:
        wallets (Wallets): The wallets containing balances for prediction market exchanges.
        trade_opportunity_size (Decimal): The size of the trade opportunity.
        kalshi_fees (Decimal): The amount of kalshi fees in the trade opportunity.

    Returns:
        int: The calculated trade size.
    """
    wallet_budget = calculate_minimum_wallet_budget(wallets, kalshi_fees)
    prct_opportunity = calculate_trade_size(trade_opportunity_size)
    potential_size = min(wallet_budget, prct_opportunity)

    if potential_size < wallet_budget:
        return potential_size
    else:
        return 0

def calculate_trade_size(trade_size: Decimal) -> int:
    """
    Calculate the trade size by taking the square root of the given trade size and rounding down
    to the nearest integer.

    Args:
        trade_size (Decimal): The size of the trade.

    Returns:
        int: The calculated trade size after applying the square root and rounding down.
    """
    scaling_factor = Decimal('0.15')
    if trade_size <= Decimal('0'):
        return 0
    return int(trade_size * scaling_factor)