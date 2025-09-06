from typing import Tuple

from cryptography.hazmat.primitives import serialization

from app.clients.kalshi import KalshiHttpClient
from app.ingestion.kalshi_wss_client import KalshiWebSocketClient
from app.settings.env import Environment
from app.settings.settings import settings, BASE_DIR_1


class KalshiClientFactory:
    """
    Factory class for creating Kalshi HTTP and WebSocket clients.
    Configuration is loaded from the central settings object.
    """
    def __init__(self) -> None:
        # Determine environment from the imported settings
        app_env = getattr(settings, "APP_ENV", "demo").lower()
        self.environment = Environment.PROD if app_env == "prod" else Environment.DEMO

        # Load credentials (API key and private key) based on the environment
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Populate self.api_key and self.private_key; raise clear errors."""
        # Load the API key from the imported settings
        if self.environment == Environment.DEMO:
            self.api_key = settings.KALSHI_DEMO_API_KEY
            key_path_str = settings.KALSHI_DEMO_PRIVATE_KEY_PATH
        else:  # Assumes Environment.PROD
            self.api_key = settings.KALSHI_PROD_API_KEY
            key_path_str = settings.KALSHI_PROD_PRIVATE_KEY_PATH

        if not self.api_key:
            raise ValueError(f"Missing Kalshi API key for {self.environment.name} environment in settings.")

            # Construct path relative to the project's BASE_DIR from settings
        self.key_file_path = BASE_DIR_1 / key_path_str

        if not self.key_file_path.exists():
            raise FileNotFoundError(
                f"Kalshi private-key file not found at {self.key_file_path} "
                f"for {self.environment.name} environment."
            )

        with self.key_file_path.open("rb") as fh:
            self.private_key = serialization.load_pem_private_key(
                fh.read(),
                password=None,
            )

    def create_http_client(self) -> KalshiHttpClient:
        """Create and return a configured HTTP client."""
        return KalshiHttpClient(
            key_id=self.api_key,
            private_key=self.private_key,
            environment=self.environment
        )

    def create_websocket_client(
        self,
        connection_timeout_seconds: int = 15
    ) -> KalshiWebSocketClient:
        """Create and return a configured WebSocket client."""
        return KalshiWebSocketClient(
            key_id=self.api_key,
            private_key=self.private_key,
            # manager=manager,
            # markets_config=markets_config,
            environment=self.environment,
            connection_timeout_seconds=connection_timeout_seconds
        )

    def create_both_clients(
            self,
            connection_timeout_seconds: int = 15
    ) -> Tuple[KalshiHttpClient, KalshiWebSocketClient]:
        """Return (HTTP client, WebSocket client)."""
        return (
            self.create_http_client(),
            self.create_websocket_client(
                connection_timeout_seconds=connection_timeout_seconds
            ),
        )
