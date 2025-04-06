# qt_api/qt_api.py
'''
# Questrade API Time Parameters Reference
# 
# startTime (DateTime):
# - Start of time range in ISO format with timezone offset
# - By default: start of today, 12:00am
#
# endTime (DateTime):
# - End of time range in ISO format with timezone offset
# - By default: end of today, 11:59pm
#
# Example usage:
#days_back = 7
#start_time = (datetime.datetime.now() - datetime.timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone().isoformat()
#end_time = datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).astimezone().isoformat()
#
# Format required:
# "start": "2014-01-02T00:00:00.000000-05:00",
# "end": "2014-01-03T00:00:00.000000-05:00"
'''
import requests
import json
from datetime import datetime
from pathlib import Path

# Define the token path as a constant
TOKEN_PATH = Path(__file__).parent / "secrets" / "questrade_token.json"

########################################################
#                                                      #
#                    ACCOUNT CALLS                     #
#                                                      #
########################################################
def refresh_questrade_token(refresh_token: str=None):
    """
    inputs:
        refresh_token (str): The refresh token to use to refresh the token

    returns:
        dict: A dictionary containing the refreshed token information with the following structure:
            {
                "access_token": str,  # The new access token
                "token_type": str,    # The token type (e.g. "Bearer")
                "expires_in": int,    # Token expiry time in seconds
                "refresh_token": str, # The new refresh token
                "api_server": str     # The Questrade API server URL
            }
    """

    # Create secrets directory if it doesn't exist
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if refresh_token is None:
        # Try to read existing token if available
        if TOKEN_PATH.exists():
            with open(TOKEN_PATH, "r") as f:
                token_data = json.load(f)
                refresh_token = token_data["refresh_token"]
        else:
            refresh_token = input("Enter the refresh token: ")

    # Make request to refresh the token
    url = f"https://login.questrade.com/oauth2/token?grant_type=refresh_token&refresh_token={refresh_token}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to refresh token: {response.text}")

    # Get the new token data
    new_token_data = response.json()
    
    # Add timestamp when token was refreshed
    new_token_data["time_refreshed"] = datetime.now().isoformat()
    
    # Calculate and add expires_at timestamp
    new_token_data["expires_at"] = datetime.now().timestamp() + new_token_data["expires_in"]
    
    # Save the refreshed token data
    with open(TOKEN_PATH, "w") as f:
        json.dump(new_token_data, f, indent=4)
        
    return new_token_data

def get_questrade_token(refresh_token: str=None):
    """
    Retrieves the Questrade API token from the token file.
    
    inputs:
        refresh_token (str): The refresh token to use to refresh the token

    Returns:
        dict: A dictionary containing the token information
    """
    # If token file doesn't exist, refresh token to create it
    if not TOKEN_PATH.exists():
        return refresh_questrade_token(refresh_token)
        
    with open(TOKEN_PATH, "r") as f:
        token_data = json.load(f)

    # Check if expires_at exists and token is expired
    if "expires_at" not in token_data or token_data["expires_at"] < datetime.now().timestamp():
        # Refresh the token if it is expired or missing expiry
        token_data = refresh_questrade_token(token_data["refresh_token"])

    return token_data

def get_questrade_time():
    """
    Retrieves the current server time from the Questrade API.
    
    Returns:
        str: Current server time in ISO format (Eastern time zone)
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Make request to get the server time
    url = f"{token_data['api_server']}v1/time"
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get server time after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get server time: {response.text}")
        
    return response.json()["time"]

def get_questrade_accounts():
    """
    Retrieves the Questrade accounts from the Questrade API.
    
    Returns:
        dict: A dictionary containing the accounts information including:
            - type: Type of account (e.g. "Cash", "Margin") 
            - number: Eight-digit account number
            - status: Account status (e.g. "Active")
            - isPrimary: Whether this is primary account
            - isBilling: Whether this account is billed for fees
            - clientAccountType: Type of client holding the account
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Make request to get the accounts
    url = f"{token_data['api_server']}v1/accounts"
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get accounts after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get accounts: {response.text}")
        
    return response.json()

