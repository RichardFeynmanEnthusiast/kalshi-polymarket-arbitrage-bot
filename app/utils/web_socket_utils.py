import asyncio
from functools import wraps


# --- Decorator Definition ---
def require_asset_ids(method):
    async def async_wrapper(self, *args, **kwargs):
        if not self.asset_ids:
            raise RuntimeError(f"`market_map` must be initialized before calling `{method.__name__}`.")
        return await method(self, *args, **kwargs)

    def sync_wrapper(self, *args, **kwargs):
        if not self.asset_ids:
            raise RuntimeError(f"`market_map` must be initialized before calling `{method.__name__}`.")
        return method(self, *args, **kwargs)

    return async_wrapper if asyncio.iscoroutinefunction(method) else sync_wrapper

def require_initialized(func):
    """
    Decorator that requires the WebSocket client to have both its message bus
    and market map configured before proceeding.
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if getattr(self, 'bus', None) is None:
            raise RuntimeError("`bus` (MessageBus) must be initialized before calling this method.")
        if getattr(self, 'market_map', None) is None:
            raise RuntimeError("`market_map` must be initialized before calling this method.")
        return await func(self, *args, **kwargs)
    return wrapper