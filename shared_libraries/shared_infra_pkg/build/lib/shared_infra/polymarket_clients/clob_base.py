from typing import Optional

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds
from eth_typing import HexStr, AnyAddress

from shared_infra.settings.environments import Environment
from shared_infra.web3_utils.polygon_net import valid_eth_private_key, valid_eth_wallet_addr, get_matic_balance, get_usdc_e_balance


class PolymarketClobBaseClient:
    """Base client class for interacting with the Polymarket Clob API."""
    def __init__(
        self,
            polym_wallet_pk: str,
            polym_wallet_pub_addr: str,
            polym_clob_api_key: Optional[str] = None,
            chain_id = 137,
            environment: str = Environment.DEMO.value,
    ):
        """Initializes the polymarket client

        Args:
            polym_wallet_pk: str: Your Polymarket wallet private key; only needed for CLOB api.
            polym_wallet_pub_addr: str: Your Polymarket (eth) wallet public key.
            polym_clob_api_key Optional(str): Your Polymarket clob API key.
            chain_id int: Polygon mainnet chain ID. Unlikely this argument needs to be changed by the caller.
            environment (Environment): The API environment to use, defaults to demo environment.
        """
        self.wallet_pk : HexStr = valid_eth_private_key(polym_wallet_pk)
        self.wallet_pub_key : AnyAddress = valid_eth_wallet_addr(polym_wallet_pub_addr)
        self.clob_api_key = polym_clob_api_key
        self.chain_id = chain_id
        self.environment = environment

        if self.environment == Environment.DEMO.value or self.environment == Environment.PROD.value:
            self.CLOB_HTTP_BASE_URL : str = "https://clob.polymarket.com"
            self.CLOB_WS_BASE_URL : str = "wss://ws-subscriptions-clob.polymarket.com/ws/"
        else:
            raise ValueError("Invalid environment")

    def generate_clob_api_creds(self) -> ApiCreds:
        try:
            client = ClobClient(self.CLOB_HTTP_BASE_URL, key=self.wallet_pk, chain_id=self.chain_id)
            api_creds = client.create_or_derive_api_creds()
        except Exception as e:
            raise e
        return api_creds

    def get_starting_balances(self):
        try:
            usdc_e_balance = get_usdc_e_balance(self.wallet_pub_key)
            matic_balance = get_matic_balance(self.wallet_pub_key)
            return usdc_e_balance, matic_balance
        except Exception as e:
            raise e