import sys
import os
import datetime
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import pandas as pd
import logging

# Add the parent directory to sys.path to make the api module importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import qt_api.qt_api as qt
import src.local_symbols as local_symbols

# Code Review: Candle Data Management System (SQL Version)

## Overall Assessment

## SQL Migration Recommendations

### 1. Database Setup and Connection

import sqlite3  # For local development
import time
from contextlib import contextmanager
# Or for production:
import psycopg2  # PostgreSQL
# import sqlalchemy

DB_SYSTEM = 'sqlite'  # 'sqlite' or 'postgres'

POSTGRES_HOST = "localhost"
POSTGRES_DATABASE = "candles"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "password"

DEBUG = False

# Define base paths
BASE_DIR = Path(__file__).resolve().parent.parent  # Gets the project root directory
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'candles.db'

def ensure_data_directory():
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\033[92m✓ Data directory ensured at: {DATA_DIR}\033[0m")

@contextmanager
def get_db_connection(max_retries=5, retry_delay=1):
    """
    Create and return a database connection with retry mechanism.
    Uses context manager to ensure proper connection handling.
    """
    if DEBUG:
        ensure_data_directory()  # Ensure data directory exists before connecting
    
    for attempt in range(max_retries):
        try:
            if DB_SYSTEM == 'sqlite':
                conn = sqlite3.connect(str(DB_PATH), timeout=20)  # Use absolute path
                conn.execute("PRAGMA foreign_keys = ON")
                conn.row_factory = sqlite3.Row
            elif DB_SYSTEM == 'postgres':
                # Replace with your PostgreSQL connection details
                conn = psycopg2.connect(
                    host=POSTGRES_HOST,
                    database=POSTGRES_DATABASE,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD
                )
            else:
                raise ValueError(f"Unsupported database system: {DB_SYSTEM}")
                
            yield conn
            return
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"\033[93m⚠ Database locked, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})\033[0m")
                time.sleep(retry_delay)
            else:
                print(f"\033[91m❌ Database error: {str(e)}\033[0m")
                print(f"\033[93m⚠ Attempted to access database at: {DB_PATH}\033[0m")
                raise
        except psycopg2.OperationalError as e:
            if attempt < max_retries - 1:
                print(f"\033[93m⚠ PostgreSQL connection error, retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})\033[0m")
                time.sleep(retry_delay)
            else:
                raise
        finally:
            try:
                conn.close()
            except UnboundLocalError:
                pass

def initialize_db():
    """Create database tables if they don't exist."""
    print(f"\033[92m➡ Initializing database at: {DB_PATH}\033[0m")
    if DEBUG:
        ensure_data_directory()
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            if DB_SYSTEM == 'sqlite':
                # Create symbols table
                cur.execute('''
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol_id TEXT PRIMARY KEY,
                    symbol TEXT UNIQUE NOT NULL,
                    description TEXT
                )
                ''')
                
                # Create candles table
                cur.execute('''
                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    VWAP REAL,
                    UNIQUE(symbol, interval, start)
                )
                ''')
            elif DB_SYSTEM == 'postgres':
                # Create symbols table
                cur.execute('''
                CREATE TABLE IF NOT EXISTS symbols (
                    symbol_id TEXT PRIMARY KEY,
                    symbol TEXT UNIQUE NOT NULL,
                    description TEXT
                )
                ''')
                
                # Create candles table
                cur.execute('''
                CREATE TABLE IF NOT EXISTS candles (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    VWAP REAL,
                    UNIQUE(symbol, interval, start)
                )
                ''')
            
            conn.commit()
            print("\033[92m✓ Database tables created successfully\033[0m")
            
    except Exception as e:
        print(f"\033[91m❌ Error initializing database: {str(e)}\033[0m")
        raise


### 2. Modified Functions for SQL-Based Operations


def get_candle_df(symbol, days_back=120, interval="OneMinute"):
    """
    Fetch candle data for a given symbol and return a formatted DataFrame.
    """
    symbol_info = local_symbols.get_local_symbol(symbol)
    start_time = (datetime.datetime.now() - datetime.timedelta(days=days_back)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).astimezone().isoformat()
    
    end_time = datetime.datetime.now().replace(
        hour=23, minute=59, second=0, microsecond=0
    ).astimezone().isoformat()
    
    candles = qt.get_candles(symbol_info['symbolId'], start_time, end_time, interval)
    df = pd.DataFrame(candles['candles'])
    
    if df.empty or 'start' not in df.columns:
        print(f"\033[91m❌ No candle data returned for symbol {symbol}\033[0m")
        return pd.DataFrame()
    
    df['symbol'] = symbol_info['symbol']
    df['interval'] = interval
    return df  # No need to set index for SQL storage

def update_candles_for_symbol(symbol, interval="OneMinute"):
    """
    Update or insert candle data for a given symbol in the SQL database.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # First, ensure symbol exists in symbols table
            symbol_info = local_symbols.get_local_symbol(symbol)
            
            if DB_SYSTEM == 'sqlite':
                cur.execute("INSERT OR IGNORE INTO symbols (symbol_id, symbol) VALUES (?, ?)",
                            (symbol_info['symbolId'], symbol))
                
                # Get the last timestamp in the database for this symbol and interval
                cur.execute("""
                SELECT MAX(end) FROM candles 
                WHERE symbol = ? AND interval = ?
                """, (symbol, interval))
            elif DB_SYSTEM == 'postgres':
                cur.execute("""
                INSERT INTO symbols (symbol_id, symbol) 
                VALUES (%s, %s)
                ON CONFLICT (symbol_id) DO NOTHING
                """, (symbol_info['symbolId'], symbol))
                
                # Get the last timestamp in the database for this symbol and interval
                cur.execute("""
                SELECT MAX(end) FROM candles 
                WHERE symbol = %s AND interval = %s
                """, (symbol, interval))
            
            result = cur.fetchone()
            last_end = result[0] if result and result[0] else None
            
            if not last_end:
                # No existing data, fetch all
                new_df = get_candle_df(symbol, interval=interval)
            else:
                # Fetch only new data
                start_time = last_end
                end_time = datetime.datetime.now().replace(
                    hour=23, minute=59, second=0, microsecond=0
                ).astimezone().isoformat()
                
                candles = qt.get_candles(symbol_info['symbolId'], start_time, end_time, interval)
                new_df = pd.DataFrame(candles['candles'])
                
                if new_df.empty:
                    print(f"\033[93m⚠ No new candle updates for symbol {symbol}\033[0m")
                    return
                    
                print(f"\033[92m📊 Updating existing candle data for symbol {symbol}\033[0m")
                new_df['symbol'] = symbol
                new_df['interval'] = interval
            
            if not new_df.empty:
                # Insert the new data
                records = new_df.to_dict('records')
                for record in records:
                    if DB_SYSTEM == 'sqlite':
                        cur.execute("""
                        INSERT OR REPLACE INTO candles 
                        (symbol, interval, start, end, open, high, low, close, volume, VWAP)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            record['symbol'],
                            record['interval'],
                            record['start'],
                            record['end'],
                            record.get('open'),
                            record.get('high'),
                            record.get('low'),
                            record.get('close'),
                            record.get('volume'),
                            record.get('VWAP')
                        ))
                    elif DB_SYSTEM == 'postgres':
                        cur.execute("""
                        INSERT INTO candles 
                        (symbol, interval, start, end, open, high, low, close, volume, VWAP)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, interval, start) DO UPDATE SET
                        end = EXCLUDED.end,
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        VWAP = EXCLUDED.VWAP
                        """, (
                            record['symbol'],
                            record['interval'],
                            record['start'],
                            record['end'],
                            record.get('open'),
                            record.get('high'),
                            record.get('low'),
                            record.get('close'),
                            record.get('volume'),
                            record.get('VWAP')
                        ))
            
            conn.commit()
            print(f"\033[92m✓ Database updated for {symbol}\033[0m")
            
    except Exception as e:
        print(f"\033[91m❌ Error updating {symbol}: {str(e)}\033[0m")
        raise

