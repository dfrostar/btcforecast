import streamlit as st
import pandas as pd
import numpy as np
import ta
import plotly.graph_objs as go
from datetime import datetime, timedelta
# --- Import model functions ---
from model import train_model, forecast_future, save_model_and_scaler, load_model_and_scaler, add_sentiment_feature
import os
# from smolagents import ... (placeholder for future integration)
from sklearn.ensemble import IsolationForest
import shap
from sklearn.metrics import mean_absolute_error

st.set_page_config(
    page_title="BTC4Cast - Bitcoin Price Forecasting with AI",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    '''
    <meta name="description" content="BTC4Cast: Accurate Bitcoin price forecasting using deep learning, technical indicators, and sentiment analysis. Interactive charts, backtesting, and more.">
    <meta name="keywords" content="Bitcoin, BTC, price prediction, forecasting, AI, deep learning, technical analysis, sentiment analysis, crypto, cryptocurrency, Streamlit">
    <meta property="og:title" content="BTC4Cast - Bitcoin Price Forecasting with AI">
    <meta property="og:description" content="Accurate Bitcoin price forecasting using deep learning, technical indicators, and sentiment analysis.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://btc4cast.cheval-volant.com">
    <meta property="og:image" content="https://btc4cast.cheval-volant.com/favicon.ico">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "WebSite",
      "name": "BTC4Cast",
      "url": "https://btc4cast.cheval-volant.com",
      "description": "Accurate Bitcoin price forecasting using deep learning, technical indicators, and sentiment analysis.",
      "potentialAction": {
        "@type": "SearchAction",
        "target": "https://btc4cast.cheval-volant.com/?q={search_term_string}",
        "query-input": "required name=search_term_string"
      }
    }
    </script>
    ''',
    unsafe_allow_html=True
)

# --- Sidebar Controls ---
st.sidebar.title('BTC Forecast Settings')
timeframe = st.sidebar.selectbox('Forecast Timeframe (days)', [7, 30, 90, 365], index=0)
indicators = st.sidebar.multiselect('Technical Indicators', ['RSI', 'MACD', 'Bollinger Bands', 'OBV', 'Ichimoku Cloud'], default=['RSI', 'MACD', 'Bollinger Bands'])
lookback = st.sidebar.slider('Lookback Window (days)', 10, 90, 30)
epochs = st.sidebar.slider('Training Epochs', 5, 100, 20)
batch_size = st.sidebar.selectbox('Batch Size', [16, 32, 64], index=1)

# --- Data Loading from CSV ---
def load_btc_csv(path='btc_usd_full_history.csv'):
    try:
        df = pd.read_csv(path, parse_dates=['Date'])
        df.set_index('Date', inplace=True)
        df.rename(columns={"Close": "price", "Volume": "volume"}, inplace=True)
        df = df[['price', 'volume']]  # Only keep necessary columns
        # Ensure numeric types for price and volume
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Failed to load CSV: {e}")
        return pd.DataFrame()

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

# --- Placeholder for Sentiment Analysis ---
def get_sentiment_features(df):
    # TODO: Integrate BERT-based sentiment analysis
    return df

# --- Main App ---
st.title('Bitcoin Price Forecasting (Hybrid Deep Learning Demo)')

st.write('''\
This app demonstrates a hybrid approach to Bitcoin price forecasting using deep learning and technical indicators.\n
- Data sourced from Yahoo Finance (yfinance)\n- Technical indicators: RSI, MACD, Bollinger Bands, OBV, Ichimoku Cloud\n- Model: Bi-LSTM + Attention\n- Forecast timeframes: 7, 30, 90, 365 days\n- Interactive visualizations\n''')

# --- Load Data Button ---
data_loaded = False
df = pd.DataFrame()
if st.button('Load Data'):
    df = load_btc_csv()
    if not df.empty:
        data_loaded = True
        st.success(f"Loaded BTC data: {df.index.min().date()} to {df.index.max().date()}")
        st.dataframe(df.tail())
    else:
        st.error("No data loaded.")

