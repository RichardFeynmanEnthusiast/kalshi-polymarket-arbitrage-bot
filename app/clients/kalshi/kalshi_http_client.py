import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List

import aiohttp
import pandas as pd
import requests
from cryptography.hazmat.primitives.asymmetric import rsa

from .base import KalshiBaseClient, Environment


class KalshiHttpClient(KalshiBaseClient):
    """Client for handling HTTP connections to the Kalshi API."""
    def __init__(
            self,
            key_id: str,
            private_key: rsa.RSAPrivateKey,
            environment: Environment = Environment.DEMO,
    ):
        super().__init__(key_id, private_key, environment)
        self.host = self.HTTP_BASE_URL
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"
        self.events_url = "/trade-api/v2/events"

    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits."""
        THRESHOLD_IN_MILLISECONDS = 100
        now = datetime.now()
        threshold_in_microseconds = 1000 * THRESHOLD_IN_MILLISECONDS
        threshold_in_seconds = THRESHOLD_IN_MILLISECONDS / 1000
        if now - self.last_api_call < timedelta(microseconds=threshold_in_microseconds):
            time.sleep(threshold_in_seconds)
        self.last_api_call = datetime.now()

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """
        Raises an HTTPError if the response status code indicates an error,
        including the response body in the error message.
        """
        if response.status_code not in range(200, 299):
            # Construct a detailed error message that includes the response text.
            error_message = (
                f"{response.status_code} {response.reason} for url: {response.url}\n"
                f"Response Body: {response.text}"
            )
            # Raise an HTTPError with the new, more informative message.
            raise requests.exceptions.HTTPError(error_message, response=response)


    async def post(self, path: str, body: dict) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        headers = self.request_headers("POST", path)
        url = self.host + path

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=body) as response:
                response.raise_for_status()
                return await response.json()

    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = requests.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def delete(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = requests.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel (zero out) an exitin order by its ID.

        Returns the updated (zeroed) order payload as JSON.
        """
        path = f"{self.portfolio_url}/orders/{order_id}"
        return self.delete(path)

    def get_balance(self) -> Dict[str, Any]:
        """Retrieves the account balance."""
        return self.get(self.portfolio_url + '/balance')

    def get_exchange_status(self) -> Dict[str, Any]:
        """Retrieves the exchange status."""
        return self.get(self.exchange_url + "/status")

    def get_orderbook(self, ticker: str) -> Dict[str, Any]:
        """Returns the full order book for one market ticker"""
        path = f"{self.markets_url}/{ticker}/orderbook"
        return self.get(path)

    async def async_get_orderbook(self, session: aiohttp.ClientSession, ticker: str) -> Dict[str, Any]:
        """Returns the full order book for one market ticker"""
        path = f"{self.markets_url}/{ticker}/orderbook"
        url = self.host + path
        headers = self.request_headers("GET", path)
        async with session.get(url, headers=headers) as response:
            response.raise_for_status()
            return await response.json()

    async def async_get_orderbooks(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Fetch all orderbooks concurrently for a list of tickers"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.async_get_orderbook(session, ticker) for ticker in tickers]
            return await asyncio.gather(*tasks)

    async def async_get_orderbooks_rate_limited(self, tickers: List[str], batch_size=10, delay=0.25) -> List[Dict[str, Any]]:
        """Fetch orderbooks given a list of tickers in batches with delays between them"""
        async with aiohttp.ClientSession() as session:
            results = []

            for i in range(0, len(tickers), batch_size):
                batch = tickers[i:i + batch_size]
                tasks = [self.async_get_orderbook(session, ticker) for ticker in batch]
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                await asyncio.sleep(delay)

            return results

    def get_trades(
            self,
            ticker: Optional[str] = None,
            limit: Optional[int] = None,
            cursor: Optional[str] = None,
            max_ts: Optional[int] = None,
            min_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'ticker': ticker,
            'limit': limit,
            'cursor': cursor,
            'max_ts': max_ts,
            'min_ts': min_ts,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url + '/trades', params=params)

    def get_all_events_dataframe(
            self,
            status: str = "open",
            limit: int = 200,
    ) -> pd.DataFrame:
        """
        Fetches all events (paginating through cursors) and return a
        Dataframe of unique events
        """
        all_events = []
        seen = set()
        params = {"status": status, "limit": limit}

        while True:
            resp = self.get(self.events_url, params)
            events = resp.get("events", [])
            cursor = resp.get("cursor")

            for event in events:
                ticker = event.get("event_ticker")
                if ticker and ticker not in seen:
                    seen.add(ticker)
                    all_events.append(event)

            if not cursor:
                break

            params["cursor"] = cursor

        df = pd.DataFrame(all_events)

        return df.drop_duplicates(subset=["event_ticker"]).reset_index(drop=True)

    def get_market(self, ticker: str):
        """ Fetches a single market given a market ticker"""
        params = {"tickers": ticker}
        resp = self.get(self.markets_url, params)
        return resp

    def get_specific_markets(self, tickers: str):
        """ Fetches multiple markets given a string of tickers as a comma seperated list"""
        params = {"tickers": tickers}
        resp = self.get(self.markets_url, params)
        return resp

    def get_all_markets_dataframe(
            self,
            status: str = "open",
            limit: int = 1000,
    ) -> pd.DataFrame:
        """
        Fetches all markets (paginating through cursors) and return a DataFrame
        """
        all_markets = []
        seen = set()
        params = {"status": status, "limit": limit}

        while True:
            resp = self.get(self.markets_url, params)
            markets = resp.get("markets", [])
            cursor = resp.get("cursor")
            print("cursor:", cursor) # TODO: make log

            for m in markets:
                tick = m.get("ticker")
                if tick and tick not in seen:
                    seen.add(tick)
                    all_markets.append(m)

            if not cursor:
                break

            params["cursor"] = cursor

        df = pd.DataFrame(all_markets)
        return df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)

    async def create_order(
        self,
        action: str,
        side: str,
        type: str,
        ticker: str,
        count: int,
        client_order_id: str,
        yes_price: Optional[int] = None,
        no_price: Optional[int] = None,
        buy_max_cost: Optional[int] = None,
        expiration_ts: Optional[int] = None,
        post_only: bool = False,
        sell_position_floor: Optional[int] = None,
        time_in_force: str = "fill_or_kill",
    ) -> Dict[str, Any]:
        """
        Submit a new order to a Kalshi market.

        Args:
            action: 'buy' or 'sell'.
            side: 'yes' or 'no'.
            type: 'market' or 'limit'.
            ticker: Market ticker.
            count: Number of contracts.
            client_order_id: Unique client-provided ID.
            yes_price: Price (in cents) when side='yes' for limit orders.
            no_price: Price (in cents) when side='no' for limit orders.
            buy_max_cost: Maximum spend (in cents) for market buy orders.
            expiration_ts: UNIX timestamp (seconds) when the order expires.
            post_only: If true, reject order if it crosses the spread.
            sell_position_floor: Prevent flipping position for market orders.
            time_in_force: Only 'fill_or_kill' is currently supported.

        Returns:
            Response JSON as a dictionary.
        """
        # Validate price parameters
        if (yes_price is None) == (no_price is None):
            raise ValueError("Exactly one of yes_price or no_price must be provided")
        # Market buy requires buy_max_cost
        if type == "market" and action == "buy" and buy_max_cost is None:
            raise ValueError("buy_max_cost is required for market buy orders")

        body: Dict[str, Any] = {
            "action": action,
            "side": side,
            "type": type,
            "ticker": ticker,
            "count": count,
            "client_order_id": client_order_id,
            "time_in_force": time_in_force,
            "post_only": post_only,
        }
        # Attach conditional parameters
        if yes_price is not None:
            body["yes_price"] = yes_price
        if no_price is not None:
            body["no_price"] = no_price
        if buy_max_cost is not None:
            body["buy_max_cost"] = buy_max_cost
        if expiration_ts is not None:
            body["expiration_ts"] = expiration_ts
        if sell_position_floor is not None:
            body["sell_position_floor"] = sell_position_floor

        # Send the request
        return await self.post(f"{self.portfolio_url}/orders", body)

    def get_orders(
            self,
            ticker: Optional[str] = None,
            event_ticker: Optional[str] = None,
            min_ts: Optional[int] = None,
            max_ts: Optional[int] = None,
            status: Optional[str] = None,
            cursor: Optional[str] = None,
            limit: int = 100,
    ) -> Dict[str, Any]:
         """
        Retrieve a list of orders from your portfolio with optional filters.

        Args:
            ticker: Restrict to orders for a specific market ticker.
            event_ticker: Restrict to orders for a specific event ticker.
            min_ts: Unix timestamp (seconds) to filter orders placed after this time.
            max_ts: Unix timestamp (seconds) to filter orders placed before this time.
            status: Filter by order status: 'resting', 'canceled', or 'executed'.
            cursor: Pagination cursor from a previous response.
            limit: Number of results per page (1-1000, default 100).

        Returns:
            Paginated response JSON including orders and next cursor if available.
        """
         params: Dict[str, Any] = {"limit": limit}
         if ticker is not None:
             params["ticker"] = ticker
         if event_ticker is not None:
             params["event_ticker"] = event_ticker
         if min_ts is not None:
             params["min_ts"] = min_ts
         if max_ts is not None:
             params["max_ts"] = max_ts
         if status is not None:
             params["status"] = status
         if cursor is not None:
             params["cursor"] = cursor

         return self.get(f"{self.portfolio_url}/orders", params)

    def get_positions(
            self,
            cursor: Optional[str] = None,
            limit: int = 100,
            count_filter: Optional[str] = None,
            settlement_status: Optional[str] = None,
            ticker: Optional[str] = None,
            event_ticker: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve a list of market positions for the member with optional filters.

        Args:
            cursor: Pagination cursor from a previous response.
            limit: Number of results per page (1-1000, default 100).
            count_filter: Comma-separated list of fields to filter by non-zero values: 'position', 'total_traded', 'resting_order_count'.
            settlement_status: Settlement status filter: 'all', 'settled', or 'unsettled'. Defaults to 'unsettled' if not provided.
            ticker: Restrict to positions for a specific market ticker.
            event_ticker: Restrict to positions for a specific event ticker.

        Returns:
            Paginated response JSON including positions and next cursor if available.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if count_filter is not None:
            params["count_filter"] = count_filter
        if settlement_status is not None:
            params["settlement_status"] = settlement_status
        if ticker is not None:
            params["ticker"] = ticker
        if event_ticker is not None:
            params["event_ticker"] = event_ticker

        return self.get(f"{self.portfolio_url}/positions", params)