def update_all_symbols():
    """Process all symbols and update their candle data in the SQL database."""
    try:
        with get_db_connection() as conn:
            initialize_db()  # Ensure database tables exist
            optimize_database()
    except Exception as e:
        print(f"\033[91m❌ Error initializing database: {str(e)}\033[0m")
        return

    all_symbols = local_symbols.get_all_local_symbols()
    
    total_symbols = len(all_symbols)
    for i, symbol_data in enumerate(all_symbols):
        symbol = symbol_data['symbol']
        progress = (i / total_symbols) * 100
        bar_length = 30
        filled_length = int(bar_length * i // total_symbols)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        print(f"\r\033[92m[{bar}] {progress:.1f}% - Processing: {symbol}\033[0m", end='')
        
        try:
            update_candles_for_symbol(symbol)
        except Exception as e:
            logging.error(f"Error updating {symbol}: {e}")
            print(f"\n\033[91m❌ Error updating {symbol}: {str(e)}\033[0m")
            continue
    
    print("\n\033[92m✓ All symbols processed successfully.\033[0m")

def load_all_candles():
    """Load all candle data from the database into a pandas DataFrame."""
    with get_db_connection() as conn:
        try:
            query = """
            SELECT * FROM candles
            ORDER BY symbol, interval, start
            """
            df = pd.read_sql_query(query, conn)
            
            if not df.empty:
                # Set multi-index for compatibility with original code
                df.set_index(['symbol', 'interval', 'start'], inplace=True)
            
            return df
        except Exception as e:
            print(f"\033[91m❌ Error loading data from database: {e}\033[0m")
            return pd.DataFrame()


### 3. Enhanced Functions for SQL Advantages

def get_candles_for_period(symbol, start_date, end_date, interval="OneMinute"):
    """Query candles for a specific time period."""
    with get_db_connection() as conn:
        if DB_SYSTEM == 'sqlite':
            query = """
            SELECT * FROM candles
            WHERE symbol = ? AND interval = ?
            AND start >= ? AND start <= ?
            ORDER BY start
            """
            df = pd.read_sql_query(query, conn, params=(symbol, interval, start_date, end_date))
        elif DB_SYSTEM == 'postgres':
            query = """
            SELECT * FROM candles
            WHERE symbol = %s AND interval = %s
            AND start >= %s AND start <= %s
            ORDER BY start
            """
            df = pd.read_sql_query(query, conn, params=(symbol, interval, start_date, end_date))
        
        return df

def get_latest_price(symbol):
    """Get the most recent closing price for a symbol."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        if DB_SYSTEM == 'sqlite':
            cur.execute("""
            SELECT close FROM candles
            WHERE symbol = ?
            ORDER BY start DESC
            LIMIT 1
            """, (symbol,))
        elif DB_SYSTEM == 'postgres':
            cur.execute("""
            SELECT close FROM candles
            WHERE symbol = %s
            ORDER BY start DESC
            LIMIT 1
            """, (symbol,))
        
        result = cur.fetchone()
        return result[0] if result else None

def backup_database():
    """Create a backup of the database."""
    import shutil
    from datetime import datetime
    
    if DB_SYSTEM == 'sqlite':
        source = str(DB_PATH)
        backup_dir = DATA_DIR / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d')
        destination = backup_dir / f"candles_backup_{timestamp}.db"
        
        shutil.copy2(source, destination)
        print(f"\033[92m✓ Database backed up to {destination}\033[0m")
    elif DB_SYSTEM == 'postgres':
        # For PostgreSQL, use pg_dump
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = DATA_DIR / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / f"candles_backup_{timestamp}.sql"
        
        # Adjust these parameters for your PostgreSQL setup
        db_name = "candles"
        db_user = "postgres"
        db_host = "localhost"
        
        try:
            os.system(f"pg_dump -U {db_user} -h {db_host} -d {db_name} -f {str(backup_file)}")
            print(f"\033[92m✓ PostgreSQL database backed up to {backup_file}\033[0m")
        except Exception as e:
            print(f"\033[91m❌ Error backing up PostgreSQL database: {e}\033[0m")


### 4. Additional Improvements

# Add index to improve query performance
def optimize_database():
    """Add indexes to improve query performance."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        if DB_SYSTEM == 'sqlite':
            # Index for time-based queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_time ON candles(symbol, interval, start)")
            
            # Index for symbol-based queries
            cur.execute("CREATE INDEX IF NOT EXISTS idx_candles_symbol ON candles(symbol)")
        elif DB_SYSTEM == 'postgres':
            # Check if index exists before creating (PostgreSQL syntax)
            cur.execute("""
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_candles_time'
            """)
            if not cur.fetchone():
                cur.execute("CREATE INDEX idx_candles_time ON candles(symbol, interval, start)")
            
            cur.execute("""
            SELECT 1 FROM pg_indexes WHERE indexname = 'idx_candles_symbol'
            """)
            if not cur.fetchone():
                cur.execute("CREATE INDEX idx_candles_symbol ON candles(symbol)")
        
        conn.commit()
        print("\033[92m✓ Database optimization complete.\033[0m")

# Transaction handling for better data integrity
def insert_candles_batch(candles_data):
    """Insert multiple candle records in a single transaction."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        try:
            conn.execute("BEGIN TRANSACTION")
            for record in candles_data:
                if DB_SYSTEM == 'sqlite':
                    cur.execute("""
                    INSERT OR REPLACE INTO candles 
                    (symbol, interval, start, end, open, high, low, close, volume, VWAP)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['symbol'],
                        record['interval'],
                        record['start'],
                        record['end'],
                        record.get('open'),
                        record.get('high'),
                        record.get('low'),
                        record.get('close'),
                        record.get('volume'),
                        record.get('VWAP')
                    ))
                elif DB_SYSTEM == 'postgres':
                    cur.execute("""
                    INSERT INTO candles 
                    (symbol, interval, start, end, open, high, low, close, volume, VWAP)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, interval, start) DO UPDATE SET
                    end = EXCLUDED.end,
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    VWAP = EXCLUDED.VWAP
                    """, (
                        record['symbol'],
                        record['interval'],
                        record['start'],
                        record['end'],
                        record.get('open'),
                        record.get('high'),
                        record.get('low'),
                        record.get('close'),
                        record.get('volume'),
                        record.get('VWAP')
                    ))
            conn.execute("COMMIT")
            print(f"\033[92m✓ Inserted {len(candles_data)} records successfully\033[0m")
        except Exception as e:
            conn.execute("ROLLBACK")
            print(f"\033[91m❌ Error in batch insert, transaction rolled back: {e}\033[0m")