# --- Only proceed if data is loaded ---
if not df.empty:
    df = add_indicators(df, indicators)
    df = add_sentiment_feature(df)

    # --- User Upload: Sentiment Data ---
    st.subheader('Upload Sentiment Data (CSV: date,sentiment)')
    sentiment_csv = st.file_uploader('Upload Sentiment CSV', type=['csv'], key='sentiment')
    if sentiment_csv is not None:
        sentiment_df = pd.read_csv(sentiment_csv, parse_dates=['date'])
        sentiment_df.set_index('date', inplace=True)
        df = df.join(sentiment_df, how='left')
        st.success('Sentiment data merged!')

    # --- User Upload: On-Chain Data ---
    st.subheader('Upload On-Chain Data (CSV: date,feature1,feature2,...)')
    onchain_csv = st.file_uploader('Upload On-Chain CSV', type=['csv'], key='onchain')
    if onchain_csv is not None:
        onchain_df = pd.read_csv(onchain_csv, parse_dates=['date'])
        onchain_df.set_index('date', inplace=True)
        df = df.join(onchain_df, how='left')
        st.success('On-chain data merged!')

    # --- Event CSV Upload ---
    st.subheader('Upload Custom Event CSV (date,type,description)')
    uploaded_event_csv = st.file_uploader('Upload Event CSV', type=['csv'])
    event_df = None
    if uploaded_event_csv is not None:
        event_df = pd.read_csv(uploaded_event_csv)
        st.success('Event CSV loaded!')
        st.dataframe(event_df.head())

    # --- Label halving events ---
    halving_agent = HalvingEventAgent()
    df = halving_agent.label(df)
    st.info('Halving events labeled in the data.')

    # --- Anomaly detection ---
    anomaly_agent = AnomalyDetectionAgent()
    df = anomaly_agent.label(df)
    st.info('Anomalies detected in the data (z-score > 3 on returns).')

    # --- Label custom events ---
    if event_df is not None:
        custom_event_agent = CustomEventAgent(event_df)
        df = custom_event_agent.label(df)
        st.info('Custom events labeled in the data.')

    # --- Isolation Forest Anomaly Detection ---
    iforest_agent = IsolationForestAnomalyAgent(contamination=0.01)
    df = iforest_agent.label(df)
    st.info('Isolation Forest anomalies detected in the data.')

    # --- Feature Selection ---
    st.sidebar.subheader('Select Features for Modeling')
    all_features = [col for col in df.columns if col not in [
        'price', 'volume', 'BB_high', 'BB_low', 'MACD_signal', 'Ichimoku_a', 'Ichimoku_b',
        'returns', 'zscore'
    ] and df[col].dtype != 'O']
    selected_features = st.sidebar.multiselect('Features', all_features, default=all_features)

    # --- Visualization Controls ---
    show_events = st.checkbox('Show Halving Events on Chart', value=True)
    show_anomalies = st.checkbox('Show Anomalies on Chart', value=True)
    show_custom_events = st.checkbox('Show Custom Events on Chart', value=True if event_df is not None else False)
    show_iforest_anomalies = st.checkbox('Show Isolation Forest Anomalies on Chart', value=True)
    show_tables = st.button('Show Event/Anomaly Tables')

    # --- Visualization ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['price'], mode='lines', name='BTC Price', line=dict(color='royalblue')))
    if 'BB_high' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_high'], mode='lines', name='BB High', line=dict(dash='dot', color='orange')))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_low'], mode='lines', name='BB Low', line=dict(dash='dot', color='orange')))
    if show_events and 'halving_event' in df.columns:
        halving_dates = df[df['halving_event'] == 1].index
        fig.add_trace(go.Scatter(x=halving_dates, y=df.loc[halving_dates, 'price'], mode='markers', name='Halving Event', marker=dict(color='red', size=10, symbol='star')))
    if show_anomalies and 'anomaly' in df.columns:
        anomaly_dates = df[df['anomaly'] == 1].index
        fig.add_trace(go.Scatter(x=anomaly_dates, y=df.loc[anomaly_dates, 'price'], mode='markers', name='Anomaly', marker=dict(color='purple', size=8, symbol='x')))
    if show_custom_events and 'custom_event' in df.columns:
        custom_event_dates = df[df['custom_event'] == 1].index
        fig.add_trace(go.Scatter(x=custom_event_dates, y=df.loc[custom_event_dates, 'price'], mode='markers', name='Custom Event', marker=dict(color='green', size=12, symbol='diamond')))
    if show_iforest_anomalies and 'iforest_anomaly' in df.columns:
        iforest_dates = df[df['iforest_anomaly'] == 1].index
        fig.add_trace(go.Scatter(x=iforest_dates, y=df.loc[iforest_dates, 'price'], mode='markers', name='IForest Anomaly', marker=dict(color='black', size=8, symbol='circle-open')))
    fig.update_layout(title='BTC Price with Events & Anomalies', xaxis_title='Date', yaxis_title='Price (USD)')
    st.plotly_chart(fig, use_container_width=True)

    if 'RSI' in df.columns:
        st.line_chart(df['RSI'], height=150, use_container_width=True)
    if 'MACD' in df.columns:
        st.line_chart(df[['MACD', 'MACD_signal']], height=150, use_container_width=True)

    # --- Show Event/Anomaly Tables ---
    if show_tables:
        st.subheader('Recent Halving Events')
        st.dataframe(df[df['halving_event'] == 1][['price']].tail(10))
        st.subheader('Recent Anomalies')
        st.dataframe(df[df['anomaly'] == 1][['price', 'zscore']].tail(10))
        if event_df is not None:
            st.subheader('Recent Custom Events')
            st.dataframe(df[df['custom_event'] == 1][['price']].tail(10))
        st.subheader('Recent Isolation Forest Anomalies')
        st.dataframe(df[df['iforest_anomaly'] == 1][['price', 'volume']].tail(10))

    # --- Model Training and Forecasting ---
    if st.button('Train Model'):
        with st.spinner('Training deep learning model...'):
            train_df = df.dropna(subset=selected_features + ['price'])
            split_idx = int(len(train_df) * 0.9)
            train_data = train_df.iloc[:split_idx]
            val_data = train_df.iloc[split_idx - lookback:]
            model, scaler, history = train_model(train_data, selected_features, lookback=lookback, epochs=epochs, batch_size=batch_size)
            X_val, y_val, _ = train_model.prepare_data(val_data, selected_features, lookback=lookback)
            y_pred = model.predict(X_val).flatten()
            dummy = np.zeros((len(y_pred), len(selected_features) + 1))
            dummy[:, -1] = y_pred
            y_pred_inv = scaler.inverse_transform(dummy)[:, -1]
            dummy[:, -1] = y_val
            y_val_inv = scaler.inverse_transform(dummy)[:, -1]
            mae = mean_absolute_error(y_val_inv, y_pred_inv)
            st.success(f'Model trained! Validation MAE: {mae:.2f}')
            st.line_chart(history.history['loss'], height=150, use_container_width=True)
            # Save model and scaler
            save_model_and_scaler(model, scaler)
            st.session_state['model'] = model
            st.session_state['scaler'] = scaler
            # Forecasting
            preds = forecast_future(train_df, model, scaler, selected_features, lookback=lookback, steps=timeframe)
            future_dates = pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=timeframe)
            forecast_df = pd.DataFrame({'date': future_dates, 'forecast': preds})
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=df.index, y=df['price'], mode='lines', name='BTC Price'))
            fig2.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['forecast'], mode='lines+markers', name='Forecast'))
            fig2.update_layout(title='BTC Price Forecast', xaxis_title='Date', yaxis_title='Price (USD)')
            st.plotly_chart(fig2, use_container_width=True)

            # --- Walk-forward Backtesting ---
            st.subheader('Walk-forward Backtesting')
            window = 365  # 1 year window
            step = 30     # monthly step
            backtest_maes = []
            for start in range(0, len(train_df) - window, step):
                train_bt = train_df.iloc[start:start+window]
                val_bt = train_df.iloc[start+window:start+window+step]
                if len(val_bt) < lookback:
                    continue
                model_bt, scaler_bt, _ = train_model(train_bt, selected_features, lookback=lookback, epochs=epochs, batch_size=batch_size)
                X_val_bt, y_val_bt, _ = train_model.prepare_data(val_bt, selected_features, lookback=lookback)
                y_pred_bt = model_bt.predict(X_val_bt).flatten()
                dummy_bt = np.zeros((len(y_pred_bt), len(selected_features) + 1))
                dummy_bt[:, -1] = y_pred_bt
                y_pred_inv_bt = scaler_bt.inverse_transform(dummy_bt)[:, -1]
                dummy_bt[:, -1] = y_val_bt
                y_val_inv_bt = scaler_bt.inverse_transform(dummy_bt)[:, -1]
                mae_bt = mean_absolute_error(y_val_inv_bt, y_pred_inv_bt)
                backtest_maes.append(mae_bt)
            if backtest_maes:
                st.line_chart(backtest_maes, height=150, use_container_width=True)
                st.write(f'Average Backtest MAE: {np.mean(backtest_maes):.2f}')
            else:
                st.write('Not enough data for backtesting.')

            # --- SHAP Explainability ---
            st.subheader('Model Explainability (SHAP)')
            try:
                # Use a small sample for SHAP due to performance
                X_sample = X_val[:100]
                explainer = shap.Explainer(model, X_sample)
                shap_values = explainer(X_sample)
                st.pyplot(shap.summary_plot(shap_values, X_sample, show=False))
            except Exception as e:
                st.warning(f'SHAP explainability failed: {e}')

