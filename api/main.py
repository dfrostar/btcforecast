import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import numpy as np
import joblib
import time
from datetime import datetime, timedelta
import logging

# Custom modules
from data.data_loader import load_btc_data
from data.feature_engineering import add_technical_indicators
from models.bilstm_attention import (
    train_ensemble_model, 
    predict_with_ensemble,
    evaluate_ensemble_model,
    recursive_forecast,
    train_feature_forecasting_model
)
from monitoring import get_health_monitor
from config import get_config

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("api.main")

# --- Configuration ---
config = get_config()
health_monitor = get_health_monitor()

# --- Middleware for Request Monitoring ---
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time = time.time() - start_time
        
        # Record metrics
        success = 200 <= response.status_code < 400
        health_monitor.record_request(success, response_time)
        
        # Add response time header
        response.headers["X-Response-Time"] = str(response_time)
        
        return response

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Bitcoin Forecasting API v2.0",
    description="Advanced API for recursive Bitcoin price forecasting with feature generation.",
    version="2.0"
)

# Add middleware
app.add_middleware(MonitoringMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Variables ---
model = None
scaler = None
features = None
current_data = None

# --- Pydantic Models ---
class HealthCheck(BaseModel):
    status: str

class TrainResponse(BaseModel):
    message: str
    training_time: float
    r2_score: float
    mse: float
    mae: float

class ForecastResponse(BaseModel):
    history: list
    forecast: list

class ForecastRequest(BaseModel):
    days: int = 7
    confidence_level: float = 0.8

class TrainingRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    interval: str = "1d"

class FeatureForecastRequest(BaseModel):
    indicator: str
    days: int = 5

# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    """Load pre-trained model if available."""
    global model, scaler, features
    try:
        if os.path.exists("btc_model.pkl") and os.path.exists("btc_scaler.pkl"):
            # Load model with version compatibility handling
            try:
                model = joblib.load("btc_model.pkl")
                scaler_data = joblib.load("btc_scaler.pkl")
                scaler = scaler_data["scaler"]
                features = scaler_data["features"]
                logger.info("Pre-trained model loaded successfully.")
                
                # Validate model structure
                if not hasattr(model, 'predict'):
                    raise ValueError("Loaded model does not have predict method")
                if scaler is None or features is None:
                    raise ValueError("Scaler or features not properly loaded")
                    
                logger.info(f"Model loaded with {len(features)} features")
                
                # Update monitoring
                health_monitor.update_model_status(True)
                
            except Exception as model_error:
                logger.warning(f"Model loading failed due to version incompatibility: {model_error}")
                logger.info("Attempting to retrain model...")
                
                # Try to retrain the model
                try:
                    from data.data_loader import load_btc_data
                    df = load_btc_data(start="2020-01-01", end=None, interval="1d")
                    if not df.empty:
                        df_featured = add_technical_indicators(df)
                        model, scaler, features, eval_results = train_ensemble_model(df_featured)
                        logger.info("Model retrained successfully after compatibility issue.")
                        
                        # Update monitoring with accuracy
                        health_monitor.update_model_status(True, eval_results.get('r2_score'))
                    else:
                        logger.warning("Could not retrain model - no data available.")
                        health_monitor.update_model_status(False)
                except Exception as retrain_error:
                    logger.error(f"Model retraining failed: {retrain_error}")
                    logger.info("API will start without a loaded model.")
                    health_monitor.update_model_status(False)
                    
        else:
            logger.warning("Model or scaler not found on disk. Please train the model first.")
            health_monitor.update_model_status(False)
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.info("Pre-trained model not found. API will start without a loaded model.")
        health_monitor.update_model_status(False)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "BTC Price Forecasting API v2.0",
        "features": [
            "Recursive forecasting with feature generation",
            "Technical indicator forecasting",
            "Ensemble model training",
            "Real-time predictions"
        ],
        "endpoints": [
            "/train - Train the forecasting model",
            "/predict - Get price predictions",
            "/forecast/recursive - Advanced recursive forecasting",
            "/forecast/features - Forecast technical indicators",
            "/evaluate - Evaluate model performance",
            "/status - Check model status"
        ]
    }

