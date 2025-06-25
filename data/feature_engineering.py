import pandas as pd
import numpy as np
import pandas_ta as ta

def add_technical_indicators(df):
    """
    Adds technical indicators to the Bitcoin price data.
    
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

    # --- Safely add technical indicators ---
    
    # Moving averages
    sma_20 = ta.sma(df['Close'], length=20)
    sma_50 = ta.sma(df['Close'], length=50)
    ema_12 = ta.ema(df['Close'], length=12)
    ema_26 = ta.ema(df['Close'], length=26)
    
    # Ensure they are Series, not DataFrames
    df['SMA_20'] = sma_20.iloc[:, 0] if isinstance(sma_20, pd.DataFrame) else sma_20
    df['SMA_50'] = sma_50.iloc[:, 0] if isinstance(sma_50, pd.DataFrame) else sma_50
    df['EMA_12'] = ema_12.iloc[:, 0] if isinstance(ema_12, pd.DataFrame) else ema_12
    df['EMA_26'] = ema_26.iloc[:, 0] if isinstance(ema_26, pd.DataFrame) else ema_26
    
    # MACD
    try:
        macd = ta.macd(df['Close'])
        if macd is not None and isinstance(macd, pd.DataFrame) and all(c in macd.columns for c in ['MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']):
            df[['MACD', 'MACD_Signal', 'MACD_Histogram']] = macd[['MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']]
    except Exception as e:
        print(f"Could not calculate MACD: {e}")

    # RSI
    rsi = ta.rsi(df['Close'], length=14)
    df['RSI'] = rsi.iloc[:, 0] if isinstance(rsi, pd.DataFrame) else rsi
    
    # Bollinger Bands
    try:
        bb = ta.bbands(df['Close'])
        if bb is not None and isinstance(bb, pd.DataFrame) and all(c in bb.columns for c in ['BBU_20_2.0', 'BBM_20_2.0', 'BBL_20_2.0']):
            df[['BB_Upper', 'BB_Middle', 'BB_Lower']] = bb[['BBU_20_2.0', 'BBM_20_2.0', 'BBL_20_2.0']]
            df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']).fillna(0)
            df['BB_Position'] = ((df['Close'] - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower'])).fillna(0.5)
    except Exception as e:
        print(f"Could not calculate Bollinger Bands: {e}")

    # Stochastic
    try:
        stoch = ta.stoch(df['High'], df['Low'], df['Close'])
        if stoch is not None and isinstance(stoch, pd.DataFrame) and all(c in stoch.columns for c in ['STOCHk_14_3_3', 'STOCHd_14_3_3']):
            df[['Stoch_K', 'Stoch_D']] = stoch[['STOCHk_14_3_3', 'STOCHd_14_3_3']]
    except Exception as e:
        print(f"Could not calculate Stochastic Oscillator: {e}")

    # Volume indicators
    try:
        volume_sma_raw = ta.sma(df['Volume'], length=20)
        # Ensure volume_sma is a Series, not a DataFrame or None
        if volume_sma_raw is None:
            # If SMA calculation fails, use a simple rolling mean as fallback
            volume_sma = df['Volume'].rolling(window=20).mean()
        elif isinstance(volume_sma_raw, pd.DataFrame):
            volume_sma = volume_sma_raw.iloc[:, 0]
        else:
            volume_sma = volume_sma_raw
        
        df['Volume_SMA'] = volume_sma
        df['Volume_Ratio'] = (df['Volume'] / volume_sma).fillna(1)
    except Exception as e:
        print(f"Could not calculate Volume SMA: {e}")
        # Fallback: use simple rolling mean
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = (df['Volume'] / df['Volume_SMA']).fillna(1)
    
    # Price-based features
    df['Price_Change'] = df['Close'].pct_change()
    df['Price_Change_5'] = df['Close'].pct_change(periods=5)
    df['Price_Change_20'] = df['Close'].pct_change(periods=20)
    
    # Volatility
    df['Volatility'] = df['Price_Change'].rolling(window=20).std()
    
    # High-Low spread
    df['HL_Spread'] = (df['High'] - df['Low']) / df['Close']
    
    # Price position within day's range - fill NaNs if High == Low
    df['Price_Position'] = ((df['Close'] - df['Low']) / (df['High'] - df['Low'])).fillna(0.5)
    
    # Momentum indicators
    roc = ta.roc(df['Close'], length=10)
    mom = ta.mom(df['Close'], length=10)
    df['ROC'] = roc.iloc[:, 0] if isinstance(roc, pd.DataFrame) else roc
    df['MOM'] = mom.iloc[:, 0] if isinstance(mom, pd.DataFrame) else mom
    
    # Additional features
    df['Day_of_Week'] = df.index.dayofweek
    df['Month'] = df.index.month
    df['Quarter'] = df.index.quarter
    
    # Remove any infinite values, but keep NaNs for the model to handle
    df = df.replace([np.inf, -np.inf], np.nan)
    
    return df 