# --- Model Saving/Loading ---
if 'model' not in st.session_state:
    st.session_state['model'] = None
    st.session_state['scaler'] = None
    st.session_state['history'] = []

if st.button('Load Saved Model'):
    if os.path.exists('btc_model.h5') and os.path.exists('btc_scaler.gz'):
        model, scaler = load_model_and_scaler()
        st.session_state['model'] = model
        st.session_state['scaler'] = scaler
        st.success('Loaded saved model and scaler!')
    else:
        st.warning('No saved model found.')

# --- Historical Performance Table ---
if st.session_state['history']:
    st.subheader('Historical Model Performance')
    st.dataframe(pd.DataFrame(st.session_state['history']))

# --- Agent Classes (must be defined before use) ---
class HalvingEventAgent:
    def __init__(self, halving_dates=None):
        if halving_dates is None:
            self.halving_dates = [
                pd.Timestamp('2012-11-28'),
                pd.Timestamp('2016-07-09'),
                pd.Timestamp('2020-05-11'),
                pd.Timestamp('2024-04-19')  # Approximate next halving
            ]
        else:
            self.halving_dates = halving_dates
    def label(self, df):
        df['halving_event'] = 0
        for date in self.halving_dates:
            mask = (df.index >= date - pd.Timedelta(days=3)) & (df.index <= date + pd.Timedelta(days=3))
            df.loc[mask, 'halving_event'] = 1
        return df

