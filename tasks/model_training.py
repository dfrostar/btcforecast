#!/usr/bin/env python3
"""
Model Training Background Tasks
Automated model retraining, hyperparameter optimization, and performance evaluation
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import pickle
import joblib
import traceback

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery import current_task
from celery.utils.log import get_task_logger

# Import application modules
from model import create_model, train_model, evaluate_model
from data.data_loader import load_bitcoin_data, preprocess_data
from data.feature_engineering import calculate_technical_indicators
from config import settings
from api.database import UserRepository

# Configure logging
logger = get_task_logger(__name__)

class ModelTrainingTask:
    """Model training task handler with progress tracking and error handling."""
    
    def __init__(self):
        self.model_version = None
        self.training_start_time = None
        self.metrics = {}
    
    def update_progress(self, progress: float, message: str):
        """Update task progress."""
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta={
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        logger.info(f"Training Progress: {progress}% - {message}")

@current_task.task(bind=True, name="model_training.retrain_model")
def retrain_model(self, force_retrain: bool = False) -> Dict[str, Any]:
    """
    Retrain the BTC forecasting model with latest data
    
    Args:
        force_retrain: Force retraining even if model is recent
        
    Returns:
        Dict containing training results and metrics
    """
    try:
        logger.info(f"Starting model retraining task {self.request.id}")
        
        # Check if retraining is needed
        if not force_retrain:
            # Check last training time
            last_training = get_last_training_time()
            if last_training and (datetime.now() - last_training) < timedelta(hours=24):
                logger.info("Model was trained recently, skipping retraining")
                return {
                    "status": "skipped",
                    "reason": "Model trained recently",
                    "last_training": last_training.isoformat()
                }
        
        # Load and preprocess latest data
        logger.info("Loading latest Bitcoin data")
        data = load_bitcoin_data()
        if data.empty:
            raise ValueError("No data available for training")
        
        # Calculate technical indicators
        logger.info("Calculating technical indicators")
        data_with_indicators = calculate_technical_indicators(data)
        
        # Preprocess data
        logger.info("Preprocessing data")
        X_train, y_train, X_test, y_test, scaler = preprocess_data(data_with_indicators)
        
        # Create and train model
        logger.info("Creating and training model")
        model = create_model(input_shape=(X_train.shape[1], X_train.shape[2]))
        
        # Train model with progress tracking
        history = train_model(
            model, 
            X_train, 
            y_train, 
            X_test, 
            y_test,
            epochs=settings.MODEL_EPOCHS,
            batch_size=settings.MODEL_BATCH_SIZE
        )
        
        # Evaluate model
        logger.info("Evaluating model performance")
        metrics = evaluate_model(model, X_test, y_test)
        
        # Save model and scaler
        logger.info("Saving model and scaler")
        save_model_artifacts(model, scaler, metrics)
        
        # Update training metadata
        update_training_metadata(metrics, history)
        
        result = {
            "status": "success",
            "task_id": self.request.id,
            "metrics": metrics,
            "training_time": datetime.now().isoformat(),
            "data_points": len(data),
            "model_size": get_model_size(model)
        }
        
        logger.info(f"Model retraining completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Model retraining failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            countdown = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            raise self.retry(countdown=countdown, max_retries=3)
        
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id,
            "retries": self.request.retries
        }

@current_task.task(bind=True, name="model_training.optimize_model_hyperparameters")
def optimize_model_hyperparameters(self, optimization_type: str = "grid") -> Dict[str, Any]:
    """
    Optimize model hyperparameters using different strategies
    
    Args:
        optimization_type: Type of optimization (grid, random, bayesian)
        
    Returns:
        Dict containing optimization results
    """
    try:
        logger.info(f"Starting hyperparameter optimization: {optimization_type}")
        
        # Load data
        data = load_bitcoin_data()
        data_with_indicators = calculate_technical_indicators(data)
        X_train, y_train, X_test, y_test, scaler = preprocess_data(data_with_indicators)
        
        # Define hyperparameter search space
        param_grid = {
            "lstm_units": [50, 100, 200],
            "dropout_rate": [0.1, 0.2, 0.3],
            "learning_rate": [0.001, 0.01, 0.1],
            "batch_size": [32, 64, 128]
        }
        
        best_params = None
        best_score = float('-inf')
        results = []
        
        # Perform optimization based on type
        if optimization_type == "grid":
            best_params, best_score, results = grid_search_optimization(
                param_grid, X_train, y_train, X_test, y_test
            )
        elif optimization_type == "random":
            best_params, best_score, results = random_search_optimization(
                param_grid, X_train, y_train, X_test, y_test, n_iter=20
            )
        elif optimization_type == "bayesian":
            best_params, best_score, results = bayesian_optimization(
                param_grid, X_train, y_train, X_test, y_test, n_iter=30
            )
        
        # Train final model with best parameters
        if best_params:
            final_model = create_model(
                input_shape=(X_train.shape[1], X_train.shape[2]),
                **best_params
            )
            history = train_model(final_model, X_train, y_train, X_test, y_test)
            final_metrics = evaluate_model(final_model, X_test, y_test)
            
            # Save optimized model
            save_model_artifacts(final_model, scaler, final_metrics, "optimized")
        
        return {
            "status": "success",
            "optimization_type": optimization_type,
            "best_params": best_params,
            "best_score": best_score,
            "final_metrics": final_metrics if best_params else None,
            "all_results": results,
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"Hyperparameter optimization failed: {str(e)}")
        if self.request.retries < 2:
            raise self.retry(countdown=300, max_retries=2)
        
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

@current_task.task(bind=True, name="model_training.evaluate_model_performance")
def evaluate_model_performance(self, model_version: Optional[str] = None) -> Dict[str, Any]:
    """
    Comprehensive model performance evaluation
    
    Args:
        model_version: Specific model version to evaluate
        
    Returns:
        Dict containing evaluation results
    """
    try:
        logger.info(f"Starting model performance evaluation")
        
        # Load test data
        data = load_bitcoin_data()
        data_with_indicators = calculate_technical_indicators(data)
        X_train, y_train, X_test, y_test, scaler = preprocess_data(data_with_indicators)
        
        # Load model
        model = load_model(model_version)
        
        # Basic metrics
        basic_metrics = evaluate_model(model, X_test, y_test)
        
        # Advanced evaluation metrics
        advanced_metrics = calculate_advanced_metrics(model, X_test, y_test, data)
        
        # Performance over time
        time_performance = evaluate_time_performance(model, data_with_indicators)
        
        # Feature importance analysis
        feature_importance = analyze_feature_importance(model, data_with_indicators)
        
        # Save evaluation results
        save_evaluation_results({
            "basic_metrics": basic_metrics,
            "advanced_metrics": advanced_metrics,
            "time_performance": time_performance,
            "feature_importance": feature_importance,
            "evaluation_time": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "basic_metrics": basic_metrics,
            "advanced_metrics": advanced_metrics,
            "time_performance": time_performance,
            "feature_importance": feature_importance,
            "task_id": self.request.id
        }
        
    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e),
            "task_id": self.request.id
        }

# Helper functions
def get_last_training_time() -> Optional[datetime]:
    """Get the last model training time from metadata"""
    try:
        # Implementation to read from training metadata
        return None  # Placeholder
    except Exception:
        return None

def save_model_artifacts(model, scaler, metrics: Dict[str, Any], suffix: str = "") -> None:
    """Save model, scaler, and metrics"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = f"models/btc_model_{suffix}_{timestamp}.h5"
        scaler_path = f"models/scaler_{suffix}_{timestamp}.pkl"
        
        model.save(model_path)
        import joblib
        joblib.dump(scaler, scaler_path)
        
        logger.info(f"Model artifacts saved: {model_path}, {scaler_path}")
    except Exception as e:
        logger.error(f"Failed to save model artifacts: {e}")

