#!/usr/bin/env python3
"""
Enhanced BTC Training Agent with Comprehensive Monitoring
========================================================

This script provides enhanced training capabilities with:
- Real-time progress monitoring with tqdm
- Detailed logging of metrics and resources
- Email notifications on completion
- Training visualization
- Automatic model validation
- Resource usage tracking

Author: BTC Forecast Team
Date: 2024
"""

import pandas as pd
import numpy as np
from model import train_model, forecast_future, save_model_and_scaler, add_sentiment_feature, calculate_directional_accuracy
import ta
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import os
import time
import logging
import psutil
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import warnings
warnings.filterwarnings('ignore')

# --- Configuration ---
class TrainingConfig:
    """Configuration class for training parameters"""
    LOOKBACK = 30
    EPOCHS = 20
    BATCH_SIZE = 32
    TIMEFRAME = 30
    INDICATORS = ['RSI', 'MACD', 'Bollinger Bands', 'OBV', 'Ichimoku Cloud']
    VALIDATION_SPLIT = 0.1
    LEARNING_RATE = 0.001
    EARLY_STOPPING_PATIENCE = 5
    
    # Monitoring settings
    LOG_LEVEL = logging.INFO
    SAVE_PLOTS = True
    EMAIL_NOTIFICATIONS = False  # Set to True to enable email notifications
    
    # Email settings (configure if using notifications)
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_FROM = "your-email@gmail.com"
    EMAIL_TO = "your-email@gmail.com"
    EMAIL_PASSWORD = "your-app-password"

# --- Enhanced Logging Setup ---
def setup_logging():
    """Setup comprehensive logging for training monitoring"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/training_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=TrainingConfig.LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return log_file

# --- Data Loading with Progress ---
def fetch_btc_data(days=730):
    """Fetch BTC data with progress indication"""
    import requests
    
    logging.info(f"Fetching {days} days of BTC data...")
    
    with tqdm(total=1, desc="Fetching BTC data") as pbar:
        # Try CoinGecko API first
        url = f'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days={days}&interval=daily'
        
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()  # Raise an exception for bad status codes
            data = r.json()
            
            # Check if the response has the expected structure
            if 'prices' not in data or 'total_volumes' not in data:
                logging.warning(f"CoinGecko API response missing required fields. Available: {list(data.keys())}")
                raise ValueError("CoinGecko API response structure unexpected")
            
            prices = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
            prices['date'] = pd.to_datetime(prices['timestamp'], unit='ms')
            prices.set_index('date', inplace=True)
            prices['price'] = prices['price'].astype(float)
            
            # Add volume
            volumes = pd.DataFrame(data['total_volumes'], columns=['timestamp', 'volume'])
            volumes['date'] = pd.to_datetime(volumes['timestamp'], unit='ms')
            volumes.set_index('date', inplace=True)
            prices['volume'] = volumes['volume']
            
            logging.info("Successfully fetched data from CoinGecko API")
            
        except Exception as e:
            logging.warning(f"CoinGecko API failed: {e}. Trying yfinance as fallback...")
            
            # Fallback to yfinance
            try:
                import yfinance as yf
                btc = yf.Ticker("BTC-USD")
                prices = btc.history(period=f"{days}d")
                prices = prices[['Close', 'Volume']]
                prices.columns = ['price', 'volume']
                logging.info("Successfully fetched data from yfinance")
                
            except Exception as yf_error:
                logging.error(f"Both CoinGecko and yfinance failed. CoinGecko error: {e}, yfinance error: {yf_error}")
                raise Exception("All data sources failed. Please check your internet connection.")
        
        pbar.update(1)
    
    logging.info(f"Data fetched successfully. Shape: {prices.shape}")
    return prices

# --- Technical Indicators with Progress ---
def add_indicators(df, indicators):
    """Add technical indicators with progress tracking"""
    logging.info(f"Adding technical indicators: {', '.join(indicators)}")
    
    with tqdm(total=len(indicators), desc="Adding indicators") as pbar:
        if 'RSI' in indicators:
            df['RSI'] = ta.momentum.RSIIndicator(df['price']).rsi()
            pbar.update(1)
            
        if 'MACD' in indicators:
            macd = ta.trend.MACD(df['price'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            pbar.update(1)
            
        if 'Bollinger Bands' in indicators:
            bb = ta.volatility.BollingerBands(df['price'])
            df['BB_high'] = bb.bollinger_hband()
            df['BB_low'] = bb.bollinger_lband()
            pbar.update(1)
            
        if 'OBV' in indicators:
            df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['price'], df['volume']).on_balance_volume()
            pbar.update(1)
            
        if 'Ichimoku Cloud' in indicators:
            # For Ichimoku, we need high and low prices
            # Since we only have close price, we'll use it for both high and low
            ichimoku = ta.trend.IchimokuIndicator(high=df['price'], low=df['price'])
            df['Ichimoku_a'] = ichimoku.ichimoku_a()
            df['Ichimoku_b'] = ichimoku.ichimoku_b()
            pbar.update(1)
    
    logging.info("Technical indicators added successfully")
    return df

# --- Resource Monitoring ---
def get_system_info():
    """Get current system resource information"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'memory_available_gb': memory.available / (1024**3),
        'disk_percent': disk.percent,
        'disk_free_gb': disk.free / (1024**3)
    }