class AnomalyDetectionAgent:
    def __init__(self, z_thresh=3):
        self.z_thresh = z_thresh
    def label(self, df):
        df['returns'] = df['price'].pct_change()
        mean = df['returns'].mean()
        std = df['returns'].std()
        df['zscore'] = (df['returns'] - mean) / std
        df['anomaly'] = (df['zscore'].abs() > self.z_thresh).astype(int)
        return df

class CustomEventAgent:
    def __init__(self, event_df):
        self.event_df = event_df
    def label(self, df):
        df['custom_event'] = 0
        if self.event_df is not None and not self.event_df.empty:
            for _, row in self.event_df.iterrows():
                event_date = pd.to_datetime(row['date'])
                mask = (df.index == event_date)
                df.loc[mask, 'custom_event'] = 1
        return df

class IsolationForestAnomalyAgent:
    def __init__(self, contamination=0.01):
        self.model = IsolationForest(contamination=contamination, random_state=42)
    def label(self, df):
        # Use price and volume for anomaly detection
        X = df[['price', 'volume']].fillna(0)
        preds = self.model.fit_predict(X)
        df['iforest_anomaly'] = (preds == -1).astype(int)
        return df

class DataAgent:
    def label(self, df):
        raise NotImplementedError

# (Other agent classes inherit from DataAgent, but for now, keep as is for backward compatibility) 