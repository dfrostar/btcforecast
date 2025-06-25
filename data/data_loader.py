import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def load_btc_data(start="2014-01-01", end=None, interval='1d'):
    """
    Downloads historical Bitcoin (BTC-USD) data from Yahoo Finance.

    Args:
        start (str): The start date for the data in 'YYYY-MM-DD' format.
        end (str): The end date for the data in 'YYYY-MM-DD' format. Defaults to today.
        interval (str): The data interval (e.g., '1d' for daily, '1h' for hourly).

    Returns:
        pandas.DataFrame: A DataFrame containing the historical BTC-USD data,
                          indexed by date. Returns an empty DataFrame on error.
    """
    if end is None:
        end = datetime.now().strftime('%Y-%m-%d')
    
    try:
        df = yf.download('BTC-USD', start=start, end=end, interval=interval)
        if df.empty:
            print("Warning: No data found for the specified date range.")
            return pd.DataFrame()
            
        # Ensure the index is a DatetimeIndex
        df.index = pd.to_datetime(df.index)
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
        
        # Select and rename columns for consistency
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        print(f"Successfully downloaded {len(df)} rows of BTC-USD data.")
        return df
    except Exception as e:
        print(f"An error occurred while downloading data: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    # Example usage:
    btc_data = load_btc_data(start="2022-01-01")
    if not btc_data.empty:
        print("\n--- BTC Data Sample ---")
        print(btc_data.head())
        print("\n--- Data Info ---")
        btc_data.info() 