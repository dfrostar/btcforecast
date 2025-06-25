import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import psutil
import logging
import time
import warnings
warnings.filterwarnings('ignore')

# Try to import TensorFlow, but provide fallback if not available
try:
    import tensorflow as tf
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input, LSTM, Bidirectional, Dense, Dropout, Layer
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.models import load_model
    from tqdm.keras import TqdmCallback
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("Warning: TensorFlow not available. Using fallback model.")

# --- Data Preparation ---
def prepare_data(df, feature_cols, target_col='price', lookback=30, forecast_horizon=1):
    '''
    Prepare data for time series forecasting with lookback window.
    Returns X, y, scaler
    '''
    scaler = MinMaxScaler()
    data = df[feature_cols + [target_col]].dropna().values
    data_scaled = scaler.fit_transform(data)
    X, y = [], []
    for i in range(lookback, len(data_scaled) - forecast_horizon + 1):
        X.append(data_scaled[i - lookback:i, :-1])
        y.append(data_scaled[i + forecast_horizon - 1, -1])
    X, y = np.array(X), np.array(y)
    return X, y, scaler

# --- Attention Layer ---
if TENSORFLOW_AVAILABLE:
    class AttentionBlock(Layer):
        def __init__(self, **kwargs):
            super(AttentionBlock, self).__init__(**kwargs)
        def build(self, input_shape):
            self.W = self.add_weight(name='att_weight', shape=(input_shape[-1], 1), initializer='normal')
            self.b = self.add_weight(name='att_bias', shape=(input_shape[1], 1), initializer='zeros')
            super(AttentionBlock, self).build(input_shape)
        def call(self, x):
            e = tf.keras.backend.tanh(tf.keras.backend.dot(x, self.W) + self.b)
            a = tf.keras.backend.softmax(e, axis=1)
            output = x * a
            return tf.keras.backend.sum(output, axis=1)

    # --- Model Definition ---
    def build_bilstm_attention(input_shape):
        inp = Input(shape=input_shape)
        x = Bidirectional(LSTM(64, return_sequences=True))(inp)
        x = Dropout(0.2)(x)
        attn = AttentionBlock()(x)
        out = Dense(1, activation='linear')(attn)
        model = Model(inputs=inp, outputs=out)
        model.compile(optimizer=Adam(learning_rate=0.001), loss='mse', metrics=['mae'])
        return model

    # --- Training Function ---
    def train_model(df, feature_cols, lookback=30, forecast_horizon=1, epochs=20, batch_size=32, log_csv_path='training_metrics.csv'):
        logging.basicConfig(filename='training.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
        logging.info('Training started.')
        process = psutil.Process(os.getpid())
        cpu_start = psutil.cpu_percent(interval=None)
        mem_start = process.memory_info().rss / 1024 ** 2
        start_time = time.time()
        X, y, scaler = prepare_data(df, feature_cols, lookback=lookback, forecast_horizon=forecast_horizon)
        model = build_bilstm_attention(X.shape[1:])
        
        class CSVLoggerCallback(tf.keras.callbacks.Callback):
            def __init__(self, csv_path):
                super().__init__()
                self.csv_path = csv_path
                self.epoch_logs = []
            def on_epoch_end(self, epoch, logs=None):
                logs = logs or {}
                row = {'epoch': epoch}
                row.update(logs)
                self.epoch_logs.append(row)
                pd.DataFrame([row]).to_csv(self.csv_path, mode='a', header=not os.path.exists(self.csv_path), index=False)
        
        try:
            print("[STATUS] Training in progress...")
            history = model.fit(
                X, y,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=0.1,
                verbose=0,
                callbacks=[TqdmCallback(verbose=1), CSVLoggerCallback(log_csv_path)]
            )
            print("[STATUS] Training complete.")
            logging.info('Training completed successfully.')
        except Exception as e:
            print(f"[STATUS] Error occurred: {e}")
            logging.error(f"Training failed: {e}")
            raise
        
        cpu_end = psutil.cpu_percent(interval=None)
        mem_end = process.memory_info().rss / 1024 ** 2
        end_time = time.time()
        duration = end_time - start_time
        logging.info(f"Training duration: {duration:.2f} seconds. CPU: {cpu_start}->{cpu_end}%, RAM: {mem_start}->{mem_end} MB")
        summary = pd.DataFrame([{
            'duration_sec': duration,
            'cpu_start_percent': cpu_start,
            'cpu_end_percent': cpu_end,
            'mem_start_mb': mem_start,
            'mem_end_mb': mem_end
        }])
        summary.to_csv('training_resource_log.csv', mode='a', header=not os.path.exists('training_resource_log.csv'), index=False)
        return model, scaler, history

    # --- Forecasting Function ---
    def forecast_future(df, model, scaler, feature_cols, lookback=30, forecast_horizon=1, steps=7):
        '''
        Forecast future prices for a given number of steps.
        '''
        data = df[feature_cols].values
        data_scaled = scaler.transform(np.hstack([data, np.zeros((data.shape[0], 1))]))[:, :-1]
        last_seq = data_scaled[-lookback:]
        preds = []
        for _ in range(steps):
            inp = last_seq[np.newaxis, :, :]
            pred_scaled = model.predict(inp)[0][0]
            # Inverse transform
            dummy = np.zeros((1, len(feature_cols) + 1))
            dummy[0, :-1] = last_seq[-1]
            dummy[0, -1] = pred_scaled
            pred = scaler.inverse_transform(dummy)[0, -1]
            preds.append(pred)
            # Update last_seq
            new_row = last_seq[-1].copy()
            last_seq = np.vstack([last_seq[1:], new_row])
        return preds

    def save_model_and_scaler(model, scaler, model_path='btc_model.h5', scaler_path='btc_scaler.gz'):
        model.save(model_path)
        joblib.dump(scaler, scaler_path)

    def load_model_and_scaler(model_path='btc_model.h5', scaler_path='btc_scaler.gz'):
        model = load_model(model_path, custom_objects={'AttentionBlock': AttentionBlock})
        scaler = joblib.load(scaler_path)
        return model, scaler

else:
    # Fallback functions when TensorFlow is not available
    def train_model(df, feature_cols, lookback=30, forecast_horizon=1, epochs=20, batch_size=32, log_csv_path='training_metrics.csv'):
        print("Warning: TensorFlow not available. Using dummy model.")
        # Create a dummy model for testing
        from sklearn.linear_model import LinearRegression
        X, y, scaler = prepare_data(df, feature_cols, lookback=lookback, forecast_horizon=forecast_horizon)
        model = LinearRegression()
        model.fit(X.reshape(X.shape[0], -1), y)
        
        # Create dummy history
        class DummyHistory:
            def __init__(self):
                self.history = {
                    'loss': [0.1] * epochs,
                    'val_loss': [0.12] * epochs,
                    'mae': [0.05] * epochs,
                    'val_mae': [0.06] * epochs
                }
        
        return model, scaler, DummyHistory()

    def forecast_future(df, model, scaler, feature_cols, lookback=30, forecast_horizon=1, steps=7):
        print("Warning: Using dummy forecast.")
        return [50000.0] * steps

    def save_model_and_scaler(model, scaler, model_path='btc_model.pkl', scaler_path='btc_scaler.pkl'):
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)

    def load_model_and_scaler(model_path='btc_model.pkl', scaler_path='btc_scaler.pkl'):
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        return model, scaler

# --- Sentiment Feature Placeholder ---
def add_sentiment_feature(df, sentiment_series=None):
    '''
    Add sentiment as a feature. If sentiment_series is None, fill with zeros.
    '''
    if sentiment_series is not None:
        df['sentiment'] = sentiment_series
    else:
        df['sentiment'] = 0.0
    return df 