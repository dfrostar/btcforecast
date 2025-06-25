# CODE_INDEX.md

## Overview
This document provides a structured, maintainable index of all major code, scripts, and documentation in the btcforecast project. Update this file with every major code or structure change.

---

## API
- `api/main.py` — FastAPI app entrypoint, defines REST endpoints for forecasting, training, evaluation, and health checks. **MAJOR UPDATE:** Enhanced with authentication, rate limiting, database integration, audit logging, and production-ready security features. **NEW:** Real-time data integration with WebSocket endpoints and price alert system. **FIXED:** Configuration method compatibility issues resolved. Key: All existing endpoints plus new auth endpoints, admin endpoints, user-specific endpoints, and real-time data endpoints.
- `api/__init__.py` — API package initializer.
- `api/auth.py` — **NEW:** Authentication and authorization module with JWT token authentication, user management, and role-based access control. **FIXED:** Configuration integration issues resolved. Key: `get_current_user()`, `require_premium()`, `require_admin()`, `authenticate_user()`, `create_user()`, `generate_user_api_key()`.
- `api/rate_limiter.py` — **NEW:** Rate limiting middleware with tiered limits for different user roles. Key: `RateLimiter` class, `rate_limit_middleware()`, `get_rate_limit_status()`.
- `api/database.py` — **NEW:** Database module for persistent data storage with SQLAlchemy ORM, user management, and audit logging. Key: `DatabaseManager`, `UserRepository`, `AuditRepository`, `PredictionRepository`, `ModelRepository`, `MetricsRepository`.
- `api/websocket.py` — **NEW:** WebSocket API module for real-time cryptocurrency data streaming. **COMPETITIVE EDGE FEATURE:** Provides live price feeds, price alert management, and multi-exchange data aggregation. Key: `ConnectionManager`, `websocket_endpoint()`, `get_current_prices()`, `create_price_alert()`, `get_user_alerts()`, `delete_price_alert()`.

## Data
- `data/data_loader.py` — Loads and preprocesses BTC data. Key: `load_btc_data()`
- `data/feature_engineering.py` — Adds technical indicators to data using native pandas/numpy. Key: `add_technical_indicators()`. **Note:** Windows-compatible implementation without pandas_ta dependency.
- `data/realtime_data.py` — **NEW:** Real-time data integration module for live cryptocurrency price feeds. **COMPETITIVE EDGE FEATURE:** Multi-exchange WebSocket connections (Binance, Coinbase, Kraken), price aggregation, alert system, and automatic reconnection. Key: `WebSocketManager`, `PriceAlertSystem`, `PriceData`, `start_realtime_data()`, `get_current_price()`, `add_price_alert()`.
- `data/__init__.py` — Data package initializer.

## Models
- `models/bilstm_attention.py` — BiLSTM with attention model definition. Key: `train_ensemble_model`, `predict_with_ensemble`, `evaluate_ensemble_model`, `recursive_forecast`, `train_feature_forecasting_model`.

## Training
- `train_agent.py` — Main training script (basic version).
- `train_agent_enhanced.py` — Enhanced training with monitoring, logging, and notifications.
- `test_training.py` — Test script for training pipeline.

## Application & Automation
- `app.py` — Streamlit frontend dashboard. **MAJOR UPDATE:** Enhanced with improved UI and functionality. **NEW:** Real-time data section with live price feeds, price alerts, and WebSocket integration. **COMPETITIVE EDGE FEATURE:** Added "⚡ Real-Time Data" section with live price cards, alert management, and connection status monitoring.
- `run_app.ps1` — PowerShell script to start the app with environment checks. **Enhanced with better error handling.**
- `run_enhanced_training.ps1` — PowerShell script for enhanced training.
- `restart_app.ps1` — **NEW:** Enhanced PowerShell script for restarting the API with port management and process cleanup.
- `deploy_production.ps1` — **NEW:** Production deployment script with security checks, environment setup, SSL configuration, and monitoring setup.
- `agent_runner.py` — Entry point for agentic automation.
- `download_btc_history.py` — Script to download historical BTC data.

## Configuration & Monitoring
- `config.py` — **MAJOR UPDATE:** Centralized configuration management system with environment variable support. **FIXED:** Added missing configuration properties and dictionary-like access method for backward compatibility. Key: `get_config()`, `update_config()`, `enable_docs`, `cors_origins`, `jwt_secret_key`.
- `monitoring.py` — **NEW:** Health monitoring and metrics collection system. Key: `HealthMonitor`, `get_health_monitor()`.

## Data, Models, and Outputs
- `btc_model.h5`, `btc_model.pkl` — Trained model files.
- `btc_scaler.pkl`, `btc_scaler.gz` — Data scaler files.
- `btc_forecast.csv` — Model forecast outputs.
- `training_results.json` — Training results summary.
- `training_metrics.csv` — Training metrics log.
- `training_resource_log.csv` — Resource usage log.
- `btc_training_log.csv` — Training log.
- `training_plots/` — Training visualizations.
- `logs/` — Log files.
- `btcforecast.db` — **NEW:** SQLite database for user management, audit logs, and predictions.
- `btcforecast_production.db` — **NEW:** Production database file.

## Configuration & Environment
- `environment.yml` — Conda environment specification (primary method).
- `requirements.txt` — Pip dependencies (secondary/legacy). **UPDATED:** Added security and authentication dependencies (PyJWT, bcrypt, etc.). **NEW:** Added real-time data dependencies (websockets, aiohttp, asyncio-mqtt) for competitive edge features.
- `docker-compose.yml`, `Dockerfile` — Containerization configs.
- `.env.production` — **NEW:** Production environment configuration file.

