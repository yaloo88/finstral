Here's a README file for your Questrade API project:

# Questrade API Wrapper

A Python wrapper for the Questrade API that provides easy access to account information, market data, and trading functionality. The project includes comprehensive data management capabilities with local storage and analysis tools.

## Features

- Account management (balances, positions, orders, activities)
- Market data access (quotes, candles, symbol search)
- Local symbol caching with SQLite database
- Historical candle data storage and management
- CSV symbol list import functionality
- Automatic token refresh handling
- Data analysis and visualization tools
- Support for multiple database backends (SQLite, PostgreSQL)

## Installation

1. Clone this repository:```bash
git clone https://github.com/yaloo88/finstral
```

2. Install required dependencies:
```bash
pip install requests pandas numpy matplotlib seaborn sqlite3
```

## Setup

1. Get your Questrade API credentials:
   - Log into your Questrade account
   - Go to App Hub
   - Register a personal app to get your refresh token

2. On first run, you'll be prompted to enter your refresh token. The token will be saved locally for future use.

3. Initialize the database:
```python
from src.local_candles import initialize_db, optimize_database
initialize_db()
optimize_database()
```

## Example Notebooks

> **💡 Tip: For detailed examples and interactive demonstrations, check out these notebooks:**
> - `notebooks/1_qt_api.ipynb` - Complete walkthrough of API functionality
> - `notebooks/2_local_symbols.ipynb` - Symbol management and caching examples
> - `notebooks/3_local_candles.ipynb` - Historical data handling and analysis demos
>
> These notebooks contain step-by-step examples, code snippets, and visualizations that will help you get started quickly.

## Usage Examples

### Account Information
```python
from src.qt_api.qt_api import qt_api as qt

# Get account list
accounts = qt.get_questrade_accounts()

# Get positions for an account
positions = qt.get_questrade_positions(account_id)

# Get account balances
balances = qt.get_questrade_balances(account_id)
```

### Market Data
```python
# Search for symbols
results = qt.search_symbols("AAPL")

# Get market quotes
quote = qt.get_market_quote(symbol_id=123456)

# Get historical candles
candles = qt.get_candles(
    symbol_id=123456,
    start_time="2023-01-01T00:00:00-05:00",
    end_time="2023-12-31T23:59:59-05:00",
    interval="OneDay"
)
```

### Local Symbol Management
```python
from src.local_symbols import get_local_symbol, import_symbols_from_csv

# Get symbol details (cached locally)
symbol_info = get_local_symbol("AAPL")

# Import symbols from CSV
imported_count = import_symbols_from_csv("path/to/symbols.csv")
```

### Historical Data Management
```python
from src.local_candles import get_candles, save_candles

# Fetch and store historical data
candles = get_candles("AAPL", "OneDay", "2023-01-01", "2023-12-31")
save_candles(candles)

# Retrieve stored data
stored_candles = get_candles("AAPL", "OneDay", "2023-01-01", "2023-12-31")
```

## Project Structure

```
├── src/
│   ├── qt_api/
│   │   └── qt_api.py         # Main API wrapper
│   ├── local_symbols.py      # Local symbol management
│   └── local_candles.py      # Historical data management
├── notebooks/
│   ├── 1_qt_api.ipynb        # API exploration notebook
│   ├── 2_local_symbols.ipynb # Symbol management notebook
│   └── 3__local_candles.ipynb # Historical data notebook
├── data/
│   ├── local_symbols.db      # SQLite database for symbol cache
│   └── candles.db            # SQLite database for historical data
└── README.md
```

## API Reference

### Account Endpoints
- `get_questrade_accounts()` - Get list of accounts
- `get_questrade_positions(account_id)` - Get account positions
- `get_questrade_balances(account_id)` - Get account balances
- `get_questrade_executions(account_id)` - Get trade executions
- `get_account_orders(account_id)` - Get account orders
- `get_account_activities(account_id)` - Get account activities

### Market Data Endpoints
- `get_markets()` - Get market information
- `search_symbols(prefix)` - Search for symbols
- `get_symbol_details(symbol_id)` - Get detailed symbol information
- `get_candles(symbol_id, start_time, end_time)` - Get historical price data
- `get_market_quote(symbol_id)` - Get current market quotes

### Local Symbol Management
- `save_local_symbol(symbol)` - Save symbol details to local database
- `get_local_symbol(symbol)` - Retrieve symbol from local database
- `get_all_local_symbols()` - Get all cached symbols
- `import_symbols_from_csv(file_path)` - Import symbols from CSV file

### Historical Data Management
- `get_candles(symbol, interval, start_date, end_date)` - Get historical candles
- `save_candles(candles)` - Save candle data to database
- `initialize_db()` - Initialize the database
- `optimize_database()` - Apply database optimizations

## Error Handling

The wrapper includes automatic token refresh and retry logic for expired tokens. Other API errors will raise exceptions with descriptive error messages.

## Contributing

Feel free to submit issues, fork the repository and create pull requests for any improvements.

## License

[Your chosen license]

## Disclaimer

This is an unofficial wrapper for the Questrade API. Use at your own risk. Always verify the data and behavior matches your trading requirements.
