import asyncio
import logging
from typing import Any, Dict, List

import aiohttp
import requests

from app.clients.polymarket.poly_market_base import PolymBaseClient
from app.settings.env import Environment


class PolymGammaClient(PolymBaseClient):
    """Client for handling HTTP connections to the Polymarket gamma API. Doesn't require auth"""
    DEFAULT_EVENTS_PAGE_SIZE: int = 20 # number of events if tag_id isn't provided
    def __init__(
            self,
            environment: Environment = Environment.DEMO,
    ):
        super().__init__(environment=environment.value)
        self.logger = logging.getLogger(__name__)
        self.host = self.GAMMA_HTTP_BASE_URL
        self.events_url = "/events"
        self.markets_url = '/markets'

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    def get(self, path: str = "", params: Dict[str, Any] = {}) -> Any:
        """Performs a GET request to the Polymarket Gamma API."""
        try:
            response = requests.get(
                self.host + path,
                params=params
            )
            self.raise_if_bad_response(response)
            return response.json()
        except requests.exceptions.ReadTimeout:
            print("The request timed out.")
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)



    def get_events(self, params: Dict[str, Any] = {}) -> Any:
        """Performs a GET request to the Polymarket event Gamma API. Returns a list of events."""
        response = self.get(path=self.events_url, params=params)
        return response

    def get_all_events(self, params=None) -> List[Any]:
        """Retrieves all events from a given offset.
         Defaults to all open events if no query params are provided."""
        events = []
        if params is None:
            offset_num = 0
            params = {"closed": "false",
                      "offset": offset_num}
        elif "offset" not in params:
            offset_num = 0
            params["offset"] = offset_num
        else:
            offset_num = params["offset"]

        while True:
            self.logger.info(f"getting events for offset: {offset_num}")
            # print()
            params["offset"] = offset_num
            response = self.get_events(params=params)

            new_events = response
            events.extend(response)

            if not new_events: # Stop when response is empty
                break

            offset_num += self.DEFAULT_EVENTS_PAGE_SIZE
        return events

    def get_markets(self, params: Dict[str, Any] = {}) -> Any:
        """Performs a GET request to the Polymarket markets Gamma API."""
        response = self.get(path=self.markets_url, params=params)
        return response

    def get_all_markets(self, params=None):
        """Retrieves all open markets from a given offset."""

        markets = []
        if params is None:
            offset_num = 0
            params = {"closed": "false",
                      "offset": offset_num}
        elif "offset" not in params:
            offset_num = 0
            params["offset"] = offset_num
        else:
            offset_num = params["offset"]

        while True:
            self.logger.info(f"getting markets for offset: {offset_num}")
            # print()
            params["offset"] = offset_num
            response = self.get_markets(params=params)

            new_markets = response
            markets.extend(response)

            if not new_markets:  # Stop when response is empty
                break

            offset_num += self.DEFAULT_EVENTS_PAGE_SIZE
        return markets

    async def async_get_market(self, session: aiohttp.ClientSession, params: dict):
        """Returns the full order book for one market ticker"""
        path = f"{self.markets_url}"
        url = self.host + path
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def async_get_markets(self, params: List[dict]):
        """Fetch all markets concurrently for a list of polymarket ids"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.async_get_market(session, param) for param in params]
            return await asyncio.gather(*tasks)