import time

from shared_wallets.domain.types import Currency

from app.gateways.balance_data_gateway import BalanceDataGateway
from app.utils.kalshi_client_factory import KalshiClientFactory
from app.utils.polymarket_client_factory import PolymarketClientFactory

# setup
polymarket_factory = PolymarketClientFactory()
clob_client, _ = polymarket_factory.create_both_clients()

factory = KalshiClientFactory()
kalshi_http, _ = factory.create_both_clients()
balance_gtwy = BalanceDataGateway(clob_http_client=clob_client, kalshi_http_client=kalshi_http)

start = time.perf_counter()
balances = balance_gtwy.get_venue_balances()
end = time.perf_counter()

print(f"Kalshi {Currency.USD.value} balance: {balances[Currency.USD]}")
print(f"Polymarket {Currency.POL.value} balance: {balances[Currency.POL]}")
print(f"Polymarket {Currency.USDC_E.value} balance: {balances[Currency.USDC_E]}")
print(f"Getting both balances took {(end - start)*1e6:.2f} µs")