## Documentation
- `README.md` — Main project overview and setup.
- `ROADMAP.md` — **MAJOR UPDATE:** Enhanced project roadmap with competitive edge strategy, market positioning analysis, and comprehensive 12-16 week publication plan. **NEW SECTIONS:** Competitive Edge & Market Positioning, Immediate Competitive Improvements, Advanced Competitive Features, Market Differentiation Strategies, Enhanced Monetization & Business Model, Performance & Scalability Enhancements.
- `DOCUMENT_INDEX.md` — Index of all documentation files. **Updated with new documentation.**
- `RECURSIVE_FORECASTING.md` — Technical details on recursive forecasting.
- `DASHBOARD_GUIDE.md` — **NEW:** Comprehensive dashboard user guide with feature explanations and workflows.
- `IMPROVEMENTS.md` — **NEW:** Detailed documentation of recent improvements and enhancements.
- `CURSOR_GLOBAL_RULES.md` — **NEW:** Comprehensive global rules for Cursor to maintain CODE_INDEX.md and project organization standards.
- `CURSOR_SETUP_GUIDE.md` — **NEW:** Step-by-step guide for setting up and using global rules in Cursor.
- `DEPLOYMENT_READINESS.md` — **NEW:** Comprehensive deployment readiness checklist and production deployment guide.
- `SECURITY_GUIDE.md` — **NEW:** Detailed security implementation guide with best practices and configuration instructions.
- `COMPETITIVE_EDGE_IMPLEMENTATION.md` — **NEW:** Comprehensive implementation plan for competitive edge features with detailed technical specifications, implementation steps, and market differentiation strategies.

---

## Competitive Edge Implementation Status

### 🚀 **IMMEDIATE COMPETITIVE IMPROVEMENTS (Phase 1: COMPLETED)**
- ✅ **Real-time Data Integration**: WebSocket feeds, multiple exchanges, live charts
  - ✅ `data/realtime_data.py` - Multi-exchange WebSocket manager
  - ✅ `api/websocket.py` - WebSocket API endpoints
  - ✅ Real-time price aggregation and validation
  - ✅ Price alert system with notifications
  - ✅ Automatic reconnection and error handling
- [ ] **Mobile Experience**: Responsive design, PWA, touch optimization
- [ ] **Social Features**: Prediction sharing, community forums, leaderboards
- [ ] **Portfolio Management**: Multi-asset tracking, risk analytics
- [ ] **Subscription System**: Payment processing, tiered pricing

### 🔬 **ADVANCED COMPETITIVE FEATURES (Phase 2: PLANNED)**
- [ ] **Backtesting Framework**: Historical testing, strategy optimization
- [ ] **Market Intelligence**: News sentiment, social media analysis
- [ ] **Educational Platform**: Tutorials, learning tools, paper trading
- [ ] **API Ecosystem**: Developer tools, third-party integrations
- [ ] **Advanced Analytics**: Market regime detection, predictive insights

### 🎨 **MARKET DIFFERENTIATION (Phase 3: PLANNED)**
- [ ] **Performance Optimization**: Redis caching, database scaling
- [ ] **Microservices Architecture**: Service decomposition, auto-scaling
- [ ] **Global Deployment**: CDN integration, geographic distribution
- [ ] **Marketing Strategy**: User acquisition, B2B expansion

---

## Deployment Readiness Status

### ✅ **RESOLVED ISSUES**
- **Configuration Compatibility:** Fixed `config.get()` method calls to work with dataclass-based configuration
- **Missing Properties:** Added `enable_docs`, `cors_origins`, and `jwt_secret_key` to AppConfig
- **Import Errors:** Resolved AttributeError issues in auth.py and main.py
- **API Startup:** Application can now start without configuration errors
- **Real-time Data Integration:** WebSocket endpoints and price alert system implemented

### ⚠️ **REMAINING CONSIDERATIONS**
- **Security:** Default JWT secret key should be changed for production
- **CORS:** Currently allows all origins (`*`) - should be restricted for production
- **SSL:** SSL certificates need to be configured for HTTPS
- **Environment Variables:** Production environment variables should be set
- **Database:** Production database should be properly initialized
- **Monitoring:** Health monitoring should be verified in production environment
- **WebSocket Security:** WebSocket connections should be secured for production

### 🚀 **DEPLOYMENT READY**
The application is now **functionally ready for deployment** with the following capabilities:
- ✅ API starts successfully without errors
- ✅ Authentication system operational
- ✅ Database integration working
- ✅ Rate limiting implemented
- ✅ Audit logging functional
- ✅ Production deployment scripts available
- ✅ Docker configuration ready
- ✅ PowerShell automation scripts available
- ✅ **Real-time data integration operational**
- ✅ **WebSocket endpoints functional**
- ✅ **Price alert system implemented**

### 💰 **ENHANCED REVENUE PROJECTIONS**
- **Free Tier**: 5,000 users/month (lead generation)
- **Premium Tier**: 500 users/month at $29.99/month = $14,995/month
- **Professional Tier**: 50 users/month at $99.99/month = $4,999/month
- **Enterprise Tier**: 20 clients at $299/month = $5,980/month
- **Total Monthly Revenue**: $25,974/month
- **Annual Revenue**: $311,688/year

---

## Best Practices for Large Codebases
1. **Update this index with every PR that adds, removes, or refactors files.**
2. **For each file, briefly describe its purpose and key functions/classes.**
3. **Link to documentation and code sections for deeper dives.**
4. **Encourage contributors to maintain this file as part of the review process.**
5. **Automate checks (optional):** Use CI to remind or require updates to CODE_INDEX.md for structural changes.

---

_Last updated: 2025-06-25 (Implemented real-time data integration - Phase 1 competitive edge features completed)_ 