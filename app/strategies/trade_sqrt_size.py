from decimal import Decimal, ROUND_FLOOR

from shared_wallets.domain.types import Currency

from app.domain.primitives import Money
from app.domain.types import Wallets
from app.settings.settings import settings


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
    sqrt_opportunity = calculate_trade_size(trade_opportunity_size)
    potential_size = min(wallet_budget, sqrt_opportunity)

    if potential_size >= settings.SHUTDOWN_BALANCE:
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
    if trade_size < Decimal('0'):
        return 0
    return int(trade_size.sqrt())


def calculate_minimum_wallet_budget(wallets: Wallets, kalshi_fees: Money) -> int:
    """
    Get the lesser of the Kalshi account's USD balance and the Polymarket account's USDC.e balance.

    Args:
        wallets (Wallets): The wallets containing balances for Kalshi and Polymarket exchanges.
        kalshi_fees (Money): The amount of kalshi fees.
    Returns:
        int: The minimum balance between the Kalshi USD and Polymarket USDC.e accounts.
        Returns 0 if the currency is not found in the wallets.
    """
    REMAINING_BALANCE = Decimal('0.95')
    try:
        kalshi_usd = wallets.kalshi_wallet.get_balance(Currency.USD).amount.quantize(
            Decimal('1'),
            rounding=ROUND_FLOOR
        )
        poly_usdc_e = wallets.polymarket_wallet.get_balance(Currency.USDC_E).amount.quantize(
            Decimal('1'),
            rounding=ROUND_FLOOR
        )
        kalshi_usd_adjusted = ((kalshi_usd * REMAINING_BALANCE) - kalshi_fees).quantize(
            Decimal('1'),
            rounding=ROUND_FLOOR
        )
        return int(max(Decimal('0'), min(kalshi_usd_adjusted, poly_usdc_e)))
    except (KeyError, AttributeError):
        # Currency not found in wallets
        return 0
