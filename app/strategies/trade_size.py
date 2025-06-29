from decimal import Decimal
import math

from shared_wallets.domain.types import Currency
from app.domain.types import Wallets
from app.domain.primitives import Money

def get_trade_size(wallets: Wallets, trade_opportunity_size : Decimal, kalshi_fees : Money) -> int:
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
    return min(calculate_minimum_wallet_budget(wallets, kalshi_fees),
               calculate_trade_size(trade_opportunity_size))

def calculate_trade_size(trade_size : Decimal) -> int:
    """
    Calculate the trade size by taking the square root of the given trade size and rounding down
    to the nearest integer.

    Args:
        trade_size (Decimal): The size of the trade.

    Returns:
        int: The calculated trade size after applying the square root and rounding down.
    """
    sqr_root = math.sqrt(math.floor(trade_size))
    return math.floor(sqr_root)

def calculate_minimum_wallet_budget(wallets: Wallets, kalshi_fees : Money) -> int:
    """
    Get the lesser of the Kalshi account's USD balance and the Polymarket account's USDC.e balance.

    Args:
        wallets (Wallets): The wallets containing balances for Kalshi and Polymarket exchanges.
        kalshi_fees (Money): The amount of kalshi fees.
    Returns:
        int: The minimum balance between the Kalshi USD and Polymarket USDC.e accounts.
        Returns 0 if the currency is not found in the wallets.
    """
    REMAINING_BALANCE = 0.95
    try:
        kalshi_usd = math.floor(wallets.kalshi_wallet.get_balance(Currency.USD).amount)
        kalshi_usd_adjusted : int = math.floor(kalshi_usd * REMAINING_BALANCE) - math.ceil(kalshi_fees)
        poly_usdc_e : int = math.floor(wallets.polymarket_wallet.get_balance(Currency.USDC_E).amount)
        return max(min(kalshi_usd_adjusted, poly_usdc_e),0) # 0 for undetected edge cases subtracting kalshi_fees
    except KeyError:
        # Currency not found in wallets
        return 0