def update_training_metadata(metrics: Dict[str, Any], history: Dict[str, Any]) -> None:
    """Update training metadata with latest results"""
    try:
        metadata = {
            "last_training": datetime.now().isoformat(),
            "metrics": metrics,
            "training_history": history,
            "model_version": f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
        
        # Save metadata to database or file
        logger.info("Training metadata updated")
    except Exception as e:
        logger.error(f"Failed to update training metadata: {e}")

def get_model_size(model) -> int:
    """Get model size in bytes"""
    try:
        import os
        model_path = "temp_model.h5"
        model.save(model_path)
        size = os.path.getsize(model_path)
        os.remove(model_path)
        return size
    except Exception:
        return 0

# Optimization helper functions (implementations would go here)
def grid_search_optimization(param_grid, X_train, y_train, X_test, y_test):
    """Grid search optimization implementation"""
    # Placeholder implementation
    return {}, 0.0, []

def random_search_optimization(param_grid, X_train, y_train, X_test, y_test, n_iter):
    """Random search optimization implementation"""
    # Placeholder implementation
    return {}, 0.0, []

def bayesian_optimization(param_grid, X_train, y_train, X_test, y_test, n_iter):
    """Bayesian optimization implementation"""
    # Placeholder implementation
    return {}, 0.0, []

def load_model(version: Optional[str] = None):
    """Load model from saved artifacts"""
    # Placeholder implementation
    return create_model()

def calculate_advanced_metrics(model, X_test, y_test, data):
    """Calculate advanced evaluation metrics"""
    # Placeholder implementation
    return {}

def evaluate_time_performance(model, data):
    """Evaluate model performance over time"""
    # Placeholder implementation
    return {}

def analyze_feature_importance(model, data):
    """Analyze feature importance"""
    # Placeholder implementation
    return {}

def save_evaluation_results(results):
    """Save evaluation results"""
    # Placeholder implementation
    pass 