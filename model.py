import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, Bidirectional, Dense, Attention, Concatenate, Dropout
from tensorflow.keras.optimizers import Adam
import joblib
from tensorflow.keras.models import load_model
import os

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
from tensorflow.keras.layers import Layer
import tensorflow as tf

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
def train_model(df, feature_cols, lookback=30, forecast_horizon=1, epochs=20, batch_size=32):
    X, y, scaler = prepare_data(df, feature_cols, lookback=lookback, forecast_horizon=forecast_horizon)
    model = build_bilstm_attention(X.shape[1:])
    history = model.fit(X, y, epochs=epochs, batch_size=batch_size, validation_split=0.1, verbose=1)
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