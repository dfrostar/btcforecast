import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import joblib
import time
from datetime import datetime, timedelta
import logging
import json
from fastapi import WebSocket

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

# Security and database modules
from api.auth import (
    User, UserCreate, UserLogin, Token, get_current_user, 
    require_premium, require_admin, authenticate_user, create_user,
    generate_user_api_key, verify_api_key
)
from api.rate_limiter import rate_limit_middleware, get_rate_limit_status
from api.database import (
    UserRepository, AuditRepository, PredictionRepository, 
    ModelRepository, MetricsRepository
)

# Real-time data integration (Competitive Edge Feature)
from api.websocket import (
    websocket_endpoint, get_current_prices, create_price_alert,
    get_user_alerts, delete_price_alert, PriceAlertRequest, PriceAlertResponse
)
from data.realtime_data import start_realtime_data, stop_realtime_data

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger("api.main")

# --- Configuration ---
config = get_config()
health_monitor = get_health_monitor()

# --- Middleware for Request Monitoring and Rate Limiting ---
class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get client information for audit logging
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        # Extract user information if available
        user_id = None
        user_role = "anonymous"
        
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            user = verify_api_key(api_key)
            if user:
                user_id = user.id if hasattr(user, 'id') else None
                user_role = user.role
                request.state.user_id = user_id
                request.state.user_role = user_role
        
        # Process request
        try:
            response = await call_next(request)
            response_status = response.status_code
        except Exception as e:
            response_status = 500
            raise e
        finally:
            # Calculate response time
            response_time = time.time() - start_time
            
            # Record metrics
            success = 200 <= response_status < 400
            health_monitor.record_request(success, response_time)
            
            # Log API request for audit
            try:
                request_data = None
                if request.method in ["POST", "PUT", "PATCH"]:
                    body = await request.body()
                    if body:
                        request_data = json.loads(body.decode())
                
                AuditRepository.log_api_request(
                    user_id=user_id,
                    endpoint=str(request.url.path),
                    method=request.method,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    request_data=request_data,
                    response_status=response_status,
                    response_time_ms=int(response_time * 1000)
                )
            except Exception as audit_error:
                logger.warning(f"Failed to log audit: {audit_error}")
            
            # Add response time header
            response.headers["X-Response-Time"] = str(response_time)
        
        return response

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Bitcoin Forecasting API v3.0",
    description="Advanced API for recursive Bitcoin price forecasting with authentication, rate limiting, and comprehensive monitoring.",
    version="3.0",
    docs_url="/docs" if config.enable_docs else None,
    redoc_url="/redoc" if config.enable_docs else None
)

