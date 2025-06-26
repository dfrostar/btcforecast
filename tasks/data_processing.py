#!/usr/bin/env python3
"""
Data Processing Background Tasks
Automated data fetching, preprocessing, and validation
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from io import StringIO

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import current_task
from celery.utils.log import get_task_logger

# Import application modules
from data.data_loader import load_bitcoin_data, save_bitcoin_data
from data.feature_engineering import calculate_technical_indicators
from data.realtime_data import get_realtime_price
from config import get_settings
from error_handling import external_api_circuit_breaker

# Configure logging
logger = get_task_logger(__name__)
settings = get_settings()

@current_task.task(bind=True, name="data.processing.update_bitcoin_data")
def update_bitcoin_data(self, force_update: bool = False):
    """
    Update Bitcoin price data from multiple sources.
    
    Args:
        force_update: Force update even if recent data exists
    """
    task_id = self.request.id
    
    try:
        logger.info(f"Starting Bitcoin data update task {task_id}")
        
        # Check if update is needed
        if not force_update and _is_recent_data_available():
            logger.info("Recent data available, skipping update")
            return {
                "status": "skipped",
                "reason": "Recent data available",
                "task_id": task_id
            }
        
        # Fetch data from multiple sources
        data_sources = [
            ("yfinance", _fetch_yfinance_data),
            ("coingecko", _fetch_coingecko_data),
            ("binance", _fetch_binance_data)
        ]
        
        all_data = []
        for source_name, fetch_func in data_sources:
            try:
                data = fetch_func()
                if data is not None and not data.empty:
                    data['source'] = source_name
                    all_data.append(data)
                    logger.info(f"Successfully fetched data from {source_name}")
            except Exception as e:
                logger.error(f"Failed to fetch data from {source_name}: {e}")
        
        if not all_data:
            raise ValueError("No data could be fetched from any source")
        
        # Combine and clean data
        combined_data = _combine_data_sources(all_data)
        cleaned_data = _clean_and_validate_data(combined_data)
        
        # Calculate technical indicators
        data_with_features = calculate_technical_indicators(cleaned_data)
        
        # Save updated data
        save_bitcoin_data(data_with_features)
        
        # Update data quality metrics
        quality_metrics = _calculate_data_quality_metrics(data_with_features)
        
        result = {
            "status": "success",
            "data_points": len(data_with_features),
            "date_range": {
                "start": data_with_features.index[0].isoformat(),
                "end": data_with_features.index[-1].isoformat()
            },
            "quality_metrics": quality_metrics,
            "sources_used": [source for source, _ in data_sources if source in data_with_features.columns],
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Bitcoin data update completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Bitcoin data update failed: {e}")
        self.retry(countdown=300, max_retries=3)  # Retry after 5 minutes
        return {
            "status": "failed",
            "error": str(e),
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }

@current_task.task(bind=True, name="data.processing.validate_data_quality")
def validate_data_quality(self, data_source: str = "all"):
    """
    Validate data quality and identify anomalies.
    
    Args:
        data_source: Specific data source to validate
    """
    task_id = self.request.id
    
    try:
        logger.info(f"Starting data quality validation task {task_id}")
        
        # Load current data
        data = load_bitcoin_data()
        
        # Perform quality checks
        quality_report = _perform_quality_checks(data, data_source)
        
        # Identify and handle anomalies
        anomalies = _identify_anomalies(data)
        
        # Generate quality score
        quality_score = _calculate_quality_score(quality_report, anomalies)
        
        result = {
            "status": "success",
            "quality_score": quality_score,
            "quality_report": quality_report,
            "anomalies": anomalies,
            "recommendations": _generate_quality_recommendations(quality_report, anomalies),
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data quality validation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Data quality validation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }

@current_task.task(bind=True, name="data.processing.backfill_missing_data")
def backfill_missing_data(self, start_date: str, end_date: str):
    """
    Backfill missing data for a specific date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    task_id = self.request.id
    
    try:
        logger.info(f"Starting data backfill task {task_id} for {start_date} to {end_date}")
        
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Fetch historical data for the range
        historical_data = _fetch_historical_data(start_dt, end_dt)
        
        if historical_data.empty:
            raise ValueError(f"No data available for range {start_date} to {end_date}")
        
        # Load existing data
        existing_data = load_bitcoin_data()
        
        # Merge and deduplicate
        merged_data = _merge_and_deduplicate(existing_data, historical_data)
        
        # Save updated data
        save_bitcoin_data(merged_data)
        
        result = {
            "status": "success",
            "backfill_range": {
                "start": start_date,
                "end": end_date
            },
            "new_data_points": len(historical_data),
            "total_data_points": len(merged_data),
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data backfill completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Data backfill failed: {e}")
        self.retry(countdown=600, max_retries=2)  # Retry after 10 minutes
        return {
            "status": "failed",
            "error": str(e),
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }

@current_task.task(bind=True, name="data.processing.aggregate_data")
def aggregate_data(self, aggregation_level: str = "1H"):
    """
    Aggregate data to different time intervals.
    
    Args:
        aggregation_level: Time interval (1H, 4H, 1D, 1W)
    """
    task_id = self.request.id
    
    try:
        logger.info(f"Starting data aggregation task {task_id} for {aggregation_level}")
        
        # Load data
        data = load_bitcoin_data()
        
        # Perform aggregation
        aggregated_data = _aggregate_to_interval(data, aggregation_level)
        
        # Save aggregated data
        filename = f"btc_data_{aggregation_level.lower()}.csv"
        aggregated_data.to_csv(filename)
        
        result = {
            "status": "success",
            "aggregation_level": aggregation_level,
            "original_points": len(data),
            "aggregated_points": len(aggregated_data),
            "filename": filename,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Data aggregation completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Data aggregation failed: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat()
        }

def _is_recent_data_available() -> bool:
    """Check if recent data is available (less than 1 hour old)."""
    try:
        data_path = "btc_forecast.csv"
        if not os.path.exists(data_path):
            return False
        
        # Check file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(data_path))
        return datetime.utcnow() - mod_time < timedelta(hours=1)
    except Exception:
        return False

@external_api_circuit_breaker
def _fetch_yfinance_data() -> pd.DataFrame:
    """Fetch Bitcoin data from Yahoo Finance."""
    try:
        btc = yf.Ticker("BTC-USD")
        data = btc.history(period="7d", interval="1h")
        
        if data.empty:
            return pd.DataFrame()
        
        # Standardize column names
        data.columns = [col.lower() for col in data.columns]
        data = data.rename(columns={'close': 'price'})
        
        return data[['open', 'high', 'low', 'price', 'volume']]
    except Exception as e:
        logger.error(f"YFinance data fetch failed: {e}")
        return pd.DataFrame()

@external_api_circuit_breaker
def _fetch_coingecko_data() -> pd.DataFrame:
    """Fetch Bitcoin data from CoinGecko API."""
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "7",
            "interval": "hourly"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame
        prices = data['prices']
        df = pd.DataFrame(prices, columns=['timestamp', 'price'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Add OHLCV columns (simplified)
        df['open'] = df['price']
        df['high'] = df['price']
        df['low'] = df['price']
        df['volume'] = 0  # CoinGecko doesn't provide volume in this endpoint
        
        return df[['open', 'high', 'low', 'price', 'volume']]
    except Exception as e:
        logger.error(f"CoinGecko data fetch failed: {e}")
        return pd.DataFrame()

@external_api_circuit_breaker
def _fetch_binance_data() -> pd.DataFrame:
    """Fetch Bitcoin data from Binance API."""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "BTCUSDT",
            "interval": "1h",
            "limit": 168  # 7 days of hourly data
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert string values to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        return df[['open', 'high', 'low', 'close', 'volume']].rename(columns={'close': 'price'})
    except Exception as e:
        logger.error(f"Binance data fetch failed: {e}")
        return pd.DataFrame()

def _combine_data_sources(data_sources: List[pd.DataFrame]) -> pd.DataFrame:
    """Combine data from multiple sources with weighted averaging."""
    if len(data_sources) == 1:
        return data_sources[0]
    
    # Align timestamps
    combined_data = pd.concat(data_sources, axis=1, join='outer')
    
    # Weight sources by reliability (YFinance > Binance > CoinGecko)
    weights = {
        'yfinance': 0.5,
        'binance': 0.3,
        'coingecko': 0.2
    }
    
    # Calculate weighted average for price columns
    price_columns = ['open', 'high', 'low', 'price']
    for col in price_columns:
        if col in combined_data.columns:
            # Get all columns for this price type
            col_sources = [c for c in combined_data.columns if c.startswith(col)]
            if len(col_sources) > 1:
                # Calculate weighted average
                weighted_values = []
                for source_col in col_sources:
                    source_name = source_col.split('_')[-1] if '_' in source_col else 'unknown'
                    weight = weights.get(source_name, 0.1)
                    weighted_values.append(combined_data[source_col] * weight)
                
                combined_data[col] = sum(weighted_values)
    
    return combined_data[['open', 'high', 'low', 'price', 'volume']]

def _clean_and_validate_data(data: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate the data."""
    # Remove duplicates
    data = data.drop_duplicates()
    
    # Remove rows with missing values
    data = data.dropna()
    
    # Remove outliers (prices outside 3 standard deviations)
    for col in ['open', 'high', 'low', 'price']:
        if col in data.columns:
            mean_val = data[col].mean()
            std_val = data[col].std()
            data = data[
                (data[col] >= mean_val - 3 * std_val) &
                (data[col] <= mean_val + 3 * std_val)
            ]
    
    # Ensure price columns are in logical order
    data = data[
        (data['low'] <= data['open']) &
        (data['low'] <= data['high']) &
        (data['low'] <= data['price']) &
        (data['high'] >= data['open']) &
        (data['high'] >= data['high']) &
        (data['high'] >= data['price'])
    ]
    
    return data

def _calculate_data_quality_metrics(data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate data quality metrics."""
    return {
        "total_records": len(data),
        "missing_values": data.isnull().sum().to_dict(),
        "duplicates": data.duplicated().sum(),
        "date_range": {
            "start": data.index[0].isoformat(),
            "end": data.index[-1].isoformat(),
            "duration_days": (data.index[-1] - data.index[0]).days
        },
        "price_statistics": {
            "mean": data['price'].mean(),
            "std": data['price'].std(),
            "min": data['price'].min(),
            "max": data['price'].max()
        },
        "volume_statistics": {
            "mean": data['volume'].mean(),
            "std": data['volume'].std(),
            "total": data['volume'].sum()
        }
    }

def _perform_quality_checks(data: pd.DataFrame, data_source: str) -> Dict[str, Any]:
    """Perform comprehensive data quality checks."""
    checks = {
        "completeness": {
            "total_records": len(data),
            "missing_values": data.isnull().sum().to_dict(),
            "completeness_score": 1 - (data.isnull().sum().sum() / (len(data) * len(data.columns)))
        },
        "consistency": {
            "price_consistency": _check_price_consistency(data),
            "volume_consistency": _check_volume_consistency(data),
            "timestamp_consistency": _check_timestamp_consistency(data)
        },
        "accuracy": {
            "price_range_check": _check_price_range(data),
            "volume_range_check": _check_volume_range(data)
        }
    }
    
    return checks

def _identify_anomalies(data: pd.DataFrame) -> Dict[str, List]:
    """Identify data anomalies."""
    anomalies = {
        "price_spikes": [],
        "volume_spikes": [],
        "missing_periods": [],
        "duplicate_records": []
    }
    
    # Price spikes (more than 10% change in 1 hour)
    price_changes = data['price'].pct_change().abs()
    spike_indices = price_changes[price_changes > 0.1].index
    anomalies["price_spikes"] = [idx.isoformat() for idx in spike_indices]
    
    # Volume spikes (more than 3 standard deviations)
    volume_mean = data['volume'].mean()
    volume_std = data['volume'].std()
    volume_spike_indices = data[data['volume'] > volume_mean + 3 * volume_std].index
    anomalies["volume_spikes"] = [idx.isoformat() for idx in volume_spike_indices]
    
    # Missing periods (gaps larger than 2 hours)
    expected_timestamps = pd.date_range(data.index[0], data.index[-1], freq='1H')
    missing_timestamps = expected_timestamps.difference(data.index)
    anomalies["missing_periods"] = [ts.isoformat() for ts in missing_timestamps]
    
    # Duplicate records
    duplicate_indices = data[data.duplicated()].index
    anomalies["duplicate_records"] = [idx.isoformat() for idx in duplicate_indices]
    
    return anomalies

def _calculate_quality_score(quality_report: Dict, anomalies: Dict) -> float:
    """Calculate overall data quality score (0-100)."""
    score = 100
    
    # Deduct for missing values
    completeness_score = quality_report["completeness"]["completeness_score"]
    score *= completeness_score
    
    # Deduct for anomalies
    total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
    if total_anomalies > 0:
        score *= max(0.5, 1 - (total_anomalies / 100))  # Cap at 50% deduction
    
    return round(score, 2)

def _generate_quality_recommendations(quality_report: Dict, anomalies: Dict) -> List[str]:
    """Generate recommendations for improving data quality."""
    recommendations = []
    
    if quality_report["completeness"]["completeness_score"] < 0.95:
        recommendations.append("Data completeness is below 95%. Consider backfilling missing data.")
    
    if len(anomalies["price_spikes"]) > 0:
        recommendations.append(f"Found {len(anomalies['price_spikes'])} price spikes. Verify data accuracy.")
    
    if len(anomalies["missing_periods"]) > 0:
        recommendations.append(f"Found {len(anomalies['missing_periods'])} missing periods. Consider data backfill.")
    
    if len(anomalies["duplicate_records"]) > 0:
        recommendations.append(f"Found {len(anomalies['duplicate_records'])} duplicate records. Clean data.")
    
    return recommendations

def _fetch_historical_data(start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Fetch historical data for a specific date range."""
    # Use YFinance for historical data
    btc = yf.Ticker("BTC-USD")
    data = btc.history(start=start_date, end=end_date, interval="1h")
    
    if data.empty:
        return pd.DataFrame()
    
    # Standardize column names
    data.columns = [col.lower() for col in data.columns]
    data = data.rename(columns={'close': 'price'})
    
    return data[['open', 'high', 'low', 'price', 'volume']]

def _merge_and_deduplicate(existing_data: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
    """Merge new data with existing data and remove duplicates."""
    combined = pd.concat([existing_data, new_data])
    combined = combined.drop_duplicates()
    combined = combined.sort_index()
    
    return combined

def _aggregate_to_interval(data: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Aggregate data to specified time interval."""
    # Resample data to the specified interval
    resampled = data.resample(interval).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'price': 'last',
        'volume': 'sum'
    })
    
    return resampled.dropna()

# Helper functions for quality checks
def _check_price_consistency(data: pd.DataFrame) -> Dict[str, Any]:
    """Check price consistency."""
    return {
        "low_leq_open": (data['low'] <= data['open']).all(),
        "low_leq_high": (data['low'] <= data['high']).all(),
        "low_leq_close": (data['low'] <= data['price']).all(),
        "high_geq_open": (data['high'] >= data['open']).all(),
        "high_geq_close": (data['high'] >= data['price']).all()
    }

def _check_volume_consistency(data: pd.DataFrame) -> Dict[str, Any]:
    """Check volume consistency."""
    return {
        "non_negative": (data['volume'] >= 0).all(),
        "finite_values": data['volume'].notna().all()
    }

def _check_timestamp_consistency(data: pd.DataFrame) -> Dict[str, Any]:
    """Check timestamp consistency."""
    return {
        "sorted": data.index.is_monotonic_increasing,
        "no_duplicates": not data.index.duplicated().any()
    }

def _check_price_range(data: pd.DataFrame) -> Dict[str, Any]:
    """Check if prices are within reasonable range."""
    return {
        "min_price": data['price'].min(),
        "max_price": data['price'].max(),
        "reasonable_range": (data['price'].min() > 0) and (data['price'].max() < 1000000)
    }

def _check_volume_range(data: pd.DataFrame) -> Dict[str, Any]:
    """Check if volumes are within reasonable range."""
    return {
        "min_volume": data['volume'].min(),
        "max_volume": data['volume'].max(),
        "reasonable_range": (data['volume'].min() >= 0) and (data['volume'].max() < 1e12)
    } 