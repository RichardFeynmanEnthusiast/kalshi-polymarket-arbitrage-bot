# Double Time HFT: Kalshi-Polymarket Arbitrage Bot

Double Time HFT is a real-time arbitrage trading bot designed to identify and execute "buy-both" arbitrage opportunities between the prediction markets **Polymarket** and **Kalshi**. It operates by listening to live order book data from both exchanges, normalizing the data, and executing trades when a potential arbitrage opportunity is detected.

The system is built using principles from **Domain-Driven Design (DDD)** and an **Event-Driven Architecture (EDA)**. It exposes its functionality via a **FastAPI** server.

## Architecture

The application employs DDD and EDA to manage complexity and promote decoupling.

### 1. Domain-Driven Design (DDD)

The application's structure focuses on the trading domain. Key concepts are represented by explicit models rather than primitive types.

* **Domain Models:** Pydantic models represent core trading concepts:
    * **`Orderbook`** (`app/markets/order_book.py`): Represents the live order book for a single asset, including logic for updates and retrieving top-of-book data.
    * **`MarketOutcomes`** (`app/markets/state.py`): Holds the `yes` and `no` `Orderbook` objects for a market on a single platform.
    * **`MarketState`** (`app/markets/state.py`): Represents the state of a single market across both platforms, containing logic for querying prices and deriving related values (e.g., `get_kalshi_derived_no_ask_price()`).
* **Layered Architecture (Ports & Adapters):**
    * **Domain Layer (`app/domain`)**: Contains core models and business rules, independent of external systems.
    * **Service Layer (`app/services`)**: Orchestrates application use cases (e.g., monitoring markets) using domain models. Includes `FletcherOrchestrator` and `ArbitrageMonitor`.
    * **Adapter Layer (`app/clients`)**: Contains WebSocket and HTTP clients that translate external API formats (Kalshi, Polymarket) into internal domain events.

### 2. Event-Driven Architecture (EDA)

Components communicate asynchronously via a **Message Bus** using **Events**.

* **Message Bus (`app/message_bus.py`)**: Central component for event publishing and subscription.
* **Domain Events (`app/domain/events.py`)**: Represent significant occurrences, such as:
    * `OrderBookSnapshotReceived`
    * `OrderBookDeltaReceived`
    * `ArbitrageOpportunityFound`
    * `ExecuteTrade`
* **Producers and Consumers**:
    * **Producers**: WebSocket clients (`KalshiWebSocketClient`, `PolymarketWebSocketClient`) publish events based on data received from exchanges.
    * **Consumers**: Services like `MarketManager` subscribe to events and update state or trigger actions accordingly.

## System Components

* `app/`
    * `web/`: FastAPI server providing a REST API.
    * `clients/`: Adapters for Kalshi and Polymarket APIs.
    * `domain/`: Core business logic, models (`models/`), primitive types (`primitives.py`), API data schemas (`schemas.py`), and events (`events.py`).
    * `infra/`: Infrastructure concerns like logging and settings.
    * `repositories/`: Data persistence abstractions (e.g., `TradeRepository`).
    * `services/`: Application services (`FletcherOrchestrator`, `ArbitrageMonitor`, `TradeExecutor`).
    * `utils/`: Helper functions.
* `main.py`: Application entry point for initialization and component wiring.

## Setup and Installation

1.  **Clone Repository**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    # Install shared libraries (adjust paths/URLs as needed)
    pip install "git+ssh://git@{your_host}/bigmencho/on-tempo.git@main#egg=shared_infra&subdirectory=shared_libraries/shared_infrastructure_container"
    pip install "git+ssh://git@{your_host}/bigmencho/on-tempo.git@main#egg=shared_wallets&subdirectory=shared_libraries/shared_wallets_container"
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory and add the necessary API keys and configuration:
    ```env
    # General Settings
    APP_ENV=prod # or demo

    # Kalshi Demo Credentials (if using demo)
    KALSHI_DEMO_API_KEY=...
    KALSHI_DEMO_PRIVATE_KEY_PATH=private-keys/kalshi_demo_private.pem

    # Kalshi Prod Credentials (if using prod)
    KALSHI_PROD_API_KEY=...
    KALSHI_PROD_PRIVATE_KEY_PATH=private-keys/kalshi_prod_private.pem

    # Polymarket Credentials
    POLYMARKET_API_KEY=...
    POLYMARKET_WALLET_PRIVATE_KEY=...
    POLYMARKET_WALLET_ADDR=...

    # Supabase Credentials (for data storage)
    SUPABASE_URL=...
    SUPABASE_KEY=...

    # Trading Parameters
    KALSHI_FEE_RATE=0.07
    MIN_PROFIT_THRESHOLD=0.00 # Minimum profit required to trade
    DRY_RUN=True # Set to False to execute real trades
    SHUTDOWN_BALANCE=10.00 # Stop trading if balance drops below this
    MINIMUM_WALLET_BALANCE=100.00 # Initial minimum required balance across wallets
    ```

## Running the Application

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
