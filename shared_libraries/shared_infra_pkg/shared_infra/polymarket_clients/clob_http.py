from typing import Any, Dict, List, Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderType, OrderArgs, PartialCreateOrderOptions, TickSize, ApiCreds
from py_clob_client.http_helpers.helpers import PolyApiException

from shared_infra.polymarket_clients.clob_base import PolymarketClobBaseClient
from shared_infra.settings.environments import Environment


class PolymarketClobHttpClient(PolymarketClobBaseClient):
    """Client for handling HTTP connections to the Polymarket clob API."""
    def __init__(
            self,
            polym_wallet_pk: str,
            polym_wallet_pub_addr: str,
            polym_clob_api_key: Optional[str] = None,
            chain_id=137,
            environment: str = Environment.DEMO.value,
    ):
        super().__init__(polym_wallet_pk, polym_wallet_pub_addr, polym_clob_api_key, chain_id, environment)
        self.host = self.CLOB_HTTP_BASE_URL

        try:
            client = ClobClient(host=self.host, key=polym_wallet_pk, chain_id=self.chain_id)
            creds: ApiCreds = self.generate_clob_api_creds()
            client.set_api_creds(creds)
            self.clob_client = client
        except Exception as e:
            raise e

    def get_single_market(self, condition_id : str) -> Any :
        """Retrieves a single market given a condition id. Returns an object of type market"""
        try:
            market = self.clob_client.get_market(condition_id)
            return market
        except PolyApiException as poly_exception:
            raise poly_exception

    def get_markets(self, next_cursor : str = "") -> Any:
        """Get available CLOB markets (paginated)."""
        try:
            response = self.clob_client.get_markets(next_cursor=next_cursor)
            return response
        except PolyApiException as poly_exception:
            raise poly_exception