# Add middleware
app.add_middleware(MonitoringMiddleware)
app.add_middleware(rate_limit_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
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
    confidence_intervals: Optional[list] = None

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

class UserProfile(BaseModel):
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

class APIKeyResponse(BaseModel):
    api_key: str
    message: str

# --- API Endpoints ---

# Authentication endpoints
@app.post("/auth/register", response_model=UserProfile, tags=["Authentication"])
async def register_user(user_data: UserCreate):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = UserRepository.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        existing_email = UserRepository.get_user_by_email(user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user in database
        from api.auth import hash_password
        hashed_password = hash_password(user_data.password)
        user = UserRepository.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role
        )
        
        return UserProfile(**user)
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login_user(user_credentials: UserLogin):
    """Login user and return JWT tokens."""
    try:
        user = authenticate_user(user_credentials.username, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update last login
        UserRepository.update_last_login(user_credentials.username)
        
        # Create tokens
        from api.auth import create_access_token, create_refresh_token
        access_token = create_access_token(data={"sub": user.username, "role": user.role})
        refresh_token = create_refresh_token(data={"sub": user.username, "role": user.role})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=30 * 60  # 30 minutes
        )
    except Exception as e:
        logger.error(f"User login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.post("/auth/api-key", response_model=APIKeyResponse, tags=["Authentication"])
async def generate_api_key(current_user: User = Depends(get_current_user)):
    """Generate an API key for the authenticated user."""
    try:
        api_key = generate_user_api_key(current_user.username)
        UserRepository.update_api_key(current_user.username, api_key)
        
        return APIKeyResponse(
            api_key=api_key,
            message="API key generated successfully"
        )
    except Exception as e:
        logger.error(f"API key generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate API key"
        )

@app.get("/auth/profile", response_model=UserProfile, tags=["Authentication"])
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    user_data = UserRepository.get_user_by_username(current_user.username)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserProfile(**user_data)

# Admin endpoints
@app.get("/admin/users", tags=["Admin"])
async def get_all_users(current_user: User = Depends(require_admin)):
    """Get all users (admin only)."""
    users = UserRepository.get_all_users()
    return {"users": users}

@app.get("/admin/audit-log", tags=["Admin"])
async def get_audit_log(
    limit: int = 100,
    current_user: User = Depends(require_admin)
):
    """Get system audit log (admin only)."""
    audit_log = AuditRepository.get_system_audit_log(limit)
    return {"audit_log": audit_log}

@app.get("/admin/metrics", tags=["Admin"])
async def get_admin_metrics(
    hours: int = 24,
    current_user: User = Depends(require_admin)
):
    """Get system metrics (admin only)."""
    metrics = MetricsRepository.get_metrics_summary(hours)
    return {"metrics": metrics}

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
async def train_model_endpoint(
    request: TrainingRequest = TrainingRequest(),
    current_user: User = Depends(get_current_user)
):
    """Train the forecasting model with specified parameters."""
    try:
        logger.info(f"Training request from user {current_user.username}")
        
        # Load and prepare data
        df = load_btc_data(
            start=request.start_date or "2020-01-01",
            end=request.end_date,
            interval=request.interval
        )
        
        if df.empty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data available for the specified date range"
            )
        
        # Add technical indicators
        df_featured = add_technical_indicators(df)
        
        # Train model
        start_time = time.time()
        model_result, scaler_result, features_result, eval_results = train_ensemble_model(df_featured)
        training_time = time.time() - start_time
        
        # Update global variables
        global model, scaler, features
        model = model_result
        scaler = scaler_result
        features = features_result
        
        # Log training session to database
        try:
            ModelRepository.log_training_session(
                model_version=f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                r2_score=eval_results.get('r2_score', 0.0),
                mae_score=eval_results.get('mae', 0.0),
                rmse_score=eval_results.get('rmse', 0.0),
                training_time_seconds=training_time,
                model_size_kb=int(os.path.getsize("btc_model.pkl") / 1024) if os.path.exists("btc_model.pkl") else 0,
                features_used=features_result,
                hyperparameters={"interval": request.interval}
            )
        except Exception as db_error:
            logger.warning(f"Failed to log training session: {db_error}")
        
        # Update health monitor
        health_monitor.update_model_status(True, eval_results.get('r2_score'))
        
        return TrainResponse(
            message="Model trained successfully",
            training_time=training_time,
            r2_score=eval_results.get('r2_score', 0.0),
            mse=eval_results.get('mse', 0.0),
            mae=eval_results.get('mae', 0.0)
        )
        
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}"
        )

@app.post("/predict", response_model=ForecastResponse, tags=["Model"])
async def predict_endpoint(
    request: ForecastRequest = ForecastRequest(),
    current_user: User = Depends(get_current_user)
):
    """Get Bitcoin price predictions."""
    try:
        if model is None or scaler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not trained. Please train the model first."
            )
        
        # Load current data
        df = load_btc_data(start="2020-01-01", end=None, interval="1d")
        df_featured = add_technical_indicators(df)
        
        # Make prediction
        predictions = predict_with_ensemble(model, scaler, features, df_featured, request.days)
        
        # Get historical data for response
        history_data = df_featured.tail(30)[['Close']].values.flatten().tolist()
        
        # Log prediction to database
        try:
            user_data = UserRepository.get_user_by_username(current_user.username)
            user_id = user_data.get('id') if user_data else None
            
            PredictionRepository.log_prediction(
                user_id=user_id,
                prediction_type="price_forecast",
                input_data={"days": request.days, "confidence_level": request.confidence_level},
                prediction_result={"predictions": predictions.tolist()},
                confidence_score=0.8  # Placeholder - implement actual confidence calculation
            )
        except Exception as db_error:
            logger.warning(f"Failed to log prediction: {db_error}")
        
        return ForecastResponse(
            history=history_data,
            forecast=predictions.tolist()
        )
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )

