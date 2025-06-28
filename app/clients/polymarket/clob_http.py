from typing import Any, Dict, List, Optional

import requests
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderType, OrderArgs, PartialCreateOrderOptions, TickSize, ApiCreds
from py_clob_client.http_helpers.helpers import PolyApiException

from app.clients.polymarket.poly_market_base import PolymBaseClient
from app.clients.polymarket.utils.polymarket_client_helpers import generate_book_params
from app.domain.models.match_models import MatchedMarket
from app.settings.env import Environment


class PolymClobHttpClient(PolymBaseClient):
    """Client for handling HTTP connections to the Polymarket clob API."""
    def __init__(
            self,
            polym_wallet_pk: str,
            polym_clob_api_key: str,
            chain_id=137,  # type may change in the future
            environment: Environment = Environment.DEMO,
            polym_wallet_addr: Optional[str] = None,
    ):
        super().__init__(polym_wallet_pk, polym_wallet_addr, polym_clob_api_key, chain_id, environment.value)
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
        except PolyApiException as poly_exception:
            print(f"Error getting market with condition_id {condition_id}: {poly_exception}")
            raise
        return market

    def get_markets(self, next_cursor : str = "") -> Any:
        """Get available CLOB markets (paginated)."""
        try:
            response = self.clob_client.get_markets(next_cursor=next_cursor)
        except PolyApiException as poly_exception:
            print(f"Error getting markets with cursor {next_cursor}: {poly_exception}")
            raise
        return response

    def get_order_books(self, matches: List[MatchedMarket]):
        """Gets order book given a list of dicts. Each dict should have a condition id value and token object"""
        token_dict = {}
        for poly_data in matches:
            token_dict[poly_data.poly_conditionId] = poly_data.poly_clobTokenIds
        order_books = self.generate_order_books(token_dict=token_dict)
        return order_books

    def generate_order_books(self, token_dict: Dict[str, Any] ) -> List[Any]:
        """Retrieves order books given a dictionary with token_ids"""
        # generate book params
        params = generate_book_params(token_dict)
        try:
            order_books = self.clob_client.get_order_books(
                params=params
            )
        except PolyApiException as poly_exception:
            print(f"An error occurred while trying to get order books: {poly_exception}")
            raise
        return order_books

    def place_single_order(
            self,
            salt: int,
            maker: str,
            signer: str,
            taker: str,
            token_id: str,
            maker_amount: str,
            taker_amount: str,
            expiration: str,
            nonce: str,
            fee_rate_bps: str,
            side: str,
            signature_type: int,
            signature: str,
            owner: str,
            order_type: str
    ) -> Dict[str, Any]:
        """
        Create and place a single order via the Polymarket CLOB API.

        Args:
            salt: Random salt for uniqueness.
            maker: Maker address (funder)
            signer: Signing address
            taker: Taker address (operator)
            token_id: ERC1155 token ID of conditional token.
            maker_amount: Maximum amount maker will spend.
            taker_amount: Minimum amount taker will pays.
            expiration: Unix expiration timestamp.
            nonce: Maker's exchange none.
            fee_rate_bps: Fee rate in basis points.
            side: Buy or sell enum index
            signature_type: Signature type enum index.
            signature: Hex encoded signature.
            owner: API key of order owner.
            order_type: Once of 'FOK', 'FAK', 'GTC', 'GTD'

        Returns:
            Response JSON as a dict.

        Raises:
            PolyApiException on API-level errors.
            requests.RequestException on HTTP errors.
        """
        payload: Dict[str, Any] = {
            "order": {
                "salt": salt,
                "maker": maker,
                "taker": taker,
                "tokenId": token_id,
                "makerAmount": maker_amount,
                "takerAmount": taker_amount,
                "expiration": expiration,
                "nonce": nonce,
                "feeRateBps": fee_rate_bps,
                "side": side,
                "signatureType": signature_type,
                "signature": signature,
            },
            "owner": owner,
            "orderType": order_type,
        }
        url = f"{self.host}/order"
        headers = {"L2-Auth": self.clob_api_key}
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"HTTP error placing single order: {e}")
            raise

        if not data.get("success", False):
            error_msg = data.get("errorMsg", "Unknown error")
            raise PolyApiException(f"Order placement failed: {error_msg}")
        return data

    def place_order(
        self,
        token_id: str,
        price: float,
        size: float,
        side: str,
        order_type: OrderType,
        tick_size: Optional[TickSize] = None,
        neg_risk: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Build, sign, and submit a single order in one call.

        Args:
            token_id: ERC1155 token ID of conditional token.
            price: Price per unit in smallest denomination.
            size: Number of shares/contracts.
            side: 'BUY' or 'SELL'.
            order_type: OrderType enum (FOK, FAK, GTC, GTD).
            tick_size: Custom tick size override (one of '0.1', '0.01', '0.001', '0.0001').
            neg_risk: Custom negative risk flag override.

        Returns:
            Response JSON dict from post_order.
        """
        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
        )
        options: Optional[PartialCreateOrderOptions] = None
        if tick_size is not None or neg_risk is not None:
            options = PartialCreateOrderOptions(
                tick_size=tick_size,
                neg_risk=neg_risk,
            )
        signed = self.clob_client.create_order(order_args, options)
        return self.clob_client.post_order(signed, order_type)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel (zero out) an existing order by its ID.
        Delegates to the underlying ClobClient.cancel(...) method.
        """
        return self.clob_client.cancel(order_id)