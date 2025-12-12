import asyncio
import json
import logging.config
import uvicorn

from app.application import create_app
from app.settings.logging_config import LOGGING_CONFIG
from app.settings.settings import settings

# Initialize Logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def load_headless_markets(hft_app):
    """Parses TARGET_MARKETS env var and injects them into the app."""
    try:
        if not settings.TARGET_MARKETS:
            return

        markets = json.loads(settings.TARGET_MARKETS)
        if not isinstance(markets, list):
            logger.error("TARGET_MARKETS must be a JSON list of tuples/lists.")
            return

        for m in markets:
            if len(m) == 2:
                hft_app.markets_to_trade.append(tuple(m))
                logger.info(f"Added market pair from config: {m}")
            else:
                logger.warning(f"Invalid market pair format: {m}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse TARGET_MARKETS json: {e}")

if __name__ == "__main__":
    # Create the core application logic (Headless by default)
    hft_app = create_app()

    if settings.ENABLE_API:
        logger.info("API Enabled. Starting FastAPI server...")
        # Import API module only if enabled to avoid side effects or heavy imports
        from app.web.api import app

        # Inject the initialized app into FastAPI state
        app.state.hft_app = hft_app

        # In API mode, we still allow loading initial markets from ENV
        load_headless_markets(hft_app)

        # Start Server
        uvicorn.run(app, host="0.0.0.0", port=8001)

    else:
        logger.info("API Disabled. Starting in Headless Mode...")

        load_headless_markets(hft_app)

        if not hft_app.markets_to_trade:
            logger.warning("No markets configured in TARGET_MARKETS. App will start but idle until configured.")

        try:
            asyncio.run(hft_app.start())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Headless application stopped.")