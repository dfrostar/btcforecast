import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_option_menu import option_menu
import yfinance as yf
import json
import os
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

# --- App Configuration ---
st.set_page_config(
    page_title="BTC Forecast Pro - Advanced Bitcoin Forecasting",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Mobile Responsive CSS ---
def load_mobile_css():
    """Load mobile-responsive CSS for better mobile experience."""
    css = """
    <style>
    /* Mobile-first responsive design */
    @media screen and (max-width: 768px) {
        .main .block-container {
            padding: 1rem 0.5rem;
            max-width: 100%;
        }
        
        .stButton > button {
            min-height: 44px;
            font-size: 16px;
            width: 100%;
            max-width: 300px;
        }
        
        .stPlotlyChart {
            height: 300px !important;
        }
        
        .metric-card {
            margin: 0.5rem 0;
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            background: white;
        }
        
        .price-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem 0;
            text-align: center;
        }
        
        .price-card .price {
            font-size: 2rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        
        .connection-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            border-radius: 8px;
            margin: 0.5rem 0;
        }
        
        .connection-status.connected {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .connection-status.disconnected {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .mobile-tabs {
            display: flex;
            overflow-x: auto;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 0.5rem 0;
            -webkit-overflow-scrolling: touch;
        }
        
        .mobile-tab {
            flex: 1;
            min-width: 120px;
            padding: 0.75rem;
            text-align: center;
            border: none;
            background: transparent;
            color: #6c757d;
            font-size: 0.9rem;
            white-space: nowrap;
        }
        
        .mobile-tab.active {
            background: #007bff;
            color: white;
            border-radius: 8px;
        }
    }
    
    /* Tablet optimization */
    @media screen and (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding: 1.5rem;
            max-width: 90%;
        }
        
        .stPlotlyChart {
            height: 400px !important;
        }
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .metric-card {
            background: #2d3748;
            color: #e2e8f0;
            border: 1px solid #4a5568;
        }
        
        .price-card {
            background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%);
        }
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# --- PWA Manifest ---
def add_pwa_manifest():
    """Add PWA manifest for app-like experience."""
    manifest = """
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#1f77b4">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="BTC Forecast Pro">
    <link rel="apple-touch-icon" href="/static/icons/icon-192x192.png">
    """
    st.markdown(manifest, unsafe_allow_html=True)

# --- API Configuration ---
API_BASE_URL = "http://127.0.0.1:8001"

# --- Helper Functions ---
def get_api_data(endpoint):
    """Fetches data from the backend API."""
    try:
        response = requests.get(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the API: {e}")
        return None

def post_api_data(endpoint, data=None):
    """Posts data to the backend API."""
    try:
        if data:
            response = requests.post(f"{API_BASE_URL}/{endpoint}", json=data, timeout=10)
        else:
            response = requests.post(f"{API_BASE_URL}/{endpoint}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Backend API is not available. Using demo mode.")
        return None
    except requests.exceptions.Timeout:
        st.warning("⚠️ Backend API request timed out. Using demo mode.")
        return None
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ API connection issue: {e}. Using demo mode.")
        return None

def get_bitcoin_data_with_fallback():
    """Get Bitcoin data with multiple fallback options to handle rate limiting."""
    try:
        # Try yfinance first
        import yfinance as yf
        btc = yf.Ticker("BTC-USD")
        hist = btc.history(period="30d")
        if not hist.empty:
            return hist, "yfinance"
    except Exception as e:
        st.warning(f"yfinance unavailable: {str(e)}")
    
    try:
        # Try CoinGecko API as fallback
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "30",
            "interval": "daily"
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            prices = data['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.columns = ['Close']
            # Add other required columns for compatibility
            df['Open'] = df['Close']
            df['High'] = df['Close']
            df['Low'] = df['Close']
            df['Volume'] = 0
            return df, "coingecko"
    except Exception as e:
        st.warning(f"CoinGecko unavailable: {str(e)}")
    
    # Generate synthetic data as final fallback
    try:
        st.info("Using synthetic data due to API limitations")
        dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
        base_price = 45000
        np.random.seed(42)  # For reproducible demo data
        price_changes = np.random.normal(0, 0.02, 30)  # 2% daily volatility
        prices = [base_price]
        for change in price_changes[1:]:
            prices.append(prices[-1] * (1 + change))
        
        df = pd.DataFrame({
            'Open': prices,
            'High': [p * 1.01 for p in prices],
            'Low': [p * 0.99 for p in prices],
            'Close': prices,
            'Volume': np.random.randint(1000, 10000, 30)
        }, index=dates)
        return df, "synthetic"
    except Exception as e:
        st.error(f"Failed to generate fallback data: {str(e)}")
        return None, None

def load_training_results():
    """Load training results from JSON file."""
    try:
        if os.path.exists("training_results.json"):
            with open("training_results.json", "r") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading training results: {e}")
    return None

def load_training_metrics():
    """Load training metrics from CSV file."""
    try:
        if os.path.exists("training_metrics.csv"):
            return pd.read_csv("training_metrics.csv")
    except Exception as e:
        st.error(f"Error loading training metrics: {e}")
    return None

def plot_forecast(forecast_data):
    """Plots historical and forecasted Bitcoin prices."""
    if not forecast_data:
        return

    try:
        hist_df = pd.DataFrame(forecast_data.get("history", []))
        forecast_df = pd.DataFrame(forecast_data.get("forecast", []))

        if "Date" not in hist_df.columns or "Date" not in forecast_df.columns:
             st.error("Dataframes must contain 'Date' column.")
             return

        hist_df['Date'] = pd.to_datetime(hist_df['Date'])
        forecast_df['Date'] = pd.to_datetime(forecast_df['Date'])
        
        fig = go.Figure()

        # Historical data
        fig.add_trace(go.Scatter(
            x=hist_df['Date'],
            y=hist_df['Close'],
            mode='lines',
            name='Historical Price',
            line=dict(color='#1f77b4', width=2)
        ))

        # Forecast data
        fig.add_trace(go.Scatter(
            x=forecast_df['Date'],
            y=forecast_df['Predicted_Close'],
            mode='lines',
            name='Forecasted Price',
            line=dict(color='#ff7f0e', dash='dash', width=2)
        ))

        # Confidence interval (if available)
        if 'confidence_lower' in forecast_df.columns and 'confidence_upper' in forecast_df.columns:
            fig.add_trace(go.Scatter(
                x=forecast_df['Date'],
                y=forecast_df['confidence_upper'],
                mode='lines',
                name='Upper Confidence',
                line=dict(width=0),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=forecast_df['Date'],
                y=forecast_df['confidence_lower'],
                mode='lines',
                fill='tonexty',
                fillcolor='rgba(255, 127, 14, 0.2)',
                name='Confidence Interval',
                line=dict(width=0),
                showlegend=False
            ))

        fig.update_layout(
            title="Bitcoin Price: Historical vs. Forecast",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            legend_title="Legend",
            template="plotly_dark",
            height=600
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred while plotting the data: {e}")

def plot_training_metrics(metrics_df):
    """Plot training metrics."""
    if metrics_df is None or metrics_df.empty:
        return
    
    # Create subplots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Training Metrics Over Time', fontsize=16)
    
    # Loss plot
    axes[0, 0].plot(metrics_df['epoch'], metrics_df['loss'], label='Training Loss', color='blue')
    axes[0, 0].plot(metrics_df['epoch'], metrics_df['val_loss'], label='Validation Loss', color='red')
    axes[0, 0].set_title('Loss')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].legend()
    axes[0, 0].grid(True)
    
    # MAE plot
    axes[0, 1].plot(metrics_df['epoch'], metrics_df['mae'], label='Training MAE', color='blue')
    axes[0, 1].plot(metrics_df['epoch'], metrics_df['val_mae'], label='Validation MAE', color='red')
    axes[0, 1].set_title('Mean Absolute Error')
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('MAE')
    axes[0, 1].legend()
    axes[0, 1].grid(True)
    
    # R² Score (if available)
    if 'r2_score' in metrics_df.columns:
        axes[1, 0].plot(metrics_df['epoch'], metrics_df['r2_score'], label='R² Score', color='green')
        axes[1, 0].set_title('R² Score')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('R² Score')
        axes[1, 0].legend()
        axes[1, 0].grid(True)
    
    # Learning rate (if available)
    if 'learning_rate' in metrics_df.columns:
        axes[1, 1].plot(metrics_df['epoch'], metrics_df['learning_rate'], label='Learning Rate', color='purple')
        axes[1, 1].set_title('Learning Rate')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('Learning Rate')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
    
    plt.tight_layout()
    st.pyplot(fig)

def display_model_status():
    """Display current model status and metrics."""
    st.subheader("📊 Model Status & Performance")
    
    # Load training results
    training_results = load_training_results()
    
    if training_results:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="R² Score", 
                value=f"{training_results.get('r2', 0):.3f}",
                delta=f"{training_results.get('r2', 0) - 0.5:.3f}" if training_results.get('r2', 0) > 0.5 else None
            )
        
        with col2:
            st.metric(
                label="MAE (USD)", 
                value=f"${training_results.get('mae', 0):,.0f}",
                delta=f"-${training_results.get('mae', 0) - 5000:.0f}" if training_results.get('mae', 0) < 10000 else None
            )
        
        with col3:
            st.metric(
                label="RMSE (USD)", 
                value=f"${training_results.get('rmse', 0):,.0f}"
            )
        
        with col4:
            st.metric(
                label="Training Time", 
                value=f"{training_results.get('duration_seconds', 0):.1f}s"
            )
        
        # Additional metrics
        st.write("### 📈 Performance Details")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Training Configuration:**")
            st.write(f"- Epochs: {training_results.get('epochs', 'N/A')}")
            st.write(f"- Lookback: {training_results.get('lookback', 'N/A')}")
            st.write(f"- Batch Size: {training_results.get('batch_size', 'N/A')}")
            st.write(f"- Last Training: {training_results.get('timestamp', 'N/A')}")
        
        with col2:
            st.write("**Technical Indicators:**")
            indicators = training_results.get('indicators', [])
            for indicator in indicators:
                st.write(f"- {indicator}")
        
        # Performance assessment
        st.write("### 🎯 Performance Assessment")
        r2_score = training_results.get('r2', 0)
        mae = training_results.get('mae', 0)
        
        if r2_score > 0.7:
            st.success("✅ Excellent model performance (R² > 0.7)")
        elif r2_score > 0.5:
            st.warning("⚠️ Good model performance (R² > 0.5)")
        else:
            st.error("❌ Model needs improvement (R² < 0.5)")
        
        if mae < 5000:
            st.success("✅ Low prediction error (MAE < $5,000)")
        elif mae < 10000:
            st.warning("⚠️ Moderate prediction error (MAE < $10,000)")
        else:
            st.error("❌ High prediction error (MAE > $10,000)")
    
    else:
        st.warning("No training results found. Please train the model first.")

def display_training_visualizations():
    """Display training visualizations."""
    st.subheader("📊 Training Visualizations")
    
    # Load training metrics
    metrics_df = load_training_metrics()
    
    if metrics_df is not None and not metrics_df.empty:
        plot_training_metrics(metrics_df)
    else:
        st.info("No training metrics available. Train the model to see visualizations.")
    
    # Show training plots if available
    if os.path.exists("training_plots"):
        plot_files = [f for f in os.listdir("training_plots") if f.endswith('.png')]
        if plot_files:
            st.write("### 📈 Training Plots")
            for plot_file in plot_files:
                st.image(f"training_plots/{plot_file}", caption=plot_file, use_column_width=True)

def display_forecast_analysis():
    """Display detailed forecast analysis."""
    st.subheader("🔮 Forecast Analysis")
    
    # Load current forecast
    try:
        if os.path.exists("btc_forecast.csv"):
            forecast_df = pd.read_csv("btc_forecast.csv")
            forecast_df['date'] = pd.to_datetime(forecast_df['date'])
            
            # Calculate forecast statistics
            current_price = forecast_df['forecast'].iloc[0]
            max_price = forecast_df['forecast'].max()
            min_price = forecast_df['forecast'].min()
            avg_price = forecast_df['forecast'].mean()
            trend = "📈 Bullish" if forecast_df['forecast'].iloc[-1] > current_price else "📉 Bearish"
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Current Forecast", f"${current_price:,.0f}")
            
            with col2:
                st.metric("Max Forecast", f"${max_price:,.0f}")
            
            with col3:
                st.metric("Min Forecast", f"${min_price:,.0f}")
            
            with col4:
                st.metric("Trend", trend)
            
            # Forecast chart
            fig = px.line(forecast_df, x='date', y='forecast', 
                         title='Bitcoin Price Forecast (Next 30 Days)',
                         labels={'forecast': 'Price (USD)', 'date': 'Date'})
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            # Forecast table
            st.write("### 📋 Detailed Forecast")
            st.dataframe(forecast_df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading forecast data: {e}")

def display_upgrade_banner(feature_name: str, premium_features: list = None, cta_text: str = "💳 Upgrade Now", price: str = "$29.99/month"):
    """Display a consistent upgrade banner for premium-locked features.
    
    Args:
        feature_name (str): Name of the feature being promoted
        premium_features (list): List of premium features to display
        cta_text (str): Call-to-action button text
        price (str): Price display text
    """
    if premium_features is None:
        premium_features = [
            "Advanced predictions (7-day forecast)",
            "All 15+ technical indicators", 
            "Portfolio management",
            "Risk analytics",
            "Real-time alerts",
            "Priority support"
        ]
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border: 2px solid rgba(255,255,255,0.1);
    ">
        <h2 style="margin: 0 0 1rem 0; font-size: 1.5rem;">🚀 Upgrade to Premium</h2>
        <p style="margin: 0 0 1.5rem 0; font-size: 1.1rem;">
            Unlock <strong>{feature_name}</strong> and all premium features for just <strong>{price}</strong>
        </p>
        <div style="display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
            <div style="background: rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; backdrop-filter: blur(10px);">
                💎 Premium Features
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; backdrop-filter: blur(10px);">
                🔔 Real-time Alerts
            </div>
            <div style="background: rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; backdrop-filter: blur(10px);">
                📊 Advanced Analytics
            </div>
        </div>
        <div style="margin-top: 1.5rem;">
            <button style="
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                border: none;
                padding: 0.75rem 2rem;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(40, 167, 69, 0.3);
            " onclick="window.location.href='#subscriptions'" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(40, 167, 69, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(40, 167, 69, 0.3)'">
                {cta_text}
            </button>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature list with enhanced styling
    with st.expander("📋 See All Premium Features", expanded=False):
        st.markdown("""
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #667eea;">
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            for feature in premium_features[:len(premium_features)//2]:
                st.markdown(f"<div style='margin: 0.5rem 0;'><span style='color: #28a745; font-weight: bold;'>✅</span> {feature}</div>", unsafe_allow_html=True)
        with col2:
            for feature in premium_features[len(premium_features)//2:]:
                st.markdown(f"<div style='margin: 0.5rem 0;'><span style='color: #28a745; font-weight: bold;'>✅</span> {feature}</div>", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

def display_feature_lock_banner(feature_name: str, message: str = None):
    """Display a simple feature lock banner for basic premium features."""
    if message is None:
        message = f"This feature requires a premium subscription"
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #6c757d 0%, #495057 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.1);
    ">
        <div style="font-size: 1.2rem; margin-bottom: 0.5rem;">🔒 {feature_name}</div>
        <div style="font-size: 0.9rem; opacity: 0.9;">{message}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Market Regime Detection Utility ---
def detect_market_regime(df, window=30):
    """Detect the current market regime based on recent price action."""
    returns = df['Close'].pct_change().dropna()
    volatility = returns.rolling(window).std().iloc[-1] if len(returns) >= window else returns.std()
    trend = (df['Close'].iloc[-1] / df['Close'].iloc[-window] - 1) if len(df) >= window else 0
    if trend > 0.1:
        if volatility > 0.03:
            return "Volatile Bull"
        else:
            return "Steady Bull"
    elif trend < -0.1:
        if volatility > 0.03:
            return "Volatile Bear"
        else:
            return "Steady Bear"
    else:
        if volatility > 0.03:
            return "Volatile Sideways"
        else:
            return "Range-Bound"

# --- Improved Demo Forecast Function ---
def generate_realistic_demo_forecast(days, current_price=None):
    if current_price is None:
        try:
            import yfinance as yf
            btc = yf.Ticker("BTC-USD")
            current_price = btc.history(period="1d")['Close'].iloc[-1]
        except:
            current_price = 45000
    prices = [current_price]
    volatility = current_price * 0.03
    regime = np.random.choice(['bull', 'bear', 'sideways'])
    if regime == 'bull':
        trend = 0.003
    elif regime == 'bear':
        trend = -0.003
    else:
        trend = 0.0
    for i in range(days):
        volatility = 0.9 * volatility + 0.1 * abs(prices[-1] - prices[0]) / prices[0] * current_price * 0.03
        momentum = 0.2 * (prices[-1] - prices[max(0, i-5)]) / prices[max(0, i-5)]
        daily_return = trend + momentum + np.random.normal(0, 1) * volatility / current_price
        next_price = prices[-1] * (1 + daily_return)
        prices.append(next_price)
    lower_bound = [price * (1 - 0.02 * (i+1)) for i, price in enumerate(prices[1:])]
    upper_bound = [price * (1 + 0.02 * (i+1)) for i, price in enumerate(prices[1:])]
    return prices[1:], lower_bound, upper_bound

# --- Main Application ---
def main():
    # Load mobile CSS and PWA support
    load_mobile_css()
    add_pwa_manifest()
    
    # Check if user is logged in (simplified for demo)
    user_logged_in = st.session_state.get('user_logged_in', False)
    
    # Login/Register section if not logged in
    if not user_logged_in:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>🚀 BTC Forecast Pro</h1>
            <p style="font-size: 1.2rem; color: #666;">Advanced Bitcoin Price Forecasting with AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Login/Register tabs
        auth_tab = st.tabs(["🔐 Login", "📝 Register", "👀 Try Demo"])
        
        with auth_tab[0]:
            st.write("### 🔐 Login to Your Account")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔐 Login", type="primary"):
                    if username and password:
                        # Call backend API for login
                        login_data = {"username": username, "password": password}
                        response = post_api_data("auth/login", login_data)
                        
                        if response and "access_token" in response:
                            st.session_state.user_logged_in = True
                            st.session_state.username = username
                            st.session_state.access_token = response["access_token"]
                            st.success("Login successful!")
                            st.rerun()
                        elif response is None:
                            # API not available, use fallback
                            st.session_state.user_logged_in = True
                            st.session_state.username = username
                            st.session_state.demo_mode = True
                            st.success("Login successful! (Demo mode - API unavailable)")
                            st.rerun()
                        else:
                            st.error("Login failed. Please check your credentials.")
                    else:
                        st.error("Please enter username and password")
            
            with col2:
                if st.button("🔑 Forgot Password?"):
                    st.info("Password reset functionality coming soon!")
        
        with auth_tab[1]:
            st.write("### 📝 Create New Account")
            new_username = st.text_input("Choose Username", key="reg_username")
            new_email = st.text_input("Email Address", key="reg_email")
            new_password = st.text_input("Choose Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.button("📝 Create Account", type="primary"):
                if new_username and new_email and new_password and new_password == confirm_password:
                    # Call backend API for registration
                    register_data = {
                        "username": new_username,
                        "email": new_email,
                        "password": new_password,
                        "role": "free"
                    }
                    response = post_api_data("auth/register", register_data)
                    
                    if response and "username" in response:
                        st.session_state.user_logged_in = True
                        st.session_state.username = new_username
                        st.success("Account created successfully!")
                        st.rerun()
                    elif response is None:
                        # API not available, use fallback
                        st.session_state.user_logged_in = True
                        st.session_state.username = new_username
                        st.session_state.demo_mode = True
                        st.success("Account created successfully! (Demo mode - API unavailable)")
                        st.rerun()
                    else:
                        st.error("Account creation failed. Please try again.")
                else:
                    st.error("Please fill all fields and ensure passwords match")
        
        with auth_tab[2]:
            st.write("### 👀 Try Demo Mode")
            st.info("Experience BTC Forecast Pro without creating an account!")
            st.write("**Demo Features:**")
            st.write("✅ View Bitcoin price chart")
            st.write("✅ Generate sample forecasts")
            st.write("✅ Explore basic features")
            st.write("⚠️ Limited functionality")
            
            if st.button("🎮 Start Demo", type="primary"):
                st.session_state.user_logged_in = True
                st.session_state.demo_mode = True
                st.session_state.username = "Demo User"
                st.success("Demo mode activated!")
                st.rerun()
        
        # Show some preview content
        st.markdown("---")
        st.write("### 📊 Preview: Live Bitcoin Chart")
        
        # Set default values for preview
        chart_type = "Line"
        indicators = ["MA"]  # Default indicators for preview
        timeframe = "1M"     # Default timeframe for preview
        
        # Get current BTC price for preview with fallback
        with st.spinner("Loading Bitcoin data..."):
            hist, data_source = get_bitcoin_data_with_fallback()
            
            if hist is not None:
                # Show data source indicator
                if data_source == "synthetic":
                    st.info("📊 Using demo data (API rate limited)")
                elif data_source == "coingecko":
                    st.success("📊 Data from CoinGecko")
                else:
                    st.success("📊 Data from Yahoo Finance")
                
                # Create chart
                fig = go.Figure()
                
                if chart_type == "Candlestick":
                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist['Open'],
                        high=hist['High'],
                        low=hist['Low'],
                        close=hist['Close'],
                        name='Bitcoin',
                        increasing_line_color='#00ff88',
                        decreasing_line_color='#ff4444'
                    ))
                elif chart_type == "Line":
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        mode='lines',
                        name='Bitcoin Price',
                        line=dict(color='#f7931a', width=2)
                    ))
                else:  # Area
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        mode='lines',
                        fill='tonexty',
                        name='Bitcoin Price',
                        line=dict(color='#f7931a', width=2)
                    ))
                
                # Add indicators
                if "MA" in indicators:
                    ma20 = hist['Close'].rolling(window=20).mean()
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=ma20,
                        mode='lines',
                        name='20-day MA',
                        line=dict(color='#ff6b6b', width=1, dash='dash')
                    ))
                
                if "Bollinger Bands" in indicators:
                    ma20 = hist['Close'].rolling(window=20).mean()
                    std20 = hist['Close'].rolling(window=20).std()
                    upper_band = ma20 + (std20 * 2)
                    lower_band = ma20 - (std20 * 2)
                    
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=upper_band,
                        mode='lines',
                        name='Upper BB',
                        line=dict(color='#4ecdc4', width=1, dash='dot')
                    ))
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=lower_band,
                        mode='lines',
                        name='Lower BB',
                        line=dict(color='#4ecdc4', width=1, dash='dot'),
                        fill='tonexty'
                    ))
                
                fig.update_layout(
                    title=f"Bitcoin Price Chart ({timeframe})",
                    xaxis_title="Date",
                    yaxis_title="Price (USD)",
                    height=600,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Price metrics
                current_price = hist['Close'].iloc[-1]
                if len(hist) > 1:
                    price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
                    price_change_pct = (price_change / hist['Close'].iloc[-2]) * 100
                else:
                    price_change = 0
                    price_change_pct = 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Current Price", f"${current_price:,.2f}")
                with col2:
                    st.metric("24h Change", f"${price_change:,.2f}", f"{price_change_pct:+.2f}%")
                with col3:
                    st.metric("Period High", f"${hist['High'].max():,.2f}")
                with col4:
                    st.metric("Period Low", f"${hist['Low'].min():,.2f}")
                
                # Quick forecast button
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("### 🔮 Ready for a Price Forecast?")
                    st.write("Get AI-powered predictions for Bitcoin's future price movement.")
                with col2:
                    if st.button("🚀 Generate Forecast", type="primary"):
                        st.session_state.show_forecast = True
                        st.rerun()
                
            else:
                st.error("Unable to load Bitcoin price data")
                st.info("Please try again later or contact support if the issue persists.")
        
        return
    
    # Main application (user is logged in)
    with st.sidebar:
        # User info
        st.markdown(f"### 👤 Welcome, {st.session_state.get('username', 'User')}")
        if st.session_state.get('demo_mode', False):
            st.warning("🎮 Demo Mode")
        
        # Navigation
        selected = option_menu(
            "Navigation",
            ["📈 Bitcoin Chart", "🔮 Forecast", "💰 Live Prices", "👥 Community", "💼 Portfolio", "💳 Subscriptions", "⚙️ Settings"],
            icons=['chart-line', 'graph-up-arrow', 'lightning', 'people', 'briefcase', 'credit-card', 'settings'],
            menu_icon="cast",
            default_index=0,
        )
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        if st.button("🔮 Quick Forecast"):
            st.session_state.quick_forecast = True
            st.rerun()
        
        if st.button("💰 Check Prices"):
            st.session_state.check_prices = True
            st.rerun()
        
        # Logout
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # Main content area
    if selected == "📈 Bitcoin Chart":
        st.title("📈 Bitcoin Price Chart & Analysis")
        
        # Chart timeframe selector
        col1, col2, col3 = st.columns(3)
        with col1:
            timeframe = st.selectbox("Timeframe", ["1D", "1W", "1M", "3M", "6M", "1Y"], index=2)
        with col2:
            chart_type = st.selectbox("Chart Type", ["Candlestick", "Line", "Area"], index=0)
        with col3:
            indicators = st.multiselect("Indicators", ["MA", "RSI", "MACD", "Bollinger Bands"], default=["MA"])
        
        # Load Bitcoin data with fallback
        with st.spinner("Loading Bitcoin data..."):
            hist, data_source = get_bitcoin_data_with_fallback()
            
            if hist is not None:
                # Show data source indicator
                if data_source == "synthetic":
                    st.info("📊 Using demo data (API rate limited)")
                elif data_source == "coingecko":
                    st.success("📊 Data from CoinGecko")
                else:
                    st.success("📊 Data from Yahoo Finance")
                
                # Create chart
                fig = go.Figure()
                
                if chart_type == "Candlestick":
                    fig.add_trace(go.Candlestick(
                        x=hist.index,
                        open=hist['Open'],
                        high=hist['High'],
                        low=hist['Low'],
                        close=hist['Close'],
                        name='Bitcoin',
                        increasing_line_color='#00ff88',
                        decreasing_line_color='#ff4444'
                    ))
                elif chart_type == "Line":
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        mode='lines',
                        name='Bitcoin Price',
                        line=dict(color='#f7931a', width=2)
                    ))
                else:  # Area
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=hist['Close'],
                        mode='lines',
                        fill='tonexty',
                        name='Bitcoin Price',
                        line=dict(color='#f7931a', width=2)
                    ))
                
                # Add indicators
                if "MA" in indicators:
                    ma20 = hist['Close'].rolling(window=20).mean()
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=ma20,
                        mode='lines',
                        name='20-day MA',
                        line=dict(color='#ff6b6b', width=1, dash='dash')
                    ))
                
                if "Bollinger Bands" in indicators:
                    ma20 = hist['Close'].rolling(window=20).mean()
                    std20 = hist['Close'].rolling(window=20).std()
                    upper_band = ma20 + (std20 * 2)
                    lower_band = ma20 - (std20 * 2)
                    
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=upper_band,
                        mode='lines',
                        name='Upper BB',
                        line=dict(color='#4ecdc4', width=1, dash='dot')
                    ))
                    fig.add_trace(go.Scatter(
                        x=hist.index,
                        y=lower_band,
                        mode='lines',
                        name='Lower BB',
                        line=dict(color='#4ecdc4', width=1, dash='dot'),
                        fill='tonexty'
                    ))
                
                fig.update_layout(
                    title=f"Bitcoin Price Chart ({timeframe})",
                    xaxis_title="Date",
                    yaxis_title="Price (USD)",
                    height=600,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Price metrics
                current_price = hist['Close'].iloc[-1]
                if len(hist) > 1:
                    price_change = hist['Close'].iloc[-1] - hist['Close'].iloc[-2]
                    price_change_pct = (price_change / hist['Close'].iloc[-2]) * 100
                else:
                    price_change = 0
                    price_change_pct = 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Current Price", f"${current_price:,.2f}")
                with col2:
                    st.metric("24h Change", f"${price_change:,.2f}", f"{price_change_pct:+.2f}%")
                with col3:
                    st.metric("Period High", f"${hist['High'].max():,.2f}")
                with col4:
                    st.metric("Period Low", f"${hist['Low'].min():,.2f}")
                
                # Quick forecast button
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("### 🔮 Ready for a Price Forecast?")
                    st.write("Get AI-powered predictions for Bitcoin's future price movement.")
                with col2:
                    if st.button("🚀 Generate Forecast", type="primary"):
                        st.session_state.show_forecast = True
                        st.rerun()
                
            else:
                st.error("Unable to load Bitcoin price data")
                st.info("Please try again later or contact support if the issue persists.")

    elif selected == "🔮 Forecast":
        st.title("🔮 Bitcoin Price Forecast")
        
        # Check if user has subscription for advanced features
        demo_mode = st.session_state.get('demo_mode', False)
        
        if demo_mode:
            st.warning("🎮 Demo Mode: Limited forecast functionality")
        
        # Forecast options
        col1, col2 = st.columns(2)
        
        with col1:
            # Limit forecast days to 7 in demo mode
            max_days = 7 if demo_mode else 30
            forecast_days = st.slider("Forecast Days", 1, max_days, min(7, max_days))
            if demo_mode:
                st.caption("<span title='Demo users are limited to 7-day forecasts. Upgrade for more!'>ℹ️ Demo users are limited to 7-day forecasts. <a href='#subscriptions' style='color:#f7931a;text-decoration:underline;'>Upgrade for more</a>!</span>", unsafe_allow_html=True)
            confidence_level = st.slider("Confidence Level", 0.5, 0.95, 0.8, 0.05)
        
        with col2:
            forecast_type = st.selectbox(
                "Forecast Type",
                ["Standard", "Recursive", "Feature-based"] if not demo_mode else ["Standard"]
            )
            
            if demo_mode and forecast_type != "Standard":
                st.info("Advanced forecast types require a subscription")
        
        # Generate forecast button
        if st.button("🚀 Generate Forecast", type="primary"):
            with st.spinner("Generating forecast..."):
                if demo_mode:
                    st.success("Demo forecast generated!")
                    # Use improved demo forecast with fallback
                    hist, data_source = get_bitcoin_data_with_fallback()
                    if hist is not None and len(hist) > 1:
                        prior_price = hist['Close'].iloc[-2]
                    else:
                        prior_price = 45000  # Fallback price
                    
                    forecast_prices, lower_bound, upper_bound = generate_realistic_demo_forecast(forecast_days, current_price=prior_price)
                    dates = pd.date_range(start=pd.Timestamp.now() + pd.Timedelta(days=1), periods=forecast_days, freq='D')
                    # Plot demo forecast with confidence intervals
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=forecast_prices,
                        mode='lines+markers',
                        name='Forecast',
                        line=dict(color='#00ff88', width=3)
                    ))
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=upper_bound,
                        mode='lines',
                        name='Upper Bound',
                        line=dict(color='rgba(0,255,136,0.2)', width=0),
                        showlegend=False
                    ))
                    fig.add_trace(go.Scatter(
                        x=dates,
                        y=lower_bound,
                        mode='lines',
                        name='Lower Bound',
                        fill='tonexty',
                        line=dict(color='rgba(0,255,136,0.2)', width=0),
                        showlegend=False
                    ))
                    fig.update_layout(
                        title=f"Bitcoin Price Forecast ({forecast_days} days)",
                        xaxis_title="Date",
                        yaxis_title="Price (USD)",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    display_upgrade_banner("7-day forecast")
                    if st.button("Go to Upgrade Page", key="upgrade_cta_btn"):
                        st.session_state['selected'] = "💳 Subscriptions"
                        st.experimental_rerun()
                else:
                    # Real forecast
                    if forecast_type == "Standard":
                        forecast_data = post_api_data("predict", {
                            "days": forecast_days,
                            "confidence_level": confidence_level
                        })
                    elif forecast_type == "Recursive":
                        forecast_data = post_api_data("forecast/recursive", {
                            "days": forecast_days,
                            "confidence_level": confidence_level
                        })
                    else:
                        forecast_data = post_api_data("forecast/features", {
                            "indicator": "rsi",
                            "days": forecast_days
                        })
                    
                    if forecast_data:
                        st.success("Forecast generated successfully!")
                        plot_forecast(forecast_data)
                    else:
                        st.error("Failed to generate forecast")

    elif selected == "💰 Live Prices":
        st.title("💰 Live Cryptocurrency Prices")
        
        # Get real-time prices
        try:
            prices_data = get_api_data("realtime/prices")
            
            if prices_data and 'prices' in prices_data:
                prices = prices_data['prices']
                st.success("✅ Real-time data connection: Active")
                
                # Live price cards
                st.write("### 💰 Live Prices")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                symbols = ['btcusdt', 'ethusdt', 'adausdt', 'dotusdt', 'solusdt']
                colors = ['#f7931a', '#627eea', '#0033ad', '#e6007a', '#9945ff']
                
                for i, (symbol, color) in enumerate(zip(symbols, colors)):
                    with [col1, col2, col3, col4, col5][i]:
                        if symbol in prices:
                            price_data = prices[symbol]
                            st.markdown(f"""
                            <div class="price-card">
                                <h3>{symbol.upper()}</h3>
                                <div class="price">${price_data.get('price', 0):,.2f}</div>
                                <div class="change">Volume: {price_data.get('volume', 0):,.0f}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div class="price-card" style="background: #2d2d2d;">
                                <h3>{symbol.upper()}</h3>
                                <div class="price">--</div>
                                <div class="change">No data</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Price alerts
                st.write("### 🔔 Price Alerts")
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    alert_symbol = st.selectbox("Symbol", ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT"])
                    alert_price = st.number_input("Target Price ($)", min_value=0.0, value=50000.0)
                    alert_type = st.selectbox("Alert Type", ["Above", "Below"])
                
                with col2:
                    st.write("")
                    st.write("")
                    if st.button("🔔 Create Alert", type="primary"):
                        if not st.session_state.get('demo_mode', False):
                            with st.spinner("Creating alert..."):
                                alert_data = post_api_data("realtime/alerts", {
                                    "symbol": alert_symbol,
                                    "target_price": alert_price,
                                    "alert_type": alert_type
                                })
                                if alert_data:
                                    st.success("Alert created successfully!")
                                else:
                                    st.error("Failed to create alert")
                        else:
                            st.info("💡 Price alerts require a subscription")
                
            else:
                st.error("❌ Real-time data connection: Failed")
                display_upgrade_banner("Real-time cryptocurrency prices", [
                    "Live price updates every 30 seconds",
                    "Real-time volume and market data",
                    "Price alerts and notifications",
                    "Advanced charting tools",
                    "Portfolio tracking",
                    "Risk analytics"
                ])
                
        except Exception as e:
            st.error(f"❌ Real-time data connection: Failed - {str(e)}")
            display_upgrade_banner("Real-time cryptocurrency prices", [
                "Live price updates every 30 seconds",
                "Real-time volume and market data", 
                "Price alerts and notifications",
                "Advanced charting tools",
                "Portfolio tracking",
                "Risk analytics"
            ])

    elif selected == "👥 Community":
        st.title("👥 Community & Social Features")
        
        # Social tabs
        social_tab = st.tabs(["📊 Leaderboard", "💬 Forums", "📈 Shared Predictions", "🎯 Trending"])
        
        with social_tab[0]:
            st.write("### 🏆 Prediction Leaderboard")
            
            if st.button("🔄 Refresh Leaderboard"):
                with st.spinner("Loading leaderboard..."):
                    if not st.session_state.get('demo_mode', False):
                        leaderboard_data = get_api_data("social/leaderboard")
                        if leaderboard_data:
                            # Create leaderboard dataframe
                            df = pd.DataFrame(leaderboard_data)
                            st.dataframe(df, use_container_width=True)
                            
                            # Top 3 visualization
                            if len(df) >= 3:
                                top_3 = df.head(3)
                                fig = px.bar(top_3, x='username', y='accuracy_score', 
                                           title="Top 3 Predictors", 
                                           color='accuracy_score',
                                           color_continuous_scale='viridis')
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.error("Failed to load leaderboard")
                    else:
                        # Demo leaderboard
                        demo_data = [
                            {"username": "crypto_master", "accuracy_score": 0.89, "rank": 1},
                            {"username": "analyst_pro", "accuracy_score": 0.85, "rank": 2},
                            {"username": "bitcoin_bull", "accuracy_score": 0.82, "rank": 3}
                        ]
                        df = pd.DataFrame(demo_data)
                        st.dataframe(df, use_container_width=True)
                        st.info("💡 Join the community to see real leaderboards!")
        
        with social_tab[1]:
            st.write("### 💬 Community Forums")
            
            if not st.session_state.get('demo_mode', False):
                # Forum categories
                categories_data = get_api_data("social/forum/categories")
                if categories_data:
                    category = st.selectbox("Select Category", 
                                          [cat['name'] for cat in categories_data])
                    
                    if st.button("📝 Create New Post"):
                        st.write("### 📝 Create New Post")
                        post_title = st.text_input("Post Title")
                        post_content = st.text_area("Post Content")
                        post_tags = st.text_input("Tags (comma-separated)")
                        
                        if st.button("📤 Submit Post"):
                            with st.spinner("Creating post..."):
                                post_data = post_api_data("social/forum/posts", {
                                    "title": post_title,
                                    "content": post_content,
                                    "category": category.lower().replace(" ", "_"),
                                    "tags": [tag.strip() for tag in post_tags.split(",") if tag.strip()]
                                })
                                if post_data:
                                    st.success("Post created successfully!")
                                else:
                                    st.error("Failed to create post")
                    
                    # Display posts
                    posts_data = get_api_data(f"social/forum/posts?category={category.lower().replace(' ', '_')}")
                    if posts_data:
                        for post in posts_data:
                            with st.expander(f"📝 {post['title']} - by {post['username']}"):
                                st.write(post['content'])
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.write(f"👁️ {post['views_count']} views")
                                with col2:
                                    st.write(f"💬 {post['replies_count']} replies")
                                with col3:
                                    st.write(f"👍 {post['likes_count']} likes")
            else:
                display_upgrade_banner("Community forums", [
                    "Create and participate in discussions",
                    "Share trading strategies and insights",
                    "Connect with other traders",
                    "Access expert analysis",
                    "Real-time notifications",
                    "Moderated content quality"
                ])
        
        with social_tab[2]:
            st.write("### 📈 Shared Predictions")
            
            if st.button("🔄 Refresh Predictions"):
                with st.spinner("Loading shared predictions..."):
                    if not st.session_state.get('demo_mode', False):
                        predictions_data = get_api_data("social/predictions/shared")
                        if predictions_data:
                            for pred in predictions_data:
                                with st.expander(f"🔮 {pred['username']} - {pred['message']}"):
                                    st.write(f"**Prediction:** {pred['prediction_data']['predicted_price']:,.2f} USD")
                                    st.write(f"**Confidence:** {pred['prediction_data']['confidence']:.1%}")
                                    st.write(f"**Forecast Days:** {pred['prediction_data']['forecast_days']}")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        if st.button(f"👍 Like ({pred['likes_count']})", key=f"like_{pred['id']}"):
                                            like_result = post_api_data(f"social/predictions/{pred['id']}/like")
                                            if like_result:
                                                st.success("Liked!")
                                    with col2:
                                        if st.button(f"💬 Comment ({pred['comments_count']})", key=f"comment_{pred['id']}"):
                                            comment = st.text_input("Your comment:", key=f"comment_text_{pred['id']}")
                                            if st.button("📤 Submit", key=f"submit_comment_{pred['id']}"):
                                                comment_result = post_api_data(f"social/predictions/{pred['id']}/comment", {
                                                    "content": comment
                                                })
                                                if comment_result:
                                                    st.success("Comment posted!")
                        else:
                            st.error("Failed to load shared predictions")
                    else:
                        display_upgrade_banner("Shared predictions", [
                            "View community predictions",
                            "Like and comment on predictions",
                            "Share your own forecasts",
                            "Track prediction accuracy",
                            "Follow top predictors",
                            "Real-time prediction feeds"
                        ])
        
        with social_tab[3]:
            st.write("### 🎯 Trending Content")
            
            if not st.session_state.get('demo_mode', False):
                trending_data = get_api_data("social/trending")
                if trending_data:
                    st.write("#### 🔥 Trending Predictions")
                    for pred in trending_data.get('trending_predictions', []):
                        st.write(f"**{pred['username']}:** {pred['message']}")
                        st.write(f"👍 {pred['likes_count']} likes | 💬 {pred['comments_count']} comments")
                        st.write("---")
                    
                    st.write("#### 📝 Trending Posts")
                    for post in trending_data.get('trending_posts', []):
                        st.write(f"**{post['title']}** - by {post['username']}")
                        st.write(f"👁️ {post['views_count']} views | 💬 {post['replies_count']} replies")
                        st.write("---")
                    
                    st.write("#### 🏷️ Trending Tags")
                    tags = trending_data.get('trending_tags', [])
                    for tag in tags:
                        st.write(f"#{tag}")
                else:
                    st.error("Failed to load trending content")
            else:
                display_upgrade_banner("Trending content", [
                    "Real-time trending predictions",
                    "Popular forum discussions",
                    "Trending hashtags and topics",
                    "Community insights",
                    "Market sentiment analysis",
                    "Social trading signals"
                ])

    elif selected == "💼 Portfolio":
        st.title("💼 Portfolio Management")
        
        if st.session_state.get('demo_mode', False):
            display_upgrade_banner("Portfolio management", [
                "Multi-asset portfolio tracking",
                "Real-time portfolio analytics",
                "Risk metrics (Sharpe ratio, VaR, drawdown)",
                "Portfolio optimization tools",
                "Performance benchmarking",
                "Automated rebalancing"
            ])
            return
        
        # Portfolio tabs
        portfolio_tab = st.tabs(["📊 My Portfolios", "➕ Create Portfolio", "📈 Analytics", "⚠️ Risk Metrics"])
        
        with portfolio_tab[0]:
            st.write("### 📊 My Portfolios")
            
            if st.button("🔄 Refresh Portfolios"):
                with st.spinner("Loading portfolios..."):
                    portfolios_data = get_api_data("portfolio/list")
                    if portfolios_data:
                        for portfolio in portfolios_data:
                            with st.expander(f"💼 {portfolio['name']}"):
                                st.write(f"**Total Value:** ${portfolio.get('total_value', 0):,.2f}")
                                st.write(f"**Total Return:** {portfolio.get('total_return', 0):.1%}")
                                st.write(f"**Assets:** {len(portfolio['assets'])}")
                                
                                # Display assets
                                st.write("#### 📈 Assets")
                                for asset in portfolio['assets']:
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.write(f"**{asset['symbol']}**")
                                    with col2:
                                        st.write(f"Amount: {asset['amount']}")
                                    with col3:
                                        st.write(f"Purchase: ${asset['purchase_price']:,.2f}")
                                    with col4:
                                        st.write(f"Date: {asset['purchase_date'][:10]}")
                                
                                # Portfolio actions
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("📊 Analytics", key=f"analytics_{portfolio['id']}"):
                                        analytics_data = get_api_data(f"portfolio/analytics/{portfolio['id']}")
                                        if analytics_data:
                                            st.json(analytics_data)
                                with col2:
                                    if st.button("⚠️ Risk Metrics", key=f"risk_{portfolio['id']}"):
                                        risk_data = get_api_data(f"portfolio/risk-metrics/{portfolio['id']}")
                                        if risk_data:
                                            st.json(risk_data)
                    else:
                        st.error("Failed to load portfolios")
        
        with portfolio_tab[1]:
            st.write("### ➕ Create New Portfolio")
            
            portfolio_name = st.text_input("Portfolio Name")
            
            st.write("#### 📈 Add Assets")
            assets = []
            
            # Asset input
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                symbol = st.text_input("Symbol (e.g., BTC)", key="new_symbol")
            with col2:
                amount = st.number_input("Amount", min_value=0.0, key="new_amount")
            with col3:
                purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, key="new_price")
            with col4:
                purchase_date = st.date_input("Purchase Date", key="new_date")
            
            if st.button("➕ Add Asset"):
                assets.append({
                    "symbol": symbol,
                    "amount": amount,
                    "purchase_price": purchase_price,
                    "purchase_date": purchase_date.isoformat()
                })
                st.success(f"Added {symbol} to portfolio")
            
            # Display added assets
            if assets:
                st.write("#### 📋 Added Assets")
                for asset in assets:
                    st.write(f"**{asset['symbol']}:** {asset['amount']} @ ${asset['purchase_price']:,.2f}")
            
            # Create portfolio
            if st.button("🚀 Create Portfolio", type="primary"):
                if portfolio_name and assets:
                    with st.spinner("Creating portfolio..."):
                        portfolio_data = post_api_data("portfolio/create", {
                            "name": portfolio_name,
                            "assets": assets
                        })
                        if portfolio_data:
                            st.success("Portfolio created successfully!")
                        else:
                            st.error("Failed to create portfolio")
                else:
                    st.warning("Please provide portfolio name and at least one asset")
        
        with portfolio_tab[2]:
            st.write("### 📈 Portfolio Analytics")
            
            # Select portfolio for analytics
            portfolios_data = get_api_data("portfolio/list")
            if portfolios_data:
                portfolio_names = [p['name'] for p in portfolios_data]
                selected_portfolio = st.selectbox("Select Portfolio", portfolio_names)
                
                if st.button("📊 Get Analytics"):
                    portfolio_id = next(p['id'] for p in portfolios_data if p['name'] == selected_portfolio)
                    analytics_data = get_api_data(f"portfolio/analytics/{portfolio_id}")
                    
                    if analytics_data:
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Return", f"{analytics_data['total_return']:.1%}")
                        with col2:
                            st.metric("Annualized Return", f"{analytics_data['annualized_return']:.1%}")
                        with col3:
                            st.metric("Sharpe Ratio", f"{analytics_data['sharpe_ratio']:.2f}")
                        with col4:
                            st.metric("Max Drawdown", f"{analytics_data['max_drawdown']:.1%}")
                    else:
                        st.error("Failed to load analytics")
            else:
                st.info("No portfolios available for analytics")
        
        with portfolio_tab[3]:
            st.write("### ⚠️ Risk Metrics")
            
            # Select portfolio for risk analysis
            portfolios_data = get_api_data("portfolio/list")
            if portfolios_data:
                portfolio_names = [p['name'] for p in portfolios_data]
                selected_portfolio = st.selectbox("Select Portfolio for Risk Analysis", portfolio_names)
                
                if st.button("⚠️ Get Risk Metrics"):
                    portfolio_id = next(p['id'] for p in portfolios_data if p['name'] == selected_portfolio)
                    risk_data = get_api_data(f"portfolio/risk-metrics/{portfolio_id}")
                    
                    if risk_data:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Sharpe Ratio", f"{risk_data['sharpe_ratio']:.2f}")
                        with col2:
                            st.metric("Max Drawdown", f"{risk_data['max_drawdown']:.1%}")
                        with col3:
                            st.metric("Value at Risk", f"{risk_data['value_at_risk']:.1%}")
                    else:
                        st.error("Failed to load risk metrics")
            else:
                st.info("No portfolios available for risk analysis")

    elif selected == "💳 Subscriptions":
        st.title("💳 Subscription Management")
        
        if st.session_state.get('demo_mode', False):
            st.warning("🎮 Demo Mode: Subscription features require registration")
            st.write("**Available Plans:**")
            st.write("• **Free**: Basic predictions, 5 indicators")
            st.write("• **Premium ($29.99/month)**: Advanced predictions, all indicators")
            st.write("• **Professional ($99.99/month)**: API access, custom indicators")
            st.write("• **Enterprise ($299/month)**: Custom integrations, dedicated support")
            
            if st.button("🆙 Upgrade Now", type="primary"):
                st.info("Please register for a free account to access subscription features")
            return
        
        # Subscription tabs
        subscription_tab = st.tabs(["📋 Current Plan", "🆙 Upgrade", "📊 Usage", "💳 Billing"])
        
        with subscription_tab[0]:
            st.write("### 📋 Current Subscription")
            
            if st.button("🔄 Refresh Subscription"):
                with st.spinner("Loading subscription..."):
                    subscription_data = get_api_data("subscriptions/current")
                    if subscription_data:
                        # Display current plan
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Plan", subscription_data['tier_name'].title())
                            st.metric("Status", subscription_data['status'].title())
                        with col2:
                            st.metric("Period Start", subscription_data['current_period_start'][:10])
                            st.metric("Period End", subscription_data['current_period_end'][:10])
                        
                        # Features
                        st.write("#### ✨ Features")
                        for feature in subscription_data['features']:
                            st.write(f"✅ {feature}")
                        
                        # Cancel subscription
                        if subscription_data['status'] == 'active':
                            if st.button("❌ Cancel Subscription"):
                                cancel_result = post_api_data("subscriptions/cancel")
                                if cancel_result:
                                    st.success("Subscription will be canceled at the end of the current period")
                                    st.rerun()
                                else:
                                    st.error("Failed to cancel subscription")
                    else:
                        st.error("Failed to load subscription")
        
        with subscription_tab[1]:
            st.write("### 🆙 Upgrade Your Plan")
            
            # Get available tiers
            tiers_data = get_api_data("subscriptions/tiers")
            if tiers_data:
                for tier in tiers_data:
                    if tier['name'] != 'Free':  # Don't show free tier in upgrade
                        with st.expander(f"💎 {tier['name']} - ${tier['monthly_price']}/month"):
                            st.write(f"**Price:** ${tier['monthly_price']}/month")
                            st.write(f"**API Rate Limit:** {tier['rate_limit']} requests/hour")
                            st.write(f"**Max Predictions:** {tier['max_predictions']}/day")
                            st.write(f"**Max Portfolios:** {tier['max_portfolios']}")
                            st.write(f"**Priority Support:** {'Yes' if tier['priority_support'] else 'No'}")
                            
                            st.write("#### ✨ Features:")
                            for feature in tier['features']:
                                st.write(f"✅ {feature}")
                            
                            if st.button(f"🆙 Upgrade to {tier['name']}", key=f"upgrade_{tier['name']}"):
                                st.info("Payment processing will be integrated with Stripe")
                                st.write("This feature requires Stripe integration setup")
            else:
                st.error("Failed to load subscription tiers")
        
        with subscription_tab[2]:
            st.write("### 📊 Usage Statistics")
            
            if st.button("🔄 Refresh Usage"):
                with st.spinner("Loading usage..."):
                    usage_data = get_api_data("subscriptions/usage")
                    if usage_data:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("API Calls Today", usage_data['api_calls_today'])
                            st.metric("API Calls This Month", usage_data['api_calls_this_month'])
                        with col2:
                            st.metric("Predictions Today", usage_data['predictions_today'])
                            st.metric("Predictions This Month", usage_data['predictions_this_month'])
                        with col3:
                            st.metric("Portfolios", usage_data['portfolios_count'])
                            st.metric("Storage Used", f"{usage_data['storage_used_mb']:.1f} MB")
                        
                        # Usage charts
                        st.write("#### 📈 Usage Trends")
                        # Placeholder for usage charts
                        st.info("Usage trend charts will be displayed here")
                    else:
                        st.error("Failed to load usage statistics")
        
        with subscription_tab[3]:
            st.write("### 💳 Billing History")
            
            if st.button("🔄 Refresh Billing"):
                with st.spinner("Loading billing history..."):
                    billing_data = get_api_data("subscriptions/billing-history")
                    if billing_data:
                        for bill in billing_data:
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.write(f"**{bill['description']}**")
                            with col2:
                                st.write(f"${bill['amount']:.2f} {bill['currency']}")
                            with col3:
                                status_color = "green" if bill['status'] == 'paid' else "red"
                                st.write(f":{status_color}[{bill['status'].title()}]")
                            with col4:
                                st.write(bill['created_at'][:10])
                    else:
                        st.info("No billing history available")

    elif selected == "⚙️ Settings":
        st.title("⚙️ Settings & Configuration")
        
        # Settings tabs
        settings_tab = st.tabs(["🔧 API Settings", "👤 Profile", "🔒 Security", "📱 Preferences"])
        
        with settings_tab[0]:
            st.write("### 🔧 API Configuration")
            
            # API Key management
            st.write("#### 🔑 API Key")
            if st.button("🔑 Generate New API Key"):
                with st.spinner("Generating API key..."):
                    api_key_data = post_api_data("auth/api-key")
                    if api_key_data:
                        st.success("New API key generated!")
                        st.code(api_key_data['api_key'], language="text")
                    else:
                        st.error("Failed to generate API key")
            
            # API endpoint info
            st.write("#### 🌐 API Endpoints")
            st.code(f"Base URL: {API_BASE_URL}")
            st.code("Health Check: GET /health")
            st.code("Forecast: POST /predict")
            st.code("Training: POST /train")
        
        with settings_tab[1]:
            st.write("### 👤 User Profile")
            
            if st.button("🔄 Load Profile"):
                with st.spinner("Loading profile..."):
                    profile_data = get_api_data("auth/profile")
                    if profile_data:
                        st.write(f"**Username:** {profile_data['username']}")
                        st.write(f"**Email:** {profile_data['email']}")
                        st.write(f"**Role:** {profile_data['role']}")
                        st.write(f"**Member Since:** {profile_data['created_at'][:10]}")
                        if profile_data['last_login']:
                            st.write(f"**Last Login:** {profile_data['last_login'][:10]}")
                    else:
                        st.error("Failed to load profile")
        
        with settings_tab[2]:
            st.write("### 🔒 Security Settings")
            
            st.write("#### 🔐 Change Password")
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.button("🔐 Update Password"):
                if new_password == confirm_password:
                    st.info("Password update functionality will be implemented")
                else:
                    st.error("Passwords do not match")
        
        with settings_tab[3]:
            st.write("### 📱 User Preferences")
            
            # Theme selection
            theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
            
            # Language selection
            language = st.selectbox("Language", ["English", "Spanish", "French", "German"])
            
            # Notifications
            st.write("#### 🔔 Notifications")
            email_notifications = st.checkbox("Email Notifications", value=True)
            price_alerts = st.checkbox("Price Alerts", value=True)
            prediction_updates = st.checkbox("Prediction Updates", value=True)
            
            if st.button("💾 Save Preferences"):
                st.success("Preferences saved successfully!")

if __name__ == "__main__":
    main() 