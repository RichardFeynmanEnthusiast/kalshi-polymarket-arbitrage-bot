#
import asyncio
import logging
from enum import Enum
from typing import Any, Dict, List, Callable

import aiohttp
import requests

from shared_infra.settings.environments import Environment

logger = logging.getLogger(__name__)

class GammaData(str, Enum):
    Market = "market",
    Event = "event",

class PolymarketGammaClient:
    """Client for handling HTTP connections to the Polymarket gamma API. Doesn't require auth"""
    DEFAULT_EVENTS_PAGE_SIZE: int = 20 # number of events if tag_id isn't provided
    MAX_CONCURRENT_BATCH_SIZE : int = 50  # Number of concurrent requests per batch based on a rate of 50 requests per 10 seconds
    API_THROTTLE_COOL_DOWN_SECONDS : int = 10

    def __init__(
            self,
            environment: str = Environment.DEMO.value,
    ):

        self.events_url = "/events"
        self.markets_url = '/markets'
        self.environment = environment
        if self.environment == Environment.DEMO.value or self.environment == Environment.PROD.value:
            self.GAMMA_BASE_URL = "https://gamma-api.polymarket.com"  # gamma api doesn't require auth
        else:
            raise ValueError("Invalid environment")

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    def get(self, path: str = "", params: Dict[str, Any] = {}) -> Any:
        """Performs a GET request to the Polymarket Gamma API."""
        try:
            response = requests.get(
                self.GAMMA_BASE_URL + path,
                params=params
            )
            self.raise_if_bad_response(response)
            return response.json()
        except requests.exceptions.ReadTimeout as e:
            logger.error("The request timed out.")
            raise e
        except requests.exceptions.RequestException as e:
            logger.error("Request failed:", e)
            raise e

    def get_events(self, params: Dict[str, Any] = {}) -> Any:
        """Performs a GET request to the Polymarket event Gamma API. Returns a list of events."""
        response = self.get(path=self.events_url, params=params)
        return response

    def get_all_events(self, params=None) -> List[Any]:
        """Retrieves all events from a given offset.
         Defaults to all open events if no query params are provided."""
        events = []
        offset_num = params.get("offset", 0) if params else 0

        params = params or {}
        params.setdefault("closed", "false")
        params.setdefault("active", "True")
        params["offset"] = offset_num

        while True:
            logger.info(f"getting events for offset: {offset_num}")
            params["offset"] = offset_num
            response = self.get_events(params=params)

            new_events = response
            events.extend(response)

            if not new_events: # Stop when response is empty
                break

            offset_num += self.DEFAULT_EVENTS_PAGE_SIZE
        return events

    async def async_get_event(self, session: aiohttp.ClientSession, params: dict):
        """Returns the full order book for one market ticker"""
        path = f"{self.events_url}"
        url = self.GAMMA_BASE_URL + path
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def async_get_events(self, params: List[dict]):
        """Fetch all markets concurrently for a list of polymarket ids"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.async_get_event(session, param) for param in params]
            return await asyncio.gather(*tasks)

    async def get_all_events_async(self, base_params=None):
        """Asynchronously fetch all open markets using batched concurrent requests."""
        events = []
        offset = base_params.get("offset", 0) if base_params else 0
        base_params = base_params or {}
        base_params.setdefault("closed", "false")
        base_params.setdefault("active", "True")

        async with aiohttp.ClientSession() as session:
            while True:
            # Build batch of params for async calls
                batch_params = []
                for i in range(self.MAX_CONCURRENT_BATCH_SIZE):
                    batch_offset = offset + i * self.DEFAULT_EVENTS_PAGE_SIZE
                    param_copy = base_params.copy()
                    param_copy["offset"] = batch_offset
                    batch_params.append(param_copy)

                logger.debug(f"Fetching batch starting at offset {offset}")
                tasks = [
                    self.async_get_event(session, param)
                    for param in batch_params
                ]
                batch_results = await asyncio.gather(*tasks)

                # Flatten and filter
                batch_events = [e for result in batch_results for e in result]

                events.extend(batch_events)
                offset += self.MAX_CONCURRENT_BATCH_SIZE * self.DEFAULT_EVENTS_PAGE_SIZE
                # If less than all requests were needed break
                if len(batch_events) < (self.MAX_CONCURRENT_BATCH_SIZE * self.DEFAULT_EVENTS_PAGE_SIZE):
                    logger.info("Received empty batch, ending async fetch.")
                    break
                await asyncio.sleep(self.API_THROTTLE_COOL_DOWN_SECONDS)

            return events

    def get_markets(self, params: Dict[str, Any] = {}) -> Any:
        """Performs a GET request to the Polymarket markets Gamma API."""
        response = self.get(path=self.markets_url, params=params)
        return response

    def get_all_markets(self, params=None):
        """Retrieves all open markets from a given offset."""

        markets = []
        offset_num = params.get("offset", 0) if params else 0

        params = params or {}
        params.setdefault("closed", "false")
        params["offset"] = offset_num

        while True:
            logger.info(f"getting markets for offset: {offset_num}")
            params["offset"] = offset_num
            response = self.get_markets(params=params)

            new_markets = response
            markets.extend(response)

            if not new_markets:  # Stop when response is empty
                break

            offset_num += self.DEFAULT_EVENTS_PAGE_SIZE
        return markets

    async def get_all_markets_async(self, base_params=None):
        """Asynchronously fetch all open markets using batched concurrent requests."""
        markets = []
        offset = base_params.get("offset", 0) if base_params else 0
        base_params = base_params or {}
        base_params.setdefault("closed", "false")
        base_params.setdefault("active", "True")

        async with aiohttp.ClientSession() as session:
            while True:
            # Build batch of params for async calls
                batch_params = []
                for i in range(self.MAX_CONCURRENT_BATCH_SIZE):
                    batch_offset = offset + i * self.DEFAULT_EVENTS_PAGE_SIZE
                    param_copy = base_params.copy()
                    param_copy["offset"] = batch_offset
                    batch_params.append(param_copy)

                logger.info(f"Fetching batch starting at offset {offset}")
                tasks = [
                    self.async_get_market(session, param)
                    for param in batch_params
                ]
                batch_results = await asyncio.gather(*tasks)

                # Flatten and filter
                batch_markets = [e for result in batch_results for e in result]

                markets.extend(batch_markets)
                offset += self.MAX_CONCURRENT_BATCH_SIZE * self.DEFAULT_EVENTS_PAGE_SIZE
                # If less than all requests were needed break
                if len(batch_markets) < (self.MAX_CONCURRENT_BATCH_SIZE * self.DEFAULT_EVENTS_PAGE_SIZE):
                    logger.info("Received empty batch, ending async fetch.")
                    break
                await asyncio.sleep(self.API_THROTTLE_COOL_DOWN_SECONDS)

            return markets

    async def async_get_market(self, session: aiohttp.ClientSession, params: dict):
        """Returns the full order book for one market ticker"""
        path = f"{self.markets_url}"
        url = self.GAMMA_BASE_URL + path
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def async_get_markets(self, params: List[dict]):
        """Fetch all markets concurrently for a list of polymarket ids"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.async_get_market(session, param) for param in params]
            return await asyncio.gather(*tasks)

    def get_number_of_events(self, num_events_estimate: int, params : dict = None) -> int:
        """Binary search to find the highest offset that returns non-empty results.

        Returns: total number of events
        """

        base_params = params.copy() if params else {}
        base_params.setdefault("closed", "false")  # default fallback
        base_params.setdefault("active", "true")  # default fallback

        last_valid_offset = self.binary_search(base_params=base_params,
                                               starting_estimate=num_events_estimate,
                                               update_api=self.get_events)

        # Add PAGE_SIZE to get count of events up to last valid offset,
        # then count how many were actually on that final page
        final_params = base_params.copy()
        final_params["offset"] = last_valid_offset
        final_page = self.get_events(params=final_params)
        return last_valid_offset + len(final_page)

    def get_number_of_markets(self, num_markets_estimate: int, params : dict = None) -> int:
        """Binary search to find the highest offset that returns non-empty results.

        Returns: total number of events
        """

        base_params = params.copy() if params else {}
        base_params.setdefault("closed", "false")  # default fallback
        base_params.setdefault("active", "true")  # default fallback

        last_valid_offset = self.binary_search(base_params=base_params,
                                               starting_estimate=num_markets_estimate,
                                               update_api=self.get_markets)

        # Add PAGE_SIZE to get count of events up to last valid offset,
        # then count how many were actually on that final page
        final_params = base_params.copy()
        final_params["offset"] = last_valid_offset
        final_page = self.get_markets(params=final_params)
        return last_valid_offset + len(final_page)

    def estimate_fetch_all_ttc(self, data_type : GammaData, estimate : int, params : dict = None) -> int:
        """ Returns estimated time to completion in seconds """
        if not isinstance(data_type, GammaData):
            return -1
        total = self.get_number_of_events(num_events_estimate=estimate, params=params) if data_type == GammaData.Event else (
            self.get_number_of_markets(num_markets_estimate=estimate, params=params))
        if total:
            data_fetched_per_query = self.DEFAULT_EVENTS_PAGE_SIZE * self.MAX_CONCURRENT_BATCH_SIZE
            calls_needed = (total + data_fetched_per_query - 1) // data_fetched_per_query
            # assume each function call takes 1 second
            total_time_needed = (calls_needed - 1 ) * self.API_THROTTLE_COOL_DOWN_SECONDS + (calls_needed * 1)
            return total_time_needed
        return total

