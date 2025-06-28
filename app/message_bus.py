import asyncio
import logging
from collections import defaultdict
from typing import Callable, Type, Dict, List

from app.domain.events import BaseMessage

logger = logging.getLogger(__name__)

# The bus operates on the generic BaseMessage type
Message = BaseMessage


class MessageBus:
    """A simple, in-process message bus."""

    def __init__(self):
        self.subscribers: Dict[Type[Message], List[Callable]] = defaultdict(list)
        self.queue: asyncio.Queue = asyncio.Queue()

    def subscribe(self, message_type: Type[Message], handler: Callable):
        """Register a handler for a specific event or command type."""
        self.subscribers[message_type].append(handler)
        logger.info(f"Handler {handler.__name__} subscribed to {message_type.__name__}")

    def unsubscribe_all(self):
        """Unsubscribe all handlers from the bus."""
        self.subscribers.clear()
        logger.info("All message handlers unsubscribed from the bus.")

    async def publish(self, message: Message):
        """Add any message (event or command) to the queue to be processed."""
        await self.queue.put(message)

    async def run(self):
        """The main event-processing loop."""
        logger.info("Message bus started.")
        while True:
            try:
                message = await self.queue.get()
                message_type = type(message)
                if message_type in self.subscribers:
                    for handler in self.subscribers[message_type]:
                        try:
                            await handler(message)
                        except Exception:
                            logger.exception(f"Exception handling {message_type.__name__} in {handler.__name__}")
                self.queue.task_done()
            except asyncio.CancelledError:
                logger.info("Message bus received cancellation signal.")
                break