def get_questrade_positions(account_id):
    """
    Retrieves positions for a specified Questrade account.
    
    Args:
        account_id (str): The account number to get positions for
        
    Returns:
        dict: A dictionary containing the positions information including:
            - symbol: Position symbol
            - symbolId: Internal symbol identifier
            - openQuantity: Position quantity remaining open
            - closedQuantity: Portion closed today
            - currentMarketValue: Market value of position
            - currentPrice: Current price of symbol
            - averageEntryPrice: Average entry price
            - closedPnL: Realized profit/loss
            - openPnL: Unrealized profit/loss
            - totalCost: Total cost of position
            - isRealTime: If real-time quote used
            - isUnderReorg: If symbol undergoing reorganization
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Make request to get the positions
    url = f"{token_data['api_server']}v1/accounts/{account_id}/positions"
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get positions after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get positions: {response.text}")
        
    return response.json()

def get_questrade_balances(account_id):
    """
    Retrieves balances for a specified Questrade account.
    
    Args:
        account_id (str): The account number to get balances for
        
    Returns:
        dict: A dictionary containing the balances information including:
            - perCurrencyBalances: List of balances per currency
            - combinedBalances: List of combined balances
            - sodPerCurrencyBalances: List of start-of-day balances per currency
            - sodCombinedBalances: List of start-of-day combined balances
            
            Each balance contains:
            - currency: Currency code (e.g. "CAD" or "USD")
            - cash: Cash balance amount
            - marketValue: Market value of securities
            - totalEquity: Total equity (cash + market value)
            - buyingPower: Available buying power
            - maintenanceExcess: Maintenance excess
            - isRealTime: If real-time data was used
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Make request to get the balances
    url = f"{token_data['api_server']}v1/accounts/{account_id}/balances"
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get balances after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get balances: {response.text}")
        
    return response.json()

def get_questrade_executions(account_id, start_time=None, end_time=None):
    """
    Retrieves executions for a specified Questrade account.
    
    Args:
        account_id (str): The account number to get executions for
        start_time (str, optional): Start of time range in ISO format. Default is start of today.
        end_time (str, optional): End of time range in ISO format. Default is end of today.
        
    Returns:
        dict: A dictionary containing the executions information including:
            - executions: List of execution records, each containing:
                - symbol: Execution symbol
                - symbolId: Internal symbol identifier
                - quantity: Execution quantity
                - side: Client side of the order (Buy/Sell)
                - price: Execution price
                - id: Internal identifier of the execution
                - orderId: Internal identifier of the order
                - orderChainId: Internal identifier of the order chain
                - exchangeExecId: Identifier of the execution at the market
                - timestamp: Execution timestamp
                - notes: Manual notes entered by Trade Desk staff
                - venue: Trading venue where execution originated
                - totalCost: Execution cost (price x quantity)
                - orderPlacementCommission: Commission for orders placed with Trade Desk
                - commission: Questrade commission
                - executionFee: Liquidity fee charged by execution venue
                - secFee: SEC fee charged on sales of US securities
                - canadianExecutionFee: Additional execution fee charged by TSX
                - parentId: Internal identifier of the parent order
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL with optional parameters
    url = f"{token_data['api_server']}v1/accounts/{account_id}/executions"
    params = {}
    if start_time:
        params['startTime'] = start_time
    if end_time:
        params['endTime'] = end_time
    
    # Make request to get the executions
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get executions after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get executions: {response.text}")
        
    return response.json()

def get_account_orders(account_id, start_time=None, end_time=None, state_filter=None, order_id=None):
    """
    Retrieves orders for a specified account.
    
    Args:
        account_id (str): Account number.
        start_time (str, optional): Start of time range in ISO format. Default is start of today.
        end_time (str, optional): End of time range in ISO format. Default is end of today.
        state_filter (str, optional): Filter by order state - 'All', 'Open', or 'Closed'.
        order_id (int, optional): Retrieve single order details.
    
    Returns:
        dict: JSON response containing order information with the following structure:
            - orders: List of order records, each containing:
                - id: Internal order identifier
                - symbol: Symbol that follows Questrade symbology
                - symbolId: Internal symbol identifier
                - totalQuantity: Total quantity of the order
                - openQuantity: Unfilled portion of the order quantity
                - filledQuantity: Filled portion of the order quantity
                - canceledQuantity: Unfilled portion after cancellation
                - side: Client view of the order side (e.g., "Buy-To-Open")
                - orderType: Order price type (e.g., "Market")
                - limitPrice: Limit price
                - stopPrice: Stop price
                - isAllOrNone: Specifies all-or-none special instruction
                - isAnonymous: Specifies Anonymous special instruction
                - icebergQuantity: Specifies Iceberg special instruction
                - minQuantity: Specifies Minimum special instruction
                - avgExecPrice: Average price of all executions for this order
                - lastExecPrice: Price of the last execution for this order
                - source: Source of the order
                - timeInForce: Time in force for the order
                - gtdDate: Good-Till-Date marker and date parameter
                - state: Order state
                - clientReasonStr: Human readable order rejection reason
                - chainId: Internal identifier of a chain to which the order belongs
                - creationTime: Order creation time
                - updateTime: Time of the last update
                - notes: Notes that may have been manually added by Questrade staff
                - primaryRoute: Primary route
                - secondaryRoute: Secondary route
                - orderRoute: Order route name
                - venueHoldingOrder: Venue where non-marketable portion was booked
                - commissionCharged: Total commission amount charged
                - exchangeOrderId: Identifier assigned by exchange
                - isSignificantShareholder: Whether user is a significant shareholder
                - isInsider: Whether user is an insider
                - isLimitOffsetInDollar: Whether limit offset is in dollars (vs. percent)
                - userId: Internal identifier of user that placed the order
                - placementCommission: Commission for placing the order via Trade Desk
                - legs: List of OrderLeg elements
                - strategyType: Multi-leg strategy to which the order belongs
                - triggerStopPrice: Stop price at which order was triggered
                - orderGroupId: Internal identifier of the order group
                - orderClass: Bracket Order class (Primary, Profit or Loss)
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL with optional parameters
    url = f"{token_data['api_server']}v1/accounts/{account_id}/orders"
    if order_id:
        url = f"{url}/{order_id}"
    
    params = {}
    if start_time:
        params['startTime'] = start_time
    if end_time:
        params['endTime'] = end_time
    if state_filter:
        params['stateFilter'] = state_filter
    
    # Make request to get the orders
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get orders after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get orders: {response.text}")
        
    return response.json()