# --- Training Visualization ---
def plot_training_metrics(history, save_path="training_plots"):
    """Plot training metrics for monitoring"""
    os.makedirs(save_path, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Training Metrics', fontsize=16)
    
    # Loss
    axes[0, 0].plot(history.history['loss'], label='Training Loss')
    axes[0, 0].plot(history.history['val_loss'], label='Validation Loss')
    axes[0, 0].set_title('Model Loss')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Loss')
    axes[0, 0].legend()
    axes[0, 0].grid(True)
    
    # MAE
    axes[0, 1].plot(history.history['mae'], label='Training MAE')
    axes[0, 1].plot(history.history['val_mae'], label='Validation MAE')
    axes[0, 1].set_title('Mean Absolute Error')
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('MAE')
    axes[0, 1].legend()
    axes[0, 1].grid(True)
    
    # Learning rate (if available)
    if 'lr' in history.history:
        axes[1, 0].plot(history.history['lr'])
        axes[1, 0].set_title('Learning Rate')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Learning Rate')
        axes[1, 0].grid(True)
    
    # Resource usage
    axes[1, 1].text(0.1, 0.5, f"Final Training Loss: {history.history['loss'][-1]:.4f}\n"
                              f"Final Validation Loss: {history.history['val_loss'][-1]:.4f}\n"
                              f"Final Training MAE: {history.history['mae'][-1]:.4f}\n"
                              f"Final Validation MAE: {history.history['val_mae'][-1]:.4f}",
                    transform=axes[1, 1].transAxes, fontsize=12,
                    verticalalignment='center', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
    axes[1, 1].set_title('Training Summary')
    axes[1, 1].axis('off')
    
    plt.tight_layout()
    plt.savefig(f"{save_path}/training_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    logging.info(f"Training plots saved to {save_path}")

# --- Email Notification ---
def send_email_notification(subject, message):
    """Send email notification about training status"""
    if not TrainingConfig.EMAIL_NOTIFICATIONS:
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = TrainingConfig.EMAIL_FROM
        msg['To'] = TrainingConfig.EMAIL_TO
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP(TrainingConfig.SMTP_SERVER, TrainingConfig.SMTP_PORT)
        server.starttls()
        server.login(TrainingConfig.EMAIL_FROM, TrainingConfig.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(TrainingConfig.EMAIL_FROM, TrainingConfig.EMAIL_TO, text)
        server.quit()
        
        logging.info("Email notification sent successfully")
    except Exception as e:
        logging.error(f"Failed to send email notification: {e}")

# --- Enhanced Training Function ---
def train_with_monitoring():
    """Main training function with comprehensive monitoring"""
    start_time = time.time()
    log_file = setup_logging()
    
    logging.info("=" * 60)
    logging.info("BTC FORECAST TRAINING STARTED")
    logging.info("=" * 60)
    logging.info(f"Configuration: Lookback={TrainingConfig.LOOKBACK}, Epochs={TrainingConfig.EPOCHS}, Batch Size={TrainingConfig.BATCH_SIZE}")
    
    # Initial system check
    system_info = get_system_info()
    logging.info(f"System Resources - CPU: {system_info['cpu_percent']}%, Memory: {system_info['memory_percent']}%, Disk: {system_info['disk_percent']}%")
    
    try:
        # Step 1: Load and prepare data
        logging.info("Step 1: Loading BTC data...")
        df = fetch_btc_data(days=730)
        
        logging.info("Step 2: Adding technical indicators...")
        df = add_indicators(df, TrainingConfig.INDICATORS)
        
        logging.info("Step 3: Adding sentiment features...")
        df = add_sentiment_feature(df)
        
        # Prepare features
        feature_cols = [col for col in df.columns if col not in ['price', 'volume', 'BB_high', 'BB_low', 'MACD_signal', 'Ichimoku_a', 'Ichimoku_b'] and df[col].dtype != 'O']
        if 'sentiment' in df.columns:
            feature_cols.append('sentiment')
        
        logging.info(f"Features selected: {feature_cols}")
        
        # Data splitting
        train_df = df.dropna(subset=feature_cols + ['price'])
        split_idx = int(len(train_df) * 0.9)
        train_data = train_df.iloc[:split_idx]
        val_data = train_df.iloc[split_idx - TrainingConfig.LOOKBACK:]
        
        logging.info(f"Training data shape: {train_data.shape}, Validation data shape: {val_data.shape}")
        
        # Step 4: Train model with enhanced monitoring
        logging.info("Step 4: Training model with enhanced monitoring...")
        model, scaler, history = train_model(
            train_data, 
            feature_cols, 
            lookback=TrainingConfig.LOOKBACK, 
            epochs=TrainingConfig.EPOCHS, 
            batch_size=TrainingConfig.BATCH_SIZE, 
            log_csv_path='training_metrics.csv'
        )
        
        # Step 5: Evaluate model
        logging.info("Step 5: Evaluating model...")
        from model import prepare_data
        X_val, y_val, _ = prepare_data(val_data, feature_cols, lookback=TrainingConfig.LOOKBACK)
        y_pred = model.predict(X_val).flatten()
        
        # Inverse transform for evaluation
        dummy = np.zeros((len(y_pred), len(feature_cols) + 1))
        dummy[:, -1] = y_pred
        y_pred_inv = scaler.inverse_transform(dummy)[:, -1]
        dummy[:, -1] = y_val
        y_val_inv = scaler.inverse_transform(dummy)[:, -1]
        
        # Calculate metrics
        mae = mean_absolute_error(y_val_inv, y_pred_inv)
        mse = mean_squared_error(y_val_inv, y_pred_inv)
        rmse = np.sqrt(mse)
        r2 = r2_score(y_val_inv, y_pred_inv)
        dir_acc = calculate_directional_accuracy(y_val_inv, y_pred_inv)
        logging.info(f"Validation Metrics - MAE: {mae:.2f}, MSE: {mse:.2f}, RMSE: {rmse:.2f}, R²: {r2:.4f}, Directional Accuracy: {dir_acc:.2%}")
        
        # Step 6: Save model and generate forecasts
        logging.info("Step 6: Saving model and generating forecasts...")
        save_model_and_scaler(model, scaler)
        
        # Generate forecasts
        preds = forecast_future(train_df, model, scaler, feature_cols, lookback=TrainingConfig.LOOKBACK, steps=TrainingConfig.TIMEFRAME)
        future_dates = pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=TrainingConfig.TIMEFRAME)
        forecast_df = pd.DataFrame({'date': future_dates, 'forecast': preds})
        forecast_df.to_csv('btc_forecast.csv', index=False)
        
        # Step 7: Generate visualizations
        if TrainingConfig.SAVE_PLOTS:
            logging.info("Step 7: Generating training visualizations...")
            plot_training_metrics(history)
        
        # Step 8: Log results
        training_duration = time.time() - start_time
        final_system_info = get_system_info()
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': training_duration,
            'mae': mae,
            'mse': mse,
            'rmse': rmse,
            'r2': r2,
            'directional_accuracy': dir_acc,
            'epochs': TrainingConfig.EPOCHS,
            'lookback': TrainingConfig.LOOKBACK,
            'batch_size': TrainingConfig.BATCH_SIZE,
            'indicators': TrainingConfig.INDICATORS,
            'initial_cpu_percent': system_info['cpu_percent'],
            'final_cpu_percent': final_system_info['cpu_percent'],
            'initial_memory_percent': system_info['memory_percent'],
            'final_memory_percent': final_system_info['memory_percent']
        }
        
        # Save detailed results
        with open('training_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Update CSV log
        pd.DataFrame([results]).to_csv('btc_training_log.csv', mode='a', header=not os.path.exists('btc_training_log.csv'), index=False)
        
        logging.info("=" * 60)
        logging.info("TRAINING COMPLETED SUCCESSFULLY")
        logging.info("=" * 60)
        logging.info(f"Total training time: {training_duration:.2f} seconds ({training_duration/60:.2f} minutes)")
        logging.info(f"Model saved as: btc_model.pkl")
        logging.info(f"Scaler saved as: btc_scaler.pkl")
        logging.info(f"Forecast saved as: btc_forecast.csv")
        logging.info(f"Results saved as: training_results.json")
        logging.info(f"Log file: {log_file}")
        
        # Send success notification
        success_message = f"""
BTC Forecast Training Completed Successfully!

Training Duration: {training_duration:.2f} seconds
Validation MAE: {mae:.2f}
Validation R²: {r2:.4f}
Model saved: btc_model.pkl
Forecast generated: btc_forecast.csv

Check the log file for detailed information: {log_file}
        """
        send_email_notification("BTC Forecast Training Completed", success_message)
        
        return True
        
    except Exception as e:
        error_message = f"Training failed with error: {str(e)}"
        logging.error(error_message)
        
        # Send error notification
        send_email_notification("BTC Forecast Training Failed", error_message)
        
        return False

if __name__ == '__main__':
    print("🚀 Starting Enhanced BTC Training Agent...")
    print("📊 This version includes comprehensive monitoring and progress tracking")
    print("=" * 60)
    
    success = train_with_monitoring()
    
    if success:
        print("\n✅ Training completed successfully!")
        print("📁 Check the following files for results:")
        print("   - btc_model.pkl (trained model)")
        print("   - btc_scaler.pkl (data scaler)")
        print("   - btc_forecast.csv (predictions)")
        print("   - training_results.json (detailed results)")
        print("   - logs/ (training logs)")
    else:
        print("\n❌ Training failed. Check the logs for details.")
    
    print("\n🎯 Ready to run the application!") 