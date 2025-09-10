# Double Time HFT: A Cross-Prediction-Market-Exchange Arbitrage Bot

Double Time High Frequency Trader (HFT) is a sophisticated, real-time arbitrage trading bot designed to identify and execute "buy-both" opportunities between two prediction markets: **Polymarket** and **Kalshi**. It operates by listening to live order book data from both exchanges, normalizing it into a consistent internal format, and executing trades when a risk-free profit opportunity is detected.

The entire system is architected using principles from **Domain-Driven Design** and an **Event-Driven** approach, resulting in a codebase that is robust, maintainable, and highly decoupled. The application is now exposed via a **FastAPI** server, allowing for easy interaction and control through a REST API.

## Core Architectural Principles

The design of this application is not accidental; it is a deliberate implementation of modern software architecture patterns to manage the inherent complexity of real-time trading systems.

### 1. Domain-Driven Design (DDD)

DDD is an approach that centers the application's structure and language around the business domain. In our case, the "domain" is the complex world of market arbitrage. Instead of writing simple scripts that manipulate primitive data types like dictionaries and lists, we build a rich **Domain Model** that explicitly represents the core concepts.

**How We Apply DDD:**

* **Explicit Models, Not Primitive Dictionaries:** The heart of our domain layer is a set of Pydantic models that represent trading concepts. We replaced complex dictionaries like `Dict[str, Dict[Platform, ...]]` with rich objects:
    * **`Orderbook`** (`app/domain/models/order_book.py`): A class that represents a live order book for a single asset and encapsulates the logic for applying updates and retrieving the top-of-book.
    * **`MarketOutcomes`** (`app/domain/types.py`): An explicit container that holds the `yes` and `no` `Orderbook` objects for a market on a single platform. This is far more readable and type-safe than a generic dictionary.
    * **`MarketState`** (`app/domain/types.py`): The root aggregate of our domain model. It represents the complete state of a single market across all platforms and contains the business logic for querying prices and deriving values (e.g., `get_kalshi_derived_no_ask_price()`).

* **Layered Architecture (Ports & Adapters):** The codebase is separated into distinct layers, each with a single responsibility. This prevents the core logic from being tightly coupled to external details like API protocols or database schemas.
    * **Domain Layer (`app/domain`)**: The core of the application. It contains the `MarketState` models and business rules. It has **zero knowledge** of how data is fetched or where it is stored.
    * **Service Layer (`app/services`)**: Contains the `FletcherOrchestrator` and `ArbitrageMonitor`. These services orchestrate the use cases of the application, such as "monitor markets for arbitrage," by using the domain models.
    * **Adapter Layer (`app/clients`)**: This layer contains the WebSocket and HTTP clients. These are "adapters" that translate the outside world (the specific API formats of Kalshi and Polymarket) into the language of our domain (standardized `Domain Events`).

### 2. Event-Driven Architecture

The different parts of our system are highly decoupled and communicate asynchronously through a **Message Bus**. Instead of components calling each other directly, they produce and consume **Events**. An event is a simple data object that represents a fact that has occurred (e.g., "the order book has received an update").

**How We Apply an Event-Driven Approach:**

* **The Message Bus (`app/message_bus.py`)**: This is the central nervous system of our application. Components can publish events to the bus, and other components can subscribe to the events they care about.

* **Events as Our Internal Language**: We have defined explicit `Domain Events` that represent significant occurrences:
    * `OrderBookSnapshotReceived`: An event published when we receive a full order book snapshot.
    * `OrderBookDeltaReceived`: An event published when we receive an incremental update to an order book.
    * `ArbitrageOpportunityFound`: Published by the monitor when a profitable trade is identified.
    * `ExecuteTrade`: Published when the system decides to act on an opportunity.

* **Decoupled Producers and Consumers**:
    * **Producers**: The WebSocket clients (`KalshiWebSocketClient` and `PolymarketWebSocketClient`) act as event producers. Their only job is to connect to the external exchanges, listen for data, and publish events to the bus. They have no idea who, if anyone, is listening.
    * **Consumers**: The `MarketManager` and other services contain handlers that subscribe to these events. For example, the `MarketManager`'s `_handle_snapshot` handler listens for `OrderBookSnapshotReceived` events and updates the appropriate `MarketState` model.

This event-driven flow makes the system incredibly flexible and resilient. We can add new consumers of market data (e.g., a data recorder, a new type of monitor) without ever having to change a single line of code in the WebSocket clients.

## System Components

* `app/`
    * `web/`: Contains the FastAPI server, which exposes the application's functionality through a REST API.
    * `clients/`: Adapters for communicating with external services (Kalshi, Polymarket).
    * `domain/`: The core of the application. Contains all business logic, models, and events. It is completely independent of any external framework or API.
        * `models/`: Contains the rich domain models like `Orderbook` and `MarketState`.
        * `primitives.py`: Holds the most basic, independent types like `Money` and `Platform`.
        * `schemas.py`: Contains Pydantic models used to parse and validate raw API data.
        * `events.py`: Defines all domain events used on the message bus.
    * `infra/`: Contains infrastructure concerns like logging configuration and environment settings.
    * `repositories/`: An abstraction layer for data persistence (e.g., `TradeRepository`).
    * `services/`: Contains the application services (`FletcherOrchestrator`, `ArbitrageMonitor`, `TradeExecutor`) that orchestrate the domain models to perform use cases.
    * `utils/`: Contains helper functions and decorators.
* `main.py`: The entry point for the application, responsible for initializing and wiring together all the components.

## Setup and Installation

1.  **Clone Repository**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create Virtual Environment**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    pip install "git+ssh://git@{your_host}/bigmencho/on-tempo.git@main#egg=shared_infra&subdirectory=shared_libraries/shared_infrastructure_container"
    pip install "git+ssh://git@{your_host}/bigmencho/on-tempo.git@main#egg=shared_wallets&subdirectory=shared_libraries/shared_wallets_container"
    ```

4.  **Configure Environment Variables**
    Create a `.env` file in the root directory and populate it with the necessary API keys and secrets:
    ```env
    POLYMARKET_WALLET_PRIVATE_KEY=...
    POLYMARKET_API_KEY=...
    KALSHI_API_KEY_ID=...
    KALSHI_PRIVATE_KEY_PEM_PATH=...
    # Add any other required settings
    ```

## Running the Application

To start the arbitrage bot, run the main entry point using **Uvicorn**:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000