def db_to_parquet():
    """Convert database to Parquet format."""
    print(f"\033[94m🔄 Starting database to Parquet conversion...\033[0m")
    with get_db_connection() as conn:
        # Get all candle data from the database
        print(f"\033[94m📊 Querying database for all candle data...\033[0m")
        query = """
        SELECT * FROM candles
        ORDER BY symbol, interval, start
        """
        # Explicitly specify parse_dates when reading from SQL
        df = pd.read_sql_query(query, conn, parse_dates=['start', 'end'])
        print(f"\033[94m✓ Retrieved {len(df)} records from database\033[0m")
        
        # Create a single Parquet file with all data
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        parquet_path = DATA_DIR / 'parquet' / f'{timestamp}_all_candles.parquet'
        print(f"\033[94m📁 Creating directory structure for Parquet file...\033[0m")
        parquet_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set multi-index for better organization
        if not df.empty:
            print(f"\033[94m🔧 Setting multi-index on dataframe...\033[0m")
            # Ensure start is datetime before setting as index
            df['start'] = pd.to_datetime(df['start'])
            df['end'] = pd.to_datetime(df['end'])
            df.set_index(['symbol', 'interval', 'start'], inplace=True)
        else:
            print(f"\033[93m⚠️ No data found in database\033[0m")
            
        print(f"\033[94m💾 Writing data to Parquet file...\033[0m")
        # Write to parquet with datetime preservation
        df.to_parquet(parquet_path, engine='pyarrow')
        print(f"\033[92m✓ Converted all candle data to Parquet format at {parquet_path}\033[0m")
        print(f"\033[92m✓ Total records: {len(df)}\033[0m")

