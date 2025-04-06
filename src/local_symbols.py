# src/local_symbols.py

import sys
import os

# Add the parent directory to sys.path to make the api module importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.qt_api import qt_api as qt

RATE_LIMIT = False

def save_local_symbol(symbol):
    """
    inputs:
        symbol (str): The symbol to save

    returns:
        dict: A dictionary containing the symbol details with the following structure:
            {
                "symbol": str,                # The stock symbol
                "symbolId": int,              # The unique identifier for the symbol
                "prevDayClosePrice": float,   # The previous day's closing price
                "highPrice52": float,         # The 52-week high price
                "lowPrice52": float,          # The 52-week low price
                "averageVol3Months": int,     # The average volume over the last 3 months
                "averageVol20Days": int,      # The average volume over the last 20 days
                "outstandingShares": int,      # The number of outstanding shares
                "eps": float,                 # Earnings per share
                "pe": float or None,          # Price-to-earnings ratio
                "dividend": float,            # Dividend amount
                "yield": float,               # Dividend yield
                "exDate": str,                # Ex-dividend date
                "marketCap": int,             # Market capitalization
                "tradeUnit": int,             # Trade unit size
                "optionType": str or None,    # Type of option
                "optionDurationType": str or None, # Duration type of the option
                "optionRoot": str,            # Option root
                "optionContractDeliverables": dict, # Deliverables for the option contract
                "optionExerciseType": str or None, # Type of option exercise
                "listingExchange": str,        # The exchange where the symbol is listed
                "description": str,            # Description of the symbol
                "securityType": str,           # Type of security (e.g., Stock)
                "optionExpiryDate": str or None, # Expiry date of the option
                "dividendDate": str,           # Date of the dividend payment
                "optionStrikePrice": float or None, # Strike price of the option
                "isTradable": bool,            # Whether the symbol is tradable
                "isQuotable": bool,            # Whether the symbol is quotable
                "hasOptions": bool,            # Whether the symbol has options
                "currency": str,               # Currency of the symbol
                "minTicks": list,              # Minimum tick sizes
                "industrySector": str,         # Industry sector
                "industryGroup": str,          # Industry group
                "industrySubgroup": str         # Industry subgroup
            }
    """
    symbol_search = qt.search_symbols(symbol)
    symbol_details = qt.get_symbol_details(symbol_search['symbols'][0]['symbolId'])
    symbol_data = symbol_details['symbols'][0]
    
    # Save the symbol details to a local database
    import sqlite3
    import json
    import os
    from pathlib import Path

    # Ensure the database directory exists
    db_dir = Path('../data')
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to the local database with absolute path
    db_path = db_dir / 'symbols.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS symbols (
        symbol TEXT PRIMARY KEY,
        symbol_id INTEGER,
        data TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Convert the symbol data to JSON for storage
    symbol_json = json.dumps(symbol_data)
    
    # Insert or replace the symbol data
    cursor.execute('''
    INSERT OR REPLACE INTO symbols (symbol, symbol_id, data, last_updated)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (symbol, symbol_data['symbolId'], symbol_json))
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    
    print(f"Symbol {symbol} saved to local database")
    return symbol_data

def get_local_symbol(symbol, force_update=False):
    """
    Retrieves symbol information from the local database.
    If the symbol is not found, it calls save_local_symbol to fetch and store it.
    
    Args:
        symbol (str): The symbol to retrieve
        force_update (bool): If True, forces an update from the API regardless of database status
        
    Returns:
        dict: The symbol information
    """
    import sqlite3
    import json
    import os
    from pathlib import Path
    
    # If force_update is True, skip database check and fetch fresh data
    if force_update:
        return save_local_symbol(symbol)
    
    # Ensure the database directory exists
    db_dir = Path('../data')
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to the local database with absolute path
    db_path = db_dir / 'symbols.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist (to prevent "no such table" error)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS symbols (
        symbol TEXT PRIMARY KEY,
        symbol_id INTEGER,
        data TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if the symbol exists in the database
    cursor.execute('SELECT data FROM symbols WHERE symbol = ?', (symbol,))
    result = cursor.fetchone()
    
    if result:
        # Symbol found in database, return the data
        symbol_data = json.loads(result[0])
        conn.close()
        return symbol_data
    else:
        # Symbol not found, fetch and save it
        conn.close()
        return save_local_symbol(symbol)

def get_all_local_symbols():
    """
    Retrieves all symbols from the local database.
    
    Returns:
        list: A list of dictionaries containing symbol information
    """
    import sqlite3
    import json
    from pathlib import Path
    
    # Ensure the database directory exists
    db_dir = Path('../data')
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Connect to the local database with absolute path
    db_path = db_dir / 'symbols.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if it doesn't exist (to prevent "no such table" error)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS symbols (
        symbol TEXT PRIMARY KEY,
        symbol_id INTEGER,
        data TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Retrieve all symbols from the database
    cursor.execute('SELECT data FROM symbols')
    results = cursor.fetchall()
    
    # Convert the results to a list of dictionaries
    symbols = [json.loads(row[0]) for row in results]
    
    conn.close()
    return symbols

def import_symbols_from_csv(csv_file_path):
    """
    Imports symbols from a CSV file into the local database.
    
    Args:
        csv_file_path (str): Path to the CSV file containing symbols.
            The CSV should have a header row and at least two columns:
            'Company' and 'Symbol'.
            
    Returns:
        int: Number of symbols successfully imported
        
    Example:
        >>> import_symbols_from_csv('../lists/DOWJONES.csv')
        30
    """
    import csv
    import time
    from pathlib import Path
    
    # Read the CSV file
    imported_count = 0
    
    # Try different encodings to handle potential encoding issues
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(csv_file_path, 'r', encoding=encoding) as file:
                # Detect delimiter (assuming it's either comma or semicolon)
                first_line = file.readline().strip()
                delimiter = ';' if ';' in first_line else ','
                file.seek(0)  # Reset file pointer to beginning
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                for row in reader:
                    symbol = row['Symbol'].strip()
                    
                    try:
                        # Call save_local_symbol for each symbol
                        save_local_symbol(symbol)
                        imported_count += 1
                        if RATE_LIMIT:
                            # Add delay to respect rate limit (max 20 requests per second)
                            time.sleep(0.05)  # 50ms delay = max 20 requests per second
                    except Exception as e:
                        print(f"Error importing {symbol}: {e}")
            
            # If we got here without errors, we found the right encoding
            break
        except UnicodeDecodeError:
            # Try the next encoding
            continue
        except Exception as e:
            print(f"Error reading file with encoding {encoding}: {e}")
            continue
    else:
        # This runs if the for loop completes without a break
        print(f"Could not read file {csv_file_path} with any of the attempted encodings")
    
    return imported_count