# -- helpers

    def find_max_heuristic(self, starting_estimate : int, base_params : dict, update_api : Callable) -> int:
        """ Finds the first index that returns an empty response,
        signifying it's greater the last paginated entry's index"""
        params_copy = base_params.copy()
        final_index = starting_estimate
        params_copy["offset"] = final_index
        results = update_api(params=base_params)
        # loop until empty array returned
        while results:
            final_index *= 2
            params_copy = base_params.copy()
            params_copy["offset"] = final_index
            results = update_api(params=params_copy)

        return final_index

    def binary_search(self, base_params : dict, starting_estimate : int , update_api : Callable):
        """ Perform binary search on the number of events or markets given a starting estimate
         based on the total entries"""
        low = 0
        high = self.find_max_heuristic(starting_estimate=starting_estimate, base_params=base_params, update_api=update_api)
        last_valid_offset = -1

        # binary search
        while low <= high:
            mid = (low + high) // 2

            offset = mid
            merged_params = base_params.copy()
            merged_params["offset"] = offset

            response = update_api(params=merged_params)
            if response:  # Non-empty => try higher
                last_valid_offset = offset
                low = mid + 1
            else:  # Empty => search lower
                high = mid - 1

        if last_valid_offset == -1:
            return 0  # no events found at all

        return last_valid_offset