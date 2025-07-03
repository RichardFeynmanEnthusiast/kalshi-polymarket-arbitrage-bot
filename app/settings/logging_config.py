from pathlib import Path

# Create a central directory for logs
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Define a reasonable max size for log rotation (e.g., 10 MB) and backup count
MAX_BYTES = 10 * 1024 * 1024
BACKUP_COUNT = 5

# Define dedicated log files for different application domains
SERVICE_LOG_FILE = LOG_DIR / "service.log"          # For general application lifecycle and orchestration
MARKET_DATA_LOG_FILE = LOG_DIR / "market_data.log"  # For raw data ingestion, connections, etc.
TRADING_LOG_FILE = LOG_DIR / "trading.log"          # For strategy decisions, opportunities, and trade executions

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # Human-readable format for the console
        "console_formatter": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        # Structured JSON format for log files
        "json_formatter": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d",
        },
    },
    "handlers": {
        # Handler for pretty console output (human-friendly)
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console_formatter",
            "level": "INFO",  # Keep console output clean
        },
        # Rotating file handler for general service logs
        "service_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(SERVICE_LOG_FILE),
            "formatter": "json_formatter",
            "maxBytes": MAX_BYTES,
            "backupCount": BACKUP_COUNT,
        },
        # Rotating file handler for market data specific logs
        "market_data_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(MARKET_DATA_LOG_FILE),
            "formatter": "json_formatter",
            "maxBytes": MAX_BYTES,
            "backupCount": BACKUP_COUNT,
        },
        # Rotating file handler for trading logic specific logs
        "trading_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(TRADING_LOG_FILE),
            "formatter": "json_formatter",
            "maxBytes": MAX_BYTES,
            "backupCount": BACKUP_COUNT,
        },
    },
    # Define loggers for specific parts of the application
    "loggers": {
        "app.ingestion": {
            "handlers": ["market_data_file", "console"],
            "level": "DEBUG",  # Log everything from ingestion to its dedicated file
            "propagate": False,
        },
        "app.strategies": {
            "handlers": ["trading_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app.execution": {
            "handlers": ["trading_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "app.markets": {
            "handlers": ["service_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "app.orchestration": {
            "handlers": ["service_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        "httpx": {
            "handlers": ["service_file", "console"],  # or use a dedicated file if you want
            "level": "DEBUG",
            "propagate": False,
        },
        "httpcore": {
            "handlers": ["service_file", "console"],  # or use a dedicated file if you want
            "level": "DEBUG",
            "propagate": False,
        },
    },
    # The root logger catches all other logs
    "root": {
        "handlers": ["service_file", "console"],
        "level": "INFO",
    },
}