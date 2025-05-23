import pandas as pd
import numpy as np
from model import train_model, forecast_future, save_model_and_scaler, add_sentiment_feature
import ta
from sklearn.metrics import mean_absolute_error
import os

# --- Parameters ---
LOOKBACK = 30
EPOCHS = 20
BATCH_SIZE = 32
TIMEFRAME = 30
INDICATORS = ['RSI', 'MACD', 'Bollinger Bands', 'OBV', 'Ichimoku Cloud']

# --- Data Loading ---
def fetch_btc_data(days=730):
    import requests
    url = f'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=daily'
    r = requests.get(url)
    data = r.json()
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

# --- Technical Indicators ---
def add_indicators(df, indicators):
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
        df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['price'], df['volume']).on_balance_volume()
    if 'Ichimoku Cloud' in indicators:
        ichimoku = ta.trend.IchimokuIndicator(df['price'])
        df['Ichimoku_a'] = ichimoku.ichimoku_a()
        df['Ichimoku_b'] = ichimoku.ichimoku_b()
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
    split_idx = int(len(train_df) * 0.9)
    train_data = train_df.iloc[:split_idx]
    val_data = train_df.iloc[split_idx - LOOKBACK:]
    print('Training model...')
    model, scaler, history = train_model(train_data, feature_cols, lookback=LOOKBACK, epochs=EPOCHS, batch_size=BATCH_SIZE)
    X_val, y_val, _ = train_model.prepare_data(val_data, feature_cols, lookback=LOOKBACK)
    y_pred = model.predict(X_val).flatten()
    dummy = np.zeros((len(y_pred), len(feature_cols) + 1))
    dummy[:, -1] = y_pred
    y_pred_inv = scaler.inverse_transform(dummy)[:, -1]
    dummy[:, -1] = y_val
    y_val_inv = scaler.inverse_transform(dummy)[:, -1]
    mae = mean_absolute_error(y_val_inv, y_pred_inv)
    print(f'Validation MAE: {mae:.2f}')
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