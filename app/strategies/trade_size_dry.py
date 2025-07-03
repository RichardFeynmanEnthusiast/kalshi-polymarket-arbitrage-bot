from decimal import Decimal, ROUND_HALF_UP


def get_trade_size_dry(trade_opportunity_size: Decimal) -> int:
    """
    For data logging purposes pretend the trade size is the full opportunity size.

    Args:
        trade_opportunity_size (Decimal): The size of the trade opportunity.
    Returns:
        int: The calculated trade size.
    """
    return trade_opportunity_size.quantize(Decimal('1'), rounding=ROUND_HALF_UP)