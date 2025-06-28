from typing import Tuple

from app.clients.polymarket.clob_http import PolymClobHttpClient
from app.ingestion.clob_wss import PolymarketWebSocketClient
from app.settings.env import Environment
from app.settings.settings import settings


class PolymarketClientFactory:
    """
    Factory class for creating Polymarket CLOB HTTP and WebSocket clients.
    Configuration is loaded from the central settings object.
    """
    def __init__(self) -> None:
        # Determine environment from the imported settings
        app_env = getattr(settings, "APP_ENV", "demo").lower()
        self.environment = Environment.DEMO if app_env == "demo" else Environment.DEMO

        # Load credentials based on the environment
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Populate self.wallet_pk and self.api_key; raise clear errors."""
        # Load credentials from the imported settings
        self.wallet_pk = settings.POLYMARKET_WALLET_PRIVATE_KEY
        self.wallet_addr = settings.POLYMARKET_WALLET_ADDR
        self.api_key = settings.POLYMARKET_API_KEY

        if not self.wallet_pk:
            raise ValueError(f"Missing Polymarket wallet private key for {self.environment.name} environment in settings.")
        
        if not self.api_key:
            raise ValueError(f"Missing Polymarket API key for {self.environment.name} environment in settings.")

    def create_http_client(self) -> PolymClobHttpClient:
        """Create and return a configured HTTP client."""
        return PolymClobHttpClient(
            polym_wallet_pk=self.wallet_pk,
            polym_wallet_addr=self.wallet_addr,
            polym_clob_api_key=self.api_key,
            environment=self.environment
        )

    def create_websocket_client(
        self,
        connection_timeout_seconds: int = 15
    ) -> PolymarketWebSocketClient:
        """Create and return a configured WebSocket client."""
        return PolymarketWebSocketClient(
            polym_wallet_pk=self.wallet_pk,
            polym_clob_api_key=self.api_key,
            environment=self.environment,
            connection_timeout_seconds=connection_timeout_seconds
        )

    def create_both_clients(
            self,
            connection_timeout_seconds: int = 15
    ) -> Tuple[PolymClobHttpClient, PolymarketWebSocketClient]:
        """Return (HTTP client, WebSocket client)."""
        return (
            self.create_http_client(),
            self.create_websocket_client(
                connection_timeout_seconds=connection_timeout_seconds
            ),
        )