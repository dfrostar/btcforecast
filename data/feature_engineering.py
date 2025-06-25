import pandas as pd
import numpy as np

def add_technical_indicators(df):
    """
    Adds technical indicators to the Bitcoin price data using native pandas/numpy.
    Windows-compatible version without pandas_ta dependency.
    
    Args:
        df (pandas.DataFrame): DataFrame with OHLCV data
        
    Returns:
        pandas.DataFrame: DataFrame with technical indicators added
    """
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Ensure we have the required columns
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    # --- Moving Averages ---
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # Exponential Moving Averages
    df['EMA_12'] = df['Close'].ewm(span=12).mean()
    df['EMA_26'] = df['Close'].ewm(span=26).mean()
    
    # --- MACD ---
    ema_12 = df['Close'].ewm(span=12).mean()
    ema_26 = df['Close'].ewm(span=26).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']

    # --- RSI ---
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # --- Bollinger Bands ---
    bb_period = 20
    bb_std = 2
    df['BB_Middle'] = df['Close'].rolling(window=bb_period).mean()
    bb_std_dev = df['Close'].rolling(window=bb_period).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std_dev * bb_std)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std_dev * bb_std)
    df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
    df['BB_Position'] = (df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])

    # --- Stochastic Oscillator ---
    stoch_period = 14
    df['Stoch_K'] = ((df['Close'] - df['Low'].rolling(window=stoch_period).min()) / 
                     (df['High'].rolling(window=stoch_period).max() - df['Low'].rolling(window=stoch_period).min())) * 100
    df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()

    # --- Volume indicators ---
    df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
    
    # --- Price-based features ---
    df['Price_Change'] = df['Close'].pct_change()
    df['Price_Change_5'] = df['Close'].pct_change(periods=5)
    df['Price_Change_20'] = df['Close'].pct_change(periods=20)
    
    # --- Volatility ---
    df['Volatility'] = df['Price_Change'].rolling(window=20).std()
    
    # --- High-Low spread ---
    df['HL_Spread'] = (df['High'] - df['Low']) / df['Close']
    
    # --- Price position within day's range ---
    df['Price_Position'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'])
    
    # --- Momentum indicators ---
    # Rate of Change
    df['ROC'] = ((df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10)) * 100
    
    # Momentum
    df['MOM'] = df['Close'] - df['Close'].shift(10)
    
    # --- Additional features ---
    df['Day_of_Week'] = df.index.dayofweek
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    
    # --- Fill NaN values ---
    # Fill NaN values with appropriate defaults
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    # Remove any infinite values
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.fillna(method='ffill').fillna(method='bfill')
    
    return df 