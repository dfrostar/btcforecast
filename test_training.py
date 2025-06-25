#!/usr/bin/env python3
"""
Test script to verify model training works correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.data_loader import load_btc_data
from data.feature_engineering import add_technical_indicators
from models.bilstm_attention import train_ensemble_model
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

def test_training():
    """Test the complete training pipeline."""
    try:
        print("=== Testing BTC Forecasting Model Training ===")
        
        # Step 1: Load data
        print("\n1. Loading BTC data...")
        df = load_btc_data(start="2020-01-01", end="2023-12-31")
        print(f"   Loaded {len(df)} rows of data")
        print(f"   Columns: {list(df.columns)}")
        
        if df.empty:
            print("   ERROR: No data loaded!")
            return False
        
        # Step 2: Add technical indicators
        print("\n2. Adding technical indicators...")
        df_featured = add_technical_indicators(df)
        feature_count = len([col for col in df_featured.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']])
        print(f"   Added {feature_count} technical indicators")
        print(f"   Total columns: {len(df_featured.columns)}")
        
        if feature_count == 0:
            print("   ERROR: No technical indicators added!")
            return False
        
        # Step 3: Train model
        print("\n3. Training ensemble model...")
        model, scaler, features, eval_results = train_ensemble_model(df_featured)
        print(f"   Model trained successfully!")
        print(f"   Features used: {len(features)}")
        print(f"   R² Score: {eval_results['r2_score']:.4f}")
        print(f"   MSE: {eval_results['mse']:.4f}")
        print(f"   MAE: {eval_results['mae']:.4f}")
        
        print("\n=== Training Test PASSED ===")
        return True
        
    except Exception as e:
        print(f"\n=== Training Test FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_training()
    sys.exit(0 if success else 1) 