import asyncio
import unittest


class ArbitrageTraderTest(unittest.TestCase):
    """ User can pass in markets across venues and view the results of arbitrage trades placed"""
    async def asyncSetUp(self):
        pass

    async def asyncTearDown(self):
        """Clean up after the test"""
        # Cancel the bus task
        if hasattr(self, 'bus_task'):
            self.bus_task.cancel()
            try:
                await self.bus_task
            except asyncio.CancelledError:
                pass

    async def test_user_can_start_running_the_arbitrage_trader(self):
        pass
        # self.fail("The database should return the same trade details of the executed trade")
        # Pirata passes in a tuple of matched markets
        # self.fail("The app should return a message that the app subscribed to the passed in web sockets")
        # Pirata gets notified when an arbitrage opportunity was found
        # self.fail("The app should return a message that an arbitrage opportunity was found and is attempting to trade")
        # Pirata gets notified when a trade gets executed
        # self.fail("The app should return a message notified him if both legs of the trade were placed")
        # Pirata should view the results of the trade in the database