@app.post("/forecast/recursive", response_model=ForecastResponse, tags=["Model"])
async def recursive_forecast_endpoint(
    request: ForecastRequest = ForecastRequest(),
    current_user: User = Depends(require_premium)
):
    """Advanced recursive forecasting (Premium feature)."""
    try:
        if model is None or scaler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not trained. Please train the model first."
            )
        
        # Load current data
        df = load_btc_data(start="2020-01-01", end=None, interval="1d")
        df_featured = add_technical_indicators(df)
        
        # Perform recursive forecasting
        recursive_predictions = recursive_forecast(
            model, scaler, features, df_featured, request.days
        )
        
        # Get historical data
        history_data = df_featured.tail(30)[['Close']].values.flatten().tolist()
        
        # Log prediction to database
        try:
            user_data = UserRepository.get_user_by_username(current_user.username)
            user_id = user_data.get('id') if user_data else None
            
            PredictionRepository.log_prediction(
                user_id=user_id,
                prediction_type="recursive_forecast",
                input_data={"days": request.days, "confidence_level": request.confidence_level},
                prediction_result={"predictions": recursive_predictions.tolist()},
                confidence_score=0.85  # Higher confidence for recursive forecasts
            )
        except Exception as db_error:
            logger.warning(f"Failed to log prediction: {db_error}")
        
        return ForecastResponse(
            history=history_data,
            forecast=recursive_predictions.tolist()
        )
        
    except Exception as e:
        logger.error(f"Recursive forecasting failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recursive forecasting failed: {str(e)}"
        )

@app.post("/forecast/features", tags=["Model"])
async def feature_forecast_endpoint(
    request: FeatureForecastRequest,
    current_user: User = Depends(require_premium)
):
    """Forecast technical indicators (Premium feature)."""
    try:
        if model is None or scaler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not trained. Please train the model first."
            )
        
        # Load current data
        df = load_btc_data(start="2020-01-01", end=None, interval="1d")
        df_featured = add_technical_indicators(df)
        
        # Train feature forecasting model
        feature_model = train_feature_forecasting_model(df_featured, request.indicator)
        
        # Make feature prediction
        feature_predictions = feature_model.predict(
            df_featured[features].tail(1).values
        )
        
        # Log prediction to database
        try:
            user_data = UserRepository.get_user_by_username(current_user.username)
            user_id = user_data.get('id') if user_data else None
            
            PredictionRepository.log_prediction(
                user_id=user_id,
                prediction_type=f"feature_forecast_{request.indicator}",
                input_data={"indicator": request.indicator, "days": request.days},
                prediction_result={"predictions": feature_predictions.tolist()},
                confidence_score=0.75
            )
        except Exception as db_error:
            logger.warning(f"Failed to log prediction: {db_error}")
        
        return {
            "indicator": request.indicator,
            "predictions": feature_predictions.tolist(),
            "message": f"Forecast for {request.indicator} indicator"
        }
        
    except Exception as e:
        logger.error(f"Feature forecasting failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature forecasting failed: {str(e)}"
        )

@app.get("/evaluate", tags=["Model"])
async def evaluate_endpoint(current_user: User = Depends(get_current_user)):
    """Evaluate model performance."""
    try:
        if model is None or scaler is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not trained. Please train the model first."
            )
        
        # Load test data
        df = load_btc_data(start="2020-01-01", end=None, interval="1d")
        df_featured = add_technical_indicators(df)
        
        # Evaluate model
        eval_results = evaluate_ensemble_model(model, scaler, features, df_featured)
        
        return {
            "r2_score": eval_results.get('r2_score', 0.0),
            "mae": eval_results.get('mae', 0.0),
            "mse": eval_results.get('mse', 0.0),
            "rmse": eval_results.get('rmse', 0.0),
            "model_status": "loaded" if model is not None else "not_loaded",
            "features_count": len(features) if features else 0
        }
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}"
        )

@app.get("/status", tags=["Model"])
async def status_endpoint(current_user: User = Depends(get_current_user)):
    """Check model status and system health."""
    try:
        health_status = health_monitor.get_health_status()
        
        # Add user-specific information
        user_data = UserRepository.get_user_by_username(current_user.username)
        user_predictions = []
        
        if user_data:
            user_id = user_data.get('id')
            user_predictions = PredictionRepository.get_user_predictions(user_id, limit=5)
        
        return {
            "model_status": "loaded" if model is not None else "not_loaded",
            "scaler_status": "loaded" if scaler is not None else "not_loaded",
            "features_count": len(features) if features else 0,
            "system_health": health_status,
            "user_role": current_user.role,
            "recent_predictions": len(user_predictions)
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status check failed: {str(e)}"
        )

