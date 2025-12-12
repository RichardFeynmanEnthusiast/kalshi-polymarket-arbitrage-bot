# Double Time HFT: Kalshi-Polymarket Arbitrage Bot

Double Time HFT is a real-time arbitrage trading bot designed to identify and execute "buy-both" arbitrage opportunities between the prediction markets **Polymarket** and **Kalshi**. 

## Architecture

The application is built using **Domain-Driven Design (DDD)** principles and an **Event-Driven Architecture (EDA)**. It follows a "Ports and Adapters" (Hexagonal) pattern to decouple core business logic from external infrastructure.

### 1. Core Components

* **Domain Layer (`app/domain`)**: Contains the business logic and state. It has no dependencies on external libraries or API clients.
    * **Models**: `Orderbook`, `MarketState` (the unified view of a market across venues), and `ArbitrageOpportunity`.
    * **Events**: Standardized events like `OrderBookDeltaReceived` and `ArbitrageOpportunityFound` that drive the system.

* **Service Layer (`app/services`)**: Orchestrates the domain logic to perform specific tasks.
    * **`MarketManager`**: Consumes raw market data events to maintain the live `MarketState`.
    * **`ArbitrageMonitor`**: The strategy engine. It listens for state updates, calculates potential arbitrage (considering fees and slippage), and emits opportunity events.
    * **`TradeExecutor`**: Handles the execution logic. It validates wallet balances, calculates optimal trade sizes (e.g., Square Root sizing), and coordinates order placement.
    * **`BalanceService`**: Maintains an internal view of wallet balances to prevent overdrafts and enforce risk limits (`SHUTDOWN_BALANCE`).

* **Infrastructure / Adapters**:
    * **Ingestion (`app/ingestion`)**: WebSocket clients that connect to Kalshi and Polymarket, normalize their specific data formats, and publish standardized Domain Events to the bus.
    * **Gateways (`app/gateways`)**: Abstractions for external I/O. `TradeGateway` handles the actual HTTP API calls to place orders. `MarketDataGateway` fetches static market details (tickers, token IDs).
    * **Repositories**: Abstractions for data persistence (e.g., Supabase).

### 2. Data Flow

The system operates as a reactive pipeline:

1.  **Ingestion**: `PolymarketWebSocketClient` and `KalshiWebSocketClient` receive raw price updates. They convert these into `OrderBookDeltaReceived` events and publish them to the `MessageBus`.
2.  **State Update**: `MarketManager` receives these deltas and updates the in-memory `Orderbook`. If the "Top of Book" changes, it emits a `MarketBookUpdated` event.
3.  **Strategy Check**: `ArbitrageMonitor` receives the update event. It queries the `MarketState` for the best prices across venues.
    * *Logic*: It checks if `Cost(Poly_YES) + Cost(Kalshi_NO) < 1.00 - Fees - ProfitMargin`.
    * If profitable, it locks the monitor and publishes `ArbitrageOpportunityFound`.
4.  **Execution**: `TradeExecutor` receives the opportunity. It checks the `BalanceService` for funds and sends buy orders to `TradeGateway`.
5.  **Result & Reset**: Trade results are published. If successful, the `FletcherOrchestrator` triggers a "Cool Down," resets the internal state, and restarts the WebSocket streams to ensure data integrity.

## Token & Outcome Mapping

The bot automatically maps outcomes between the two platforms:

* **Polymarket**: Outcomes are identified by **Token IDs**. The bot uses the `clobTokenIds` array from the API.
    * Index `0` is mapped to **YES**.
    * Index `1` is mapped to **NO**.
* **Kalshi**: Outcomes are identified by `ticker` and `side`.
    * **YES** trades use `side="yes"`.
    * **NO** trades use `side="no"`.

## Configuration (`.env`)

Create a `.env` file in the root directory. Below is the complete list of supported configuration variables.

### General & Mode Settings
| Variable | Description | Default/Example |
| :--- | :--- | :--- |
| `APP_ENV` | Application environment. Controls which Kalshi API endpoints are used. | `prod` or `demo` |
| `ENABLE_API` | If `True`, starts the FastAPI server. If `False`, runs the trading loop immediately (headless). | `True` |
| `DRY_RUN` | If `True`, no real orders are placed. Trade execution is simulated and logged. | `True` |
| `TARGET_MARKETS` | **Required if ENABLE_API=False**. A JSON string of market pairs to trade. Format: `[["POLY_MARKET_ID", "KALSHI_TICKER"]]` | `'[["601699", "KXFEDDECISION-26JAN-H0"]]'` |

### Credentials: Kalshi
| Variable | Description |
| :--- | :--- |
| `KALSHI_PROD_API_KEY` | Your Kalshi Production API Key ID (UUID). |
| `KALSHI_PROD_PRIVATE_KEY_PATH` | Relative path to your Kalshi Production Private Key file (e.g., `private-keys/kalshi.txt`). |
| `KALSHI_DEMO_API_KEY` | Your Kalshi Demo API Key ID. |
| `KALSHI_DEMO_PRIVATE_KEY_PATH` | Relative path to your Kalshi Demo Private Key file. |

### Credentials: Polymarket
| Variable | Description |
| :--- | :--- |
| `POLYMARKET_API_KEY` | Your Polymarket CLOB API Key. |
| `POLYMARKET_WALLET_PRIVATE_KEY` | The private key of the wallet used to sign transactions (Polygon/Ethereum). |
| `POLYMARKET_WALLET_ADDR` | The public address of your Polymarket wallet. |

### Infrastructure
| Variable | Description |
| :--- | :--- |
| `SUPABASE_URL` | URL for your Supabase database instance. |
| `SUPABASE_KEY` | API Key for Supabase. |

### Risk & Trading Parameters
| Variable | Description | Default |
| :--- | :--- | :--- |
| `KALSHI_FEE_RATE` | Fee rate to assume for Kalshi trades (e.g., 0.07 for 7%). | `0.07` |
| `MIN_PROFIT_THRESHOLD` | Minimum profit margin required to execute a trade (0.00 - 1.00). | `0.00` |
| `SHUTDOWN_BALANCE` | If wallet balances drop below this amount ($), the bot will shutdown. | `10.00` |
| `MINIMUM_WALLET_BALANCE` | The target minimum balance required to operate. Used for calculating "Max Spend". | `100.00` |

## Setup and Installation

1.  **Clone & Install Dependencies**
    ```bash
    git clone https://github.com/RichardFeynmanEnthusiast/kalshi-polymarket-arbitrage-bot.git
    cd kalshi-polymarket-arbitrage-bot
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Configure Environment**
    Copy the example above into a file named `.env`.

3.  **Running the Bot**
    The application has a single entry point that adapts based on your `.env` settings.

    ```bash
    python -m app.main
    ```
    * **Headless Mode**: Set `ENABLE_API=False`. The bot will immediately connect to the markets defined in `TARGET_MARKETS`.
    * **API Mode**: Set `ENABLE_API=True`. The bot will start a web server on port 8001. You can then configure markets dynamically via HTTP requests.

## Local Packages
This project includes vendored versions of `shared_infra` and `shared_wallets` located in `shared_libraries/`. These are installed automatically via `requirements.txt`.