@app.get("/health", response_model=HealthCheck, tags=["General"])
async def health_check():
    """Check if the API is running."""
    return {"status": "ok"}

@app.get("/health/detailed", tags=["General"])
async def detailed_health_check():
    """Get detailed health status including system metrics and API performance."""
    health_status = health_monitor.get_health_status()
    health_monitor.save_metrics()  # Save current metrics
    return health_status

@app.get("/health/metrics", tags=["General"])
async def get_metrics():
    """Get API performance metrics."""
    return health_monitor.load_metrics()

@app.post("/train", response_model=TrainResponse, tags=["Model"])
async def train_model_endpoint(request: TrainingRequest = TrainingRequest()):
    """Train the Bitcoin price prediction model."""
    global model, scaler, features, current_data
    
    start_time = time.time()
    
    try:
        # Load data
        logger.info("Fetching training data...")
        df = load_btc_data(
            start=request.start_date or "2014-01-01",
            end=request.end_date,
            interval=request.interval
        )
        
        if df.empty:
            raise HTTPException(status_code=400, detail="No data retrieved. Please check your date parameters.")
        
        logger.info(f"Loaded {len(df)} rows of data")
        
        # Add technical indicators
        logger.info("Adding technical indicators...")
        df_featured = add_technical_indicators(df)
        
        # Verify that features were added successfully
        feature_count = len([col for col in df_featured.columns if col not in ['Open', 'High', 'Low', 'Close', 'Volume']])
        logger.info(f"Added {feature_count} technical indicators")
        
        if feature_count == 0:
            raise HTTPException(status_code=500, detail="No technical indicators were added. Check feature engineering.")
        
        # Train the ensemble model
        logger.info("Training ensemble model...")
        model, scaler, features, eval_results = train_ensemble_model(df_featured)
        
        # Store current data for forecasting
        current_data = df_featured
        
        # Update monitoring with model status and accuracy
        health_monitor.update_model_status(True, eval_results.get('r2_score'))
        
        end_time = time.time()
        training_time = round(end_time - start_time, 2)
        logger.info(f"Model training completed. Score: {eval_results['r2_score']:.4f}, Time: {training_time}s")

        return {
            "message": "Model trained successfully",
            "training_time": training_time,
            **eval_results
        }
    except ValueError as e:
        logger.error(f"Value error during model training: {e}")
        raise HTTPException(status_code=400, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Error during model training: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@app.post("/predict", response_model=ForecastResponse, tags=["Model"])
async def predict_endpoint(request: ForecastRequest = ForecastRequest()):
    """Get price predictions using the trained model."""
    global model, scaler, features, current_data
    
    if model is None or scaler is None or features is None:
        raise HTTPException(status_code=400, detail="Model not trained. Please train the model first.")
    
    if current_data is None:
        raise HTTPException(status_code=400, detail="No current data available. Please train the model first.")
    
    try:
        # Use recursive forecasting for more accurate predictions
        predictions = predict_with_ensemble(
            model, scaler, features, current_data, 
            days_to_predict=request.days
        )
        
        # Prepare historical data for the response
        history_df = current_data.tail(30).reset_index()
        history_data = history_df[['Date', 'Close']].to_dict(orient='records')
        
        # Prepare forecast data
        forecast_data = predictions.to_dict(orient='records')

        logger.info(f"Forecast generated successfully. Predictions: {len(forecast_data)}")
        return {"history": history_data, "forecast": forecast_data}

    except Exception as e:
        logger.error(f"Error during prediction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forecast/recursive", response_model=ForecastResponse, tags=["Model"])
async def recursive_forecast_endpoint(request: ForecastRequest = ForecastRequest()):
    """Advanced recursive forecasting with feature generation."""
    global model, scaler, features, current_data
    
    if model is None or scaler is None or features is None:
        raise HTTPException(status_code=400, detail="Model not trained. Please train the model first.")
    
    if current_data is None:
        raise HTTPException(status_code=400, detail="No current data available. Please train the model first.")
    
    try:
        # Perform recursive forecasting
        predictions = recursive_forecast(
            model, scaler, features, current_data,
            days_to_predict=request.days
        )
        
        # Prepare historical data for the response
        history_df = current_data.tail(30).reset_index()
        history_data = history_df[['Date', 'Close']].to_dict(orient='records')
        
        # Prepare forecast data
        forecast_data = predictions.to_dict(orient='records')

        logger.info(f"Recursive forecast generated successfully. Predictions: {len(forecast_data)}")
        return {"history": history_data, "forecast": forecast_data}

    except Exception as e:
        logger.error(f"Error during recursive forecasting: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forecast/features")
async def feature_forecast_endpoint(request: FeatureForecastRequest):
    """Forecast specific technical indicators."""
    global current_data, features
    
    if current_data is None:
        raise HTTPException(status_code=400, detail="No current data available. Please train the model first.")
    
    if request.indicator not in features:
        raise HTTPException(status_code=400, detail=f"Indicator '{request.indicator}' not available. Available indicators: {features}")
    
    try:
        # Train feature forecasting models
        feature_models = train_feature_forecasting_model(current_data, features)
        
        if request.indicator not in feature_models:
            raise HTTPException(status_code=400, detail=f"Could not train forecasting model for {request.indicator}")
        
        # Get the model for this indicator
        indicator_model = feature_models[request.indicator]
        
        # Prepare input data
        last_data = current_data[['Close', 'Volume']].tail(10).values
        X_input = last_data.reshape(1, -1)
        
        # Make predictions
        predictions = []
        current_input = X_input.copy()
        
        for day in range(request.days):
            pred = indicator_model.predict(current_input)[0]
            predictions.append(pred)
            
            # Update input for next prediction (simplified)
            current_input = np.roll(current_input, -2)
            current_input[0, -2:] = [current_data['Close'].iloc[-1], current_data['Volume'].iloc[-1]]
        
        future_dates = pd.to_datetime(current_data.index[-1]) + pd.to_timedelta(np.arange(1, request.days + 1), 'D')
        
        return {
            "indicator": request.indicator,
            "predictions": [
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "value": float(pred)
                }
                for date, pred in zip(future_dates, predictions)
            ]
        }
        
    except Exception as e:
        logger.error(f"Error during feature forecasting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluate", tags=["Model"])