def load_parquet():
    """Load Parquet file into a pandas DataFrame."""
    # Find the most recent parquet file
    parquet_dir = DATA_DIR / 'parquet'
    parquet_files = list(parquet_dir.glob('*_all_candles.parquet'))
    
    if not parquet_files:
        raise FileNotFoundError("No parquet files found in the data directory")
    
    # Sort files by name (which includes timestamp) to get the most recent
    most_recent_file = sorted(parquet_files)[-1]
    print(f"\033[94m📂 Loading most recent parquet file: {most_recent_file.name}\033[0m")
    
    return pd.read_parquet(most_recent_file)

import matplotlib.pyplot as plt

# Function to plot simple line chart for stock data
def parquet_plot_ohlc(df, symbol, interval='OneMinute', n_days=None):
    """
    Create a simple line chart for a specific symbol using matplotlib.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame with MultiIndex (symbol, interval, start)
    symbol : str
        The stock symbol to plot
    interval : str, optional
        The time interval to use (default: 'OneMinute')
    n_days : int, optional
        Number of most recent days to plot (default: None, which plots all available data)
    
    Example:
        # Example usage 
        symbol = input("Enter a symbol: ").upper()
        parquet_plot_ohlc(df, symbol, 'OneMinute')
    """
    try:
        # Filter DataFrame for the specific symbol and interval
        symbol_data = df.xs((symbol, interval), level=('symbol', 'interval'))
        
        # Sort by date to ensure chronological order
        symbol_data = symbol_data.sort_index()
        
        # Ensure index is datetime
        if isinstance(symbol_data.index.max(), str):
            symbol_data.index = pd.to_datetime(symbol_data.index, utc=True)
            
        # Limit to last n_days if specified
        if n_days is not None:
            last_date = symbol_data.index.max()
            start_date = last_date - pd.Timedelta(days=n_days)
            symbol_data = symbol_data[symbol_data.index >= start_date]
        
        # Create figure with single plot
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # Plot only close price
        ax.plot(symbol_data.index, symbol_data['close'], label='Close', color='blue')
        
        # Format the plot
        ax.set_title(f'{symbol} Price Chart ({interval})', fontsize=16)
        ax.set_ylabel('Price ($)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plt.show()
        
        return fig, ax
    except KeyError:
        print(f"Symbol '{symbol}' or interval '{interval}' not found in the DataFrame.")
        return None, None
    except Exception as e:
        print(f"Error creating chart: {e}")
        return None, None

def get_candle_from_db(symbol, interval="OneMinute"):
    """
    Fetch candle data for a given symbol and interval from the database.
    """
    with get_db_connection() as conn:
        if DB_SYSTEM == 'sqlite':
            query = """
            SELECT * FROM candles
            WHERE symbol = ? AND interval = ?
            ORDER BY start
            """
            df = pd.read_sql_query(query, conn, params=(symbol, interval))
        elif DB_SYSTEM == 'postgres':
            query = """
            SELECT * FROM candles
            WHERE symbol = %s AND interval = %s
            ORDER BY start
            """
            df = pd.read_sql_query(query, conn, params=(symbol, interval))
        
        return df


def prepare_parquet_autogluon(update_db=True):
    '''
    Prepare a parquet file for autogluon.
    '''
    from termcolor import colored
    import time
    import pandas as pd
    from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor

    all_symbols = local_symbols.get_all_local_symbols()
    dataframes = []

    for symbol_info in all_symbols:
        symbol = symbol_info['symbol']
        industry_sector = symbol_info['industrySector']
        
        if update_db:
            update_candles_for_symbol(symbol, interval="OneMinute")
        print(colored(f"Processing symbol: {symbol}", "green"))
        
        candles = get_candle_from_db(symbol, interval="OneMinute")
        print(colored(f"Retrieved {len(candles)} candles for {symbol}", "cyan"))
        
        # Convert datetime columns to the desired format
        # First convert to datetime objects if they aren't already
        candles['start'] = pd.to_datetime(candles['start'], errors='coerce', utc=True)
        if 'end' in candles.columns:
            candles['end'] = pd.to_datetime(candles['end'], errors='coerce', utc=True)

        # Convert timezone from UTC to Eastern Time
        candles['start'] = candles['start'].dt.tz_convert('US/Eastern')
        if 'end' in candles.columns:
            candles['end'] = candles['end'].dt.tz_convert('US/Eastern')

        # Format the datetime columns to the desired string format
        # Only after timezone conversion is complete
        candles['start'] = candles['start'].dt.strftime('%Y-%m-%d %H:%M:%S')
        if 'end' in candles.columns:
            candles['end'] = candles['end'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # drop id column
        candles = candles.drop(columns=['id'])

        # Add industry sector from the already retrieved symbol_info
        candles['industrySector'] = industry_sector

        # Sort by start date
        candles = candles.sort_values(by='start')
        
        candles = TimeSeriesDataFrame.from_data_frame(
            candles,
            id_column="symbol",
            timestamp_column="start"
        )
        
        dataframes.append(candles)
        print(colored("-" * 50, "white"))

    # Combine all dataframes at once instead of in the loop
    combined_df = pd.concat(dataframes) if dataframes else pd.DataFrame()

    # Save the combined dataframe to a parquet file
    combined_df.to_parquet(f'{DATA_DIR}/parquet/{time.strftime("%Y%m%d")}_AG_combined.parquet')
    return combined_df

