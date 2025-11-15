import logging.config

import uvicorn

from app.application import create_app
from app.settings.logging_config import LOGGING_CONFIG
from app.web.api import app

logging.config.dictConfig(LOGGING_CONFIG)

app.state.hft_app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)