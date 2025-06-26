import pandas as pd
import numpy as np
from model import train_model, forecast_future, save_model_and_scaler, add_sentiment_feature, calculate_directional_accuracy
import ta
from sklearn.metrics import mean_absolute_error
import os
import time

# --- Parameters ---
LOOKBACK = 30
EPOCHS = 20
BATCH_SIZE = 32
TIMEFRAME = 30
INDICATORS = ['RSI', 'MACD', 'Bollinger Bands', 'OBV', 'Ichimoku Cloud']

# --- Data Loading ---
def fetch_btc_data(days=730):
    import requests
    import json
    url = f'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=daily'
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if 'prices' not in data or 'total_volumes' not in data:
            print('[ERROR] Unexpected API response from CoinGecko:')
            print(json.dumps(data, indent=2))
            raise ValueError('Missing "prices" or "total_volumes" in API response.')
        prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
        prices.set_index('date', inplace=True)
        prices['price'] = prices['price'].astype(float)
        # Add volume
        volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
        volumes['date'] = pd.to_datetime(volumes['timestamp'], unit='ms')
        volumes.set_index('date', inplace=True)
        prices['volume'] = volumes['volume']
        return prices
    except Exception as e:
        print(f'[WARNING] Could not fetch data from CoinGecko: {e}')
        # Fallback: try to load local btc_forecast.csv if available
        if os.path.exists('btc_forecast.csv'):
            print('[INFO] Loading fallback data from btc_forecast.csv')
            df = pd.read_csv('btc_forecast.csv')
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            if 'forecast' in df.columns:
                df.rename(columns={'forecast': 'price'}, inplace=True)
            if 'volume' not in df.columns:
                df['volume'] = 0.0
            return df[['price', 'volume']]
        else:
            raise RuntimeError('No BTC data available from API or local file.')

# --- Technical Indicators ---
def add_indicators(df, indicators):
    import warnings
    if 'RSI' in indicators:
        df['RSI'] = ta.momentum.RSIIndicator(df['price']).rsi()
    if 'MACD' in indicators:
        macd = ta.trend.MACD(df['price'])
        df['MACD'] = macd.macd()
        df['MACD_signal'] = macd.macd_signal()
    if 'Bollinger Bands' in indicators:
        bb = ta.volatility.BollingerBands(df['price'])
        df['BB_high'] = bb.bollinger_hband()
        df['BB_low'] = bb.bollinger_lband()
    if 'OBV' in indicators:
        if 'volume' in df.columns:
            df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['price'], df['volume']).on_balance_volume()
        else:
            warnings.warn('Skipping OBV: volume column missing')
    if 'Ichimoku Cloud' in indicators:
        if 'high' in df.columns and 'low' in df.columns:
            ichimoku = ta.trend.IchimokuIndicator(df['high'], df['low'])
            df['Ichimoku_a'] = ichimoku.ichimoku_a()
            df['Ichimoku_b'] = ichimoku.ichimoku_b()
        else:
            warnings.warn('Skipping Ichimoku Cloud: high/low columns missing')
    return df

if __name__ == '__main__':
    print('Loading data...')
    df = fetch_btc_data(days=730)
    df = add_indicators(df, INDICATORS)
    df = add_sentiment_feature(df)  # Placeholder: zeros
    feature_cols = [col for col in df.columns if col not in ['price', 'volume', 'BB_high', 'BB_low', 'MACD_signal', 'Ichimoku_a', 'Ichimoku_b'] and df[col].dtype != 'O']
    if 'sentiment' in df.columns:
        feature_cols.append('sentiment')
    train_df = df.dropna(subset=feature_cols + ['price'])
    # --- Robustness check ---
    if len(train_df) < LOOKBACK + 10:
        print(f'[ERROR] Not enough data for training (need at least {LOOKBACK + 10} rows, got {len(train_df)}).')
        print('Please ensure btc_forecast.csv or API data contains sufficient history.')
        exit(1)
    if len(feature_cols) == 0:
        print('[ERROR] No usable features found in data. Check your data columns.')
        exit(1)
    split_idx = int(len(train_df) * 0.9)
    train_data = train_df.iloc[:split_idx]
    val_data = train_df.iloc[split_idx - LOOKBACK:]
    print('[STATUS] Training model...')
    model, scaler, history = train_model(train_data, feature_cols, lookback=LOOKBACK, epochs=EPOCHS, batch_size=BATCH_SIZE, log_csv_path='training_metrics.csv')
    print('[STATUS] Training finished. Evaluating...')
    X_val, y_val, _ = train_model.prepare_data(val_data, feature_cols, lookback=LOOKBACK)
    y_pred = model.predict(X_val).flatten()
    dummy = np.zeros((len(y_pred), len(feature_cols) + 1))
    dummy[:, -1] = y_pred
    y_pred_inv = scaler.inverse_transform(dummy)[:, -1]
    dummy[:, -1] = y_val
    y_val_inv = scaler.inverse_transform(dummy)[:, -1]
    mae = mean_absolute_error(y_val_inv, y_pred_inv)
    dir_acc = calculate_directional_accuracy(y_val_inv, y_pred_inv)
    print(f'Validation MAE: {mae:.2f}')
    print(f'Directional Accuracy: {dir_acc:.2%}')
    save_model_and_scaler(model, scaler)
    print('Model and scaler saved.')
    # Forecast
    preds = forecast_future(train_df, model, scaler, feature_cols, lookback=LOOKBACK, steps=TIMEFRAME)
    future_dates = pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=TIMEFRAME)
    forecast_df = pd.DataFrame({'date': future_dates, 'forecast': preds})
    forecast_df.to_csv('btc_forecast.csv', index=False)
    print('Forecast saved to btc_forecast.csv')
    # Log results
    pd.DataFrame({'MAE': [mae], 'Epochs': [EPOCHS], 'Lookback': [LOOKBACK], 'Indicators': [','.join(INDICATORS)]}).to_csv('btc_training_log.csv', mode='a', header=not os.path.exists('btc_training_log.csv'), index=False)
    print('Training log updated.') 