async def evaluate_endpoint():
    """Evaluate the current model performance."""
    global model, scaler, features, current_data
    
    if model is None or scaler is None or features is None:
        raise HTTPException(status_code=400, detail="Model not trained. Please train the model first.")
    
    if current_data is None:
        raise HTTPException(status_code=400, detail="No current data available. Please train the model first.")
    
    try:
        # Evaluate the model
        eval_results = evaluate_ensemble_model(model, scaler, features, current_data)
        
        return {
            "evaluation_results": eval_results,
            "model_info": {
                "features_used": len(features),
                "data_points": len(current_data),
                "last_training_date": current_data.index[-1].strftime("%Y-%m-%d")
            }
        }
        
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", tags=["Model"])
async def status_endpoint():
    """Check the current status of the model and system."""
    global model, scaler, features, current_data
    
    return {
        "model_loaded": model is not None,
        "scaler_loaded": scaler is not None,
        "features_available": len(features) if features else 0,
        "data_available": len(current_data) if current_data is not None else 0,
        "last_update": current_data.index[-1].strftime("%Y-%m-%d") if current_data is not None else None,
        "system_status": "Ready" if model is not None else "Needs Training"
    }

@app.get("/features", tags=["Model"])
async def features_endpoint():
    """Get information about available features."""
    global features
    
    if features is None:
        raise HTTPException(status_code=400, detail="No features available. Please train the model first.")
    
    return {
        "total_features": len(features),
        "feature_list": features,
        "feature_categories": {
            "technical_indicators": [f for f in features if any(indicator in f for indicator in ['RSI', 'MACD', 'BB', 'EMA', 'SMA'])],
            "volume_indicators": [f for f in features if 'Volume' in f],
            "momentum_indicators": [f for f in features if any(indicator in f for indicator in ['ROC', 'MOM', 'CCI'])],
            "volatility_indicators": [f for f in features if 'Volatility' in f]
        }
    } 