@app.get("/features", tags=["Model"])
async def features_endpoint(current_user: User = Depends(get_current_user)):
    """Get available features and their descriptions."""
    try:
        feature_descriptions = {
            "Close": "Closing price",
            "Volume": "Trading volume",
            "RSI": "Relative Strength Index",
            "MACD": "Moving Average Convergence Divergence",
            "BB_upper": "Bollinger Bands upper",
            "BB_lower": "Bollinger Bands lower",
            "BB_middle": "Bollinger Bands middle",
            "OBV": "On-Balance Volume",
            "Ichimoku_a": "Ichimoku Cloud conversion line",
            "Ichimoku_b": "Ichimoku Cloud base line",
            "Ichimoku_c": "Ichimoku Cloud leading span A",
            "Ichimoku_d": "Ichimoku Cloud leading span B"
        }
        
        return {
            "available_features": features if features else [],
            "feature_descriptions": feature_descriptions,
            "total_features": len(features) if features else 0
        }
        
    except Exception as e:
        logger.error(f"Features endpoint failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Features endpoint failed: {str(e)}"
        )

# User-specific endpoints
@app.get("/user/predictions", tags=["User"])
async def get_user_predictions(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    """Get user's prediction history."""
    try:
        user_data = UserRepository.get_user_by_username(current_user.username)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        predictions = PredictionRepository.get_user_predictions(user_data['id'], limit)
        return {"predictions": predictions}
        
    except Exception as e:
        logger.error(f"Failed to get user predictions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get predictions"
        )

@app.get("/user/analytics", tags=["User"])
async def get_user_analytics(
    days: int = 30,
    current_user: User = Depends(require_premium)
):
    """Get user's prediction analytics (Premium feature)."""
    try:
        analytics = PredictionRepository.get_prediction_analytics(days)
        return {"analytics": analytics}
        
    except Exception as e:
        logger.error(f"Failed to get user analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics"
        )

# Real-time data integration (Competitive Edge Feature)
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time data streaming."""
    await websocket_endpoint(websocket)

@app.get("/realtime/prices", tags=["Real-Time Data"])
async def get_realtime_prices(
    symbols: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get current real-time prices for specified symbols."""
    try:
        symbol_list = symbols.split(',') if symbols else None
        prices = await get_current_prices(symbol_list)
        return prices
    except Exception as e:
        logger.error(f"Failed to get real-time prices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get real-time prices"
        )

@app.post("/realtime/alerts", response_model=PriceAlertResponse, tags=["Real-Time Data"])
async def create_price_alert_endpoint(
    request: PriceAlertRequest,
    current_user: User = Depends(require_premium)
):
    """Create a new price alert."""
    try:
        user_data = UserRepository.get_user_by_username(current_user.username)
        user_id = user_data.get('id') if user_data else current_user.username
        
        alert = await create_price_alert(
            user_id=user_id,
            symbol=request.symbol,
            target_price=request.target_price,
            alert_type=request.alert_type
        )
        return alert
    except Exception as e:
        logger.error(f"Failed to create price alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create price alert"
        )

@app.get("/realtime/alerts", tags=["Real-Time Data"])
async def get_user_alerts_endpoint(
    current_user: User = Depends(require_premium)
):
    """Get user's price alerts."""
    try:
        user_data = UserRepository.get_user_by_username(current_user.username)
        user_id = user_data.get('id') if user_data else current_user.username
        
        alerts = await get_user_alerts(user_id)
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Failed to get user alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get alerts"
        )

@app.delete("/realtime/alerts/{alert_id}", tags=["Real-Time Data"])
async def delete_price_alert_endpoint(
    alert_id: str,
    current_user: User = Depends(require_premium)
):
    """Delete a price alert."""
    try:
        user_data = UserRepository.get_user_by_username(current_user.username)
        user_id = user_data.get('id') if user_data else current_user.username
        
        result = await delete_price_alert(user_id, alert_id)
        return result
    except Exception as e:
        logger.error(f"Failed to delete price alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete price alert"
        )

@app.post("/realtime/start", tags=["Real-Time Data"])
async def start_realtime_data_endpoint(
    current_user: User = Depends(require_admin)
):
    """Start real-time data integration (Admin only)."""
    try:
        await start_realtime_data()
        return {"message": "Real-time data integration started successfully"}
    except Exception as e:
        logger.error(f"Failed to start real-time data integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start real-time data integration"
        )

@app.post("/realtime/stop", tags=["Real-Time Data"])
async def stop_realtime_data_endpoint(
    current_user: User = Depends(require_admin)
):
    """Stop real-time data integration (Admin only)."""
    try:
        await stop_realtime_data()
        return {"message": "Real-time data integration stopped successfully"}
    except Exception as e:
        logger.error(f"Failed to stop real-time data integration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stop real-time data integration"
        ) 