def get_account_activities(account_id: str, start_time: str=None, end_time: str=None):
    """
    Retrieves account activities, including cash transactions, dividends, trades, etc.
    
    inputs:
        account_id (str): The account number
        start_time (str): The start time of the interval to retrieve activities in ISO format with timezone offset
        end_time (str): The end time of the interval to retrieve activities in ISO format with timezone offset
        
    returns:
        dict: A dictionary containing the account activities with the following structure:
            {
                "activities": [
                    {
                        "tradeDate": str,          # Trade date in ISO format
                        "transactionDate": str,    # Transaction date in ISO format
                        "settlementDate": str,     # Settlement date in ISO format
                        "action": str,             # Activity action
                        "symbol": str,             # Symbol name
                        "symbolId": int,           # Symbol ID
                        "description": str,        # Description
                        "currency": str,           # Currency
                        "quantity": float,         # The quantity
                        "price": float,            # The price
                        "grossAmount": float,      # Gross amount
                        "commission": float,       # The commission
                        "netAmount": float,        # Net Amount
                        "type": str                # Activity Type
                    },
                    ...
                ]
            }
            
    Note: Maximum 31 days of data can be requested at a time.
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL with optional parameters
    url = f"{token_data['api_server']}v1/accounts/{account_id}/activities"
    
    params = {}
    if start_time:
        params['startTime'] = start_time
    if end_time:
        params['endTime'] = end_time
    
    # Make request to get the account activities
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get account activities after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get account activities: {response.text}")
        
    return response.json()

########################################################
#                                                      #
#                    MARKET CALLS                     #
#                                                      #
########################################################

def get_markets():
    """
    Retrieves information about supported markets.
    
    Returns:
        dict: A dictionary containing information about supported markets with the following structure:
            {
                "markets": [
                    {
                        "name": str,                   # Market name
                        "tradingVenues": [str, ...],   # List of trading venue codes
                        "defaultTradingVenue": str,    # Default trading venue code
                        "primaryOrderRoutes": [str, ...],    # List of primary order route codes
                        "secondaryOrderRoutes": [str, ...],  # List of secondary order route codes
                        "level1Feeds": [str, ...],     # List of level 1 market data feed codes
                        "level2Feeds": [str, ...],     # List of level 2 market data feed codes
                        "extendedStartTime": str,      # Pre-market opening time for current trading date
                        "startTime": str,              # Regular market opening time for current trading date
                        "endTime": str,                # Regular market closing time for current trading date
                        "extendedEndTime": str,        # Extended market closing time for current trading date
                        "currency": str,               # Currency code (ISO format)
                        "snapQuotesLimit": int         # Number of snap quotes that the user can retrieve from a market
                    },
                    ...
                ]
            }
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL
    url = f"{token_data['api_server']}v1/markets"
    
    # Make request to get the markets
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get markets after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get markets: {response.text}")
        
    return response.json()

def search_symbols(prefix: str, offset: int = 0):
    """
    Retrieves symbol(s) using search criteria.
    
    Args:
        prefix (str): Prefix of a symbol or any word in the description.
        offset (int, optional): Offset in number of records from the beginning of a result set. Defaults to 0.
    
    Returns:
        dict: A dictionary containing information about symbols with the following structure:
            {
                "symbols": [
                    {
                        "symbol": str,             # Symbol name
                        "symbolId": int,           # Internal unique symbol identifier
                        "description": str,        # Symbol description
                        "securityType": str,       # Symbol security type
                        "listingExchange": str,    # Primary listing exchange of the symbol
                        "isQuotable": bool,        # Whether a symbol has live market data
                        "isTradable": bool,        # Whether a symbol is tradable on the platform
                        "currency": str            # Symbol currency (ISO format)
                    },
                    ...
                ]
            }
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL with query parameters
    url = f"{token_data['api_server']}v1/symbols/search?prefix={prefix}&offset={offset}"
    
    # Make request to search symbols
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to search symbols after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to search symbols: {response.text}")
        
    return response.json()

def get_symbol_details(symbol_id=None, symbol_ids=None, symbol_names=None):
    """
    Retrieves detailed information about one or more symbols.
    
    Args:
        symbol_id (int, optional): Internal symbol identifier for a single symbol.
        symbol_ids (list, optional): List of internal symbol identifiers.
        symbol_names (list, optional): List of symbol names.
    
    Returns:
        dict: A dictionary containing detailed information about the requested symbols with the following structure:
            {
                "symbols": [
                    {
                        "symbol": str,                 # Symbol name (e.g., "AAPL")
                        "symbolId": int,               # Internal symbol identifier
                        "prevDayClosePrice": float,    # Previous day's closing price
                        "highPrice52": float,          # 52-week high price
                        "lowPrice52": float,           # 52-week low price
                        "averageVol3Months": int,      # 3-month average volume
                        "averageVol20Days": int,       # 20-day average volume
                        "outstandingShares": int,      # Total outstanding shares
                        "eps": float,                  # Earnings per share
                        "pe": float,                   # Price to earnings ratio
                        "dividend": float,             # Dividend amount per share
                        "yield": float,                # Dividend yield
                        "exDate": str,                 # Dividend ex-date
                        "marketCap": float,            # Market capitalization
                        "optionType": str,             # Option type (if applicable)
                        "listingExchange": str,        # Primary listing exchange
                        "description": str,            # Symbol description
                        "securityType": str,           # Security type
                        "isQuotable": bool,            # Whether symbol is actively listed
                        "hasOptions": bool,            # Whether symbol has options
                        "currency": str,               # Currency code (ISO format)
                        # ... and other properties
                    },
                    ...
                ]
            }
    
    Note:
        Only one of symbol_id, symbol_ids, or symbol_names should be provided.
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Determine which parameter to use and build the URL
    if symbol_id is not None:
        url = f"{token_data['api_server']}v1/symbols/{symbol_id}"
    elif symbol_ids is not None:
        ids_str = ','.join(str(id) for id in symbol_ids)
        url = f"{token_data['api_server']}v1/symbols?ids={ids_str}"
    elif symbol_names is not None:
        names_str = ','.join(symbol_names)
        url = f"{token_data['api_server']}v1/symbols?names={names_str}"
    else:
        raise ValueError("At least one of symbol_id, symbol_ids, or symbol_names must be provided")
    
    # Make request to get symbol details
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get symbol details after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get symbol details: {response.text}")
    
    return response.json()

def get_candles(symbol_id, start_time, end_time, interval="OneMinute"):
    """
    Retrieves historical market data in the form of OHLC candlesticks for a specified symbol.
    
    Args:
        symbol_id (int): Internal symbol identifier.
        start_time (str): Beginning of the candlestick range in ISO format with timezone offset.
        end_time (str): End of the candlestick range in ISO format with timezone offset.
        interval (str): Interval of a single candlestick. 
                        Valid values: OneMinute, TwoMinutes, ThreeMinutes, FourMinutes, 
                        FiveMinutes, TenMinutes, FifteenMinutes, TwentyMinutes, 
                        HalfHour, OneHour, TwoHours, FourHours, OneDay, OneWeek, OneMonth, OneYear
    
    Returns:
        dict: A dictionary containing the candlestick data with the following structure:
            {
                "candles": [
                    {
                        "start": str,     # Candlestick start timestamp (in ISO format)
                        "end": str,       # Candlestick end timestamp (in ISO format)
                        "open": float,    # Opening price
                        "high": float,    # High price
                        "low": float,     # Low price
                        "close": float,   # Closing price
                        "volume": int     # Trading volume
                    },
                    ...
                ]
            }
    
    Note:
        This call is limited to returning 20,000 candlesticks in a single response.

    Time format required:
        "start": "2014-01-02T00:00:00.000000-05:00",
        "end": "2014-01-03T00:00:00.000000-05:00"
    Example usage:
        days_back = 7
        start_time = (datetime.datetime.now() - datetime.timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone().isoformat()
        end_time = datetime.datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).astimezone().isoformat()
        get_candles(symbol_id, start_time, end_time, interval="OneMinute")
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL with required parameters
    url = f"{token_data['api_server']}v1/markets/candles/{symbol_id}"
    
    params = {
        'startTime': start_time,
        'endTime': end_time,
        'interval': interval
    }
    
    # Make request to get the candles
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get candles after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get candles: {response.text}")
    
    return response.json()

def get_market_quote(symbol_id=None, ids=None):
    """
    Retrieves a single Level 1 market data quote for one or more symbols.
    
    inputs:
        symbol_id (int): Internal symbol identifier. Mutually exclusive with 'ids' parameter.
        ids (list): List of symbol ids.
    
    returns:
        dict: A dictionary containing the market quotes with the following structure:
            {
                "quotes": [
                    {
                        "symbol": str,                # Symbol name following Questrade's symbology
                        "symbolId": int,              # Internal symbol identifier
                        "tier": str,                  # Market tier
                        "bidPrice": float,            # Bid price
                        "bidSize": int,               # Bid quantity
                        "askPrice": float,            # Ask price
                        "askSize": int,               # Ask quantity
                        "lastTradePriceTrHrs": float, # Price of the last trade during regular trade hours
                        "lastTradePrice": float,      # Price of the last trade
                        "lastTradeSize": int,         # Quantity of the last trade
                        "lastTradeTick": str,         # Trade direction
                        "lastTradeTime": str,         # Time of the last trade
                        "volume": int,                # Volume
                        "openPrice": float,           # Opening trade price
                        "highPrice": float,           # Daily high price
                        "lowPrice": float,            # Daily low price
                        "delay": int,                 # Whether a quote is delayed (true) or real-time
                        "isHalted": bool              # Whether trading in the symbol is currently halted
                    },
                    ...
                ]
            }
    
    Note:
        User needs to be subscribed to a real-time data package to receive market quotes in real-time,
        otherwise the call is considered a snap quote and limit per market can be quickly reached.
        Without real-time data package, once limit is reached, the response will return delayed data.
        (Please check "delay" parameter in response always)
    """
    # Get the token data
    token_data = get_questrade_token()
    
    # Build the URL with required parameters
    if symbol_id is not None:
        url = f"{token_data['api_server']}v1/markets/quotes/{symbol_id}"
        params = {}
    elif ids is not None:
        url = f"{token_data['api_server']}v1/markets/quotes"
        # Convert list of ids to comma-separated string if needed
        if isinstance(ids, list):
            ids = ','.join(map(str, ids))
        params = {'ids': ids}
    else:
        raise ValueError("Either symbol_id or ids must be provided")
    
    # Make request to get the quotes
    headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        # If unauthorized, try refreshing token once and retry
        if response.status_code == 401:
            token_data = refresh_questrade_token()
            headers = {"Authorization": f"{token_data['token_type']} {token_data['access_token']}"}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get market quotes after token refresh: {response.text}")
        else:
            raise Exception(f"Failed to get market quotes: {response.text}")
    
    return response.json()
