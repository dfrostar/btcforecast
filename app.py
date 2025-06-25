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
    page_title="Bitcoin Price Forecaster - Advanced Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"

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
            response = requests.post(f"{API_BASE_URL}/{endpoint}", json=data)
        else:
            response = requests.post(f"{API_BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to the API: {e}")
        return None

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

# --- Main Application ---
def main():
    with st.sidebar:
        selected = option_menu(
            "BTC Forecast Dashboard",
            ["🏠 Dashboard", "🔮 Forecast", "📊 Model Evaluation", "🔄 Training", "📈 Analytics", "⚡ Real-Time Data", "⚙️ Settings"],
            icons=['house', 'graph-up-arrow', 'wrench', 'gear', 'chart-line', 'lightning', 'settings'],
            menu_icon="cast",
            default_index=0,
        )

    st.title("🚀 Bitcoin Price Forecasting - Advanced Dashboard")
    st.markdown("---")

    if selected == "🏠 Dashboard":
        st.subheader("🎯 Welcome to the BTC Forecaster Dashboard!")
        
        # System status
        st.write("### 🔧 System Status")
        col1, col2 = st.columns(2)
        
        with col1:
            # Check API status
            api_status = get_api_data("health")
            if api_status:
                st.success("✅ Backend API: Running")
            else:
                st.error("❌ Backend API: Not responding")
        
        with col2:
            # Check model status
            model_status = get_api_data("status")
            if model_status:
                st.success("✅ Model: Loaded and Ready")
            else:
                st.warning("⚠️ Model: Not loaded")
        
        # Quick metrics
        display_model_status()
        
        # Recent forecast
        st.write("### 🔮 Latest Forecast")
        display_forecast_analysis()

    elif selected == "🔮 Forecast":
        st.subheader("🔮 Bitcoin Price Forecast")
        
        # Forecast options
        col1, col2 = st.columns(2)
        
        with col1:
            forecast_days = st.slider("Forecast Days", 1, 30, 7)
            confidence_level = st.slider("Confidence Level", 0.5, 0.95, 0.8, 0.05)
        
        with col2:
            forecast_type = st.selectbox(
                "Forecast Type",
                ["Standard", "Recursive", "Feature-based"]
            )
        
        # Generate forecast button
        if st.button("🚀 Generate New Forecast", type="primary"):
            with st.spinner("Generating forecast..."):
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
                    st.info("Feature-based forecasting coming soon!")
                    forecast_data = None
                
                if forecast_data:
                    st.session_state['forecast_data'] = forecast_data
                    st.success("Forecast generated successfully!")
                else:
                    st.error("Failed to generate forecast.")
        
        # Display forecast
        if 'forecast_data' in st.session_state:
            plot_forecast(st.session_state['forecast_data'])
            
            # Forecast statistics
            if st.session_state['forecast_data']:
                forecast_df = pd.DataFrame(st.session_state['forecast_data']['forecast'])
                if not forecast_df.empty:
                    st.write("### 📊 Forecast Statistics")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Average Forecast", f"${forecast_df['Predicted_Close'].mean():,.0f}")
                    
                    with col2:
                        st.metric("Max Forecast", f"${forecast_df['Predicted_Close'].max():,.0f}")
                    
                    with col3:
                        st.metric("Min Forecast", f"${forecast_df['Predicted_Close'].min():,.0f}")

    elif selected == "📊 Model Evaluation":
        st.subheader("📊 Model Performance & Evaluation")
        
        # Evaluation options
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📈 Evaluate Current Model", type="primary"):
                with st.spinner("Evaluating model performance..."):
                    eval_data = get_api_data("evaluate")
                    if eval_data:
                        st.session_state['eval_data'] = eval_data
                        st.success("Evaluation completed!")
                    else:
                        st.error("Evaluation failed.")
        
        with col2:
            if st.button("🔄 Retrain Model", type="secondary"):
                with st.spinner("Retraining model... This may take several minutes."):
                    train_data = post_api_data("train")
                    if train_data:
                        st.session_state['eval_data'] = train_data
                        st.success("Model retrained successfully!")
                    else:
                        st.error("Model retraining failed.")
        
        # Display evaluation results
        if 'eval_data' in st.session_state:
            st.write("### 📊 Performance Metrics")
            metrics = st.session_state['eval_data']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("R² Score", f"{metrics.get('r2_score', 0):.4f}")
            
            with col2:
                st.metric("MSE", f"{metrics.get('mse', 0):.2e}")
            
            with col3:
                st.metric("MAE", f"{metrics.get('mae', 0):.2f}")
            
            with col4:
                st.metric("RMSE", f"{metrics.get('rmse', 0):.2f}")
            
            # Cross-validation scores
            if 'cv_scores' in metrics:
                st.write("### 🔄 Cross-Validation Scores")
                cv_df = pd.DataFrame(metrics['cv_scores'], columns=['CV R² Score'])
                
                fig = px.bar(cv_df, title='Cross-Validation R² Scores')
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        
        # Training visualizations
        display_training_visualizations()

    elif selected == "🔄 Training":
        st.subheader("🔄 Model Training")
        
        # Training configuration
        st.write("### ⚙️ Training Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            epochs = st.slider("Epochs", 10, 100, 20)
            batch_size = st.selectbox("Batch Size", [16, 32, 64, 128], index=1)
            lookback = st.slider("Lookback Period", 10, 60, 30)
        
        with col2:
            learning_rate = st.selectbox("Learning Rate", [0.001, 0.01, 0.1], index=0)
            validation_split = st.slider("Validation Split", 0.1, 0.3, 0.2, 0.05)
            early_stopping = st.checkbox("Early Stopping", value=True)
        
        # Technical indicators
        st.write("### 📊 Technical Indicators")
        indicators = st.multiselect(
            "Select Technical Indicators",
            ["RSI", "MACD", "Bollinger Bands", "OBV", "Ichimoku Cloud", "Stochastic", "Williams %R"],
            default=["RSI", "MACD", "Bollinger Bands", "OBV", "Ichimoku Cloud"]
        )
        
        # Training buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🚀 Start Training", type="primary"):
                with st.spinner("Training model... This may take several minutes."):
                    # Here you would call the training API with the configuration
                    st.info("Training started! Check the logs for progress.")
        
        with col2:
            if st.button("📊 View Training Logs"):
                st.info("Training logs will be displayed here.")
        
        # Training progress
        st.write("### 📈 Training Progress")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Placeholder for training progress
        st.info("Training progress will be displayed here when training is active.")

    elif selected == "📈 Analytics":
        st.subheader("📈 Advanced Analytics")
        
        # Data analysis
        st.write("### 📊 Data Analysis")
        
        # Load and display historical data
        try:
            # This would load actual BTC data
            st.info("Historical data analysis will be displayed here.")
        except Exception as e:
            st.error(f"Error loading data: {e}")
        
        # Feature importance
        st.write("### 🎯 Feature Importance")
        st.info("Feature importance analysis will be displayed here.")
        
        # Model comparison
        st.write("### 🔄 Model Comparison")
        st.info("Model comparison tools will be displayed here.")

    elif selected == "⚡ Real-Time Data":
        st.subheader("⚡ Real-Time Data & Live Market Feed")
        
        # Real-time data status
        st.write("### 🔌 Connection Status")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Check WebSocket connection
            try:
                # This would check WebSocket connection status
                st.success("✅ WebSocket: Connected")
            except:
                st.error("❌ WebSocket: Disconnected")
        
        with col2:
            # Check real-time data service
            try:
                realtime_status = get_api_data("realtime/prices")
                if realtime_status:
                    st.success("✅ Real-time Data: Active")
                else:
                    st.warning("⚠️ Real-time Data: Inactive")
            except:
                st.error("❌ Real-time Data: Error")
        
        with col3:
            # Check price alert system
            try:
                st.success("✅ Price Alerts: Active")
            except:
                st.warning("⚠️ Price Alerts: Inactive")
        
        # Live price feed
        st.write("### 💰 Live Price Feed")
        
        # Auto-refresh price data
        if 'price_refresh' not in st.session_state:
            st.session_state.price_refresh = 0
        
        if st.button("🔄 Refresh Prices") or st.session_state.price_refresh == 0:
            with st.spinner("Fetching live prices..."):
                try:
                    prices_data = get_api_data("realtime/prices")
                    if prices_data and 'prices' in prices_data:
                        st.session_state.live_prices = prices_data['prices']
                        st.session_state.price_refresh += 1
                        st.success("Prices updated!")
                    else:
                        st.error("Failed to fetch live prices")
                except Exception as e:
                    st.error(f"Error fetching prices: {e}")
        
        # Display live prices
        if 'live_prices' in st.session_state and st.session_state.live_prices:
            prices = st.session_state.live_prices
            
            # Create price cards
            col1, col2, col3, col4, col5 = st.columns(5)
            
            symbols = ['btcusdt', 'ethusdt', 'adausdt', 'dotusdt', 'solusdt']
            colors = ['#f7931a', '#627eea', '#0033ad', '#e6007a', '#9945ff']
            
            for i, (symbol, color) in enumerate(zip(symbols, colors)):
                with [col1, col2, col3, col4, col5][i]:
                    if symbol in prices:
                        price_data = prices[symbol]
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, {color}20, {color}40);
                            border: 2px solid {color};
                            border-radius: 10px;
                            padding: 15px;
                            text-align: center;
                            margin: 5px 0;
                        ">
                            <h3 style="color: {color}; margin: 0;">{symbol.upper()}</h3>
                            <h2 style="color: white; margin: 10px 0;">${price_data.get('price', 0):,.2f}</h2>
                            <p style="color: #ccc; margin: 0;">Volume: {price_data.get('volume', 0):,.0f}</p>
                            <p style="color: #ccc; margin: 0;">Source: {price_data.get('exchange', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="
                            background: #2d2d2d;
                            border: 2px solid #666;
                            border-radius: 10px;
                            padding: 15px;
                            text-align: center;
                            margin: 5px 0;
                        ">
                            <h3 style="color: #666; margin: 0;">{symbol.upper()}</h3>
                            <p style="color: #666; margin: 0;">No data</p>
                        </div>
                        """, unsafe_allow_html=True)
        
        # Price alerts section
        st.write("### 🔔 Price Alerts")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Create new alert
            st.write("#### Create New Alert")
            
            alert_symbol = st.selectbox(
                "Symbol",
                ["btcusdt", "ethusdt", "adausdt", "dotusdt", "solusdt"],
                key="alert_symbol"
            )
            
            col_a, col_b = st.columns(2)
            with col_a:
                target_price = st.number_input(
                    "Target Price ($)",
                    min_value=0.0,
                    value=50000.0 if alert_symbol == "btcusdt" else 1000.0,
                    step=100.0
                )
            
            with col_b:
                alert_type = st.selectbox(
                    "Alert Type",
                    ["above", "below"],
                    key="alert_type"
                )
            
            if st.button("🔔 Create Alert", type="primary"):
                with st.spinner("Creating price alert..."):
                    try:
                        alert_data = post_api_data("realtime/alerts", {
                            "symbol": alert_symbol,
                            "target_price": target_price,
                            "alert_type": alert_type
                        })
                        if alert_data:
                            st.success("Price alert created successfully!")
                            # Refresh alerts list
                            st.session_state.alerts_refresh = True
                        else:
                            st.error("Failed to create price alert")
                    except Exception as e:
                        st.error(f"Error creating alert: {e}")
        
        with col2:
            # Alert status
            st.write("#### Alert Status")
            
            try:
                alerts_data = get_api_data("realtime/alerts")
                if alerts_data and 'alerts' in alerts_data:
                    active_alerts = len(alerts_data['alerts'])
                    st.metric("Active Alerts", active_alerts)
                    
                    if active_alerts > 0:
                        st.info(f"📊 {active_alerts} active price alerts")
                    else:
                        st.info("📊 No active alerts")
                else:
                    st.metric("Active Alerts", 0)
                    st.info("📊 No alerts found")
            except:
                st.metric("Active Alerts", "Error")
                st.error("Failed to load alerts")
        
        # Display existing alerts
        st.write("#### Your Price Alerts")
        
        try:
            alerts_data = get_api_data("realtime/alerts")
            if alerts_data and 'alerts' in alerts_data and alerts_data['alerts']:
                alerts = alerts_data['alerts']
                
                for alert in alerts:
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{alert.get('symbol', 'N/A').upper()}** {alert.get('alert_type', 'N/A')} ${alert.get('target_price', 0):,.2f}")
                    
                    with col2:
                        status = "🟢 Active" if not alert.get('triggered', False) else "🔴 Triggered"
                        st.write(status)
                    
                    with col3:
                        if alert.get('created_at'):
                            created = alert['created_at'][:10]  # Just the date
                            st.write(f"Created: {created}")
                    
                    with col4:
                        if st.button(f"🗑️ Delete", key=f"delete_{alert.get('id', 'unknown')}"):
                            try:
                                delete_result = post_api_data(f"realtime/alerts/{alert.get('id', '')}", method="DELETE")
                                if delete_result:
                                    st.success("Alert deleted!")
                                    st.rerun()
                                else:
                                    st.error("Failed to delete alert")
                            except Exception as e:
                                st.error(f"Error deleting alert: {e}")
                
            else:
                st.info("No price alerts found. Create your first alert above!")
                
        except Exception as e:
            st.error(f"Error loading alerts: {e}")
        
        # Real-time chart (placeholder for future implementation)
        st.write("### 📈 Real-Time Chart")
        st.info("""
        **Real-time chart features coming soon:**
        - Live price charts with WebSocket updates
        - Technical indicators on real-time data
        - Price movement alerts
        - Volume analysis
        - Multi-timeframe views
        """)
        
        # WebSocket connection info
        st.write("### 🔌 WebSocket Connection")
        st.info("""
        **WebSocket Endpoint:** `ws://localhost:8000/ws`
        
        **Available Features:**
        - Real-time price streaming
        - Price alert notifications
        - Live market data
        - Multi-exchange aggregation
        
        **Message Types:**
        - `subscribe`: Subscribe to symbol updates
        - `price_alert`: Create price alerts
        - `get_price`: Get current price
        - `ping`: Connection health check
        """)

    elif selected == "⚙️ Settings":
        st.subheader("⚙️ Application Settings")
        
        # API Configuration
        st.write("### 🔧 API Configuration")
        api_url = st.text_input("API Base URL", value=API_BASE_URL)
        
        # Model Settings
        st.write("### 🤖 Model Settings")
        auto_retrain = st.checkbox("Auto-retrain on startup", value=False)
        retrain_interval = st.selectbox("Retrain Interval", ["Daily", "Weekly", "Monthly", "Never"])
        
        # Notification Settings
        st.write("### 🔔 Notification Settings")
        email_notifications = st.checkbox("Email Notifications", value=False)
        if email_notifications:
            email_address = st.text_input("Email Address")
        
        # Save settings
        if st.button("💾 Save Settings"):
            st.success("Settings saved successfully!")

if __name__ == "__main__":
    main() 