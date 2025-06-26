# 📚 BTC Forecasting Project - Code Index

## 🎯 **Project Overview**
Advanced Bitcoin price forecasting system with machine learning models, real-time predictions, and comprehensive analytics dashboard.

**Last Updated**: 2025-06-26  
**Version**: 2.2.0  
**Status**: ✅ Production Ready with Deployment Security Fixes

## 📁 **Core Application Files**

### **Main Application Entry Points**
- **`app.py`** - Main Streamlit dashboard application
  - **Key Functions**: `main()`, `load_model()`, `display_forecast()`
  - **Purpose**: Interactive web dashboard for BTC forecasting
  - **Status**: ✅ Production Ready

- **`api_simple.py`** - Production-ready FastAPI backend
  - **Key Functions**: `lifespan()`, `system_status()`, `register_user()`, `login_user()`
  - **Purpose**: RESTful API with authentication, rate limiting, and monitoring
  - **Status**: ✅ Production Ready (Enhanced with deployment security fixes)
  - **Recent Security Fixes**: 
    - ✅ CORS configuration now uses environment variables
    - ✅ Default user creation controlled by environment variables
    - ✅ Production-ready CORS headers and methods
    - ✅ Secure environment variable parsing

- **`api/main.py`** - Enhanced API with advanced features
  - **Key Functions**: `get_forecast()`, `train_model()`, `get_model_status()`
  - **Purpose**: Advanced API with model management and training
  - **Status**: ✅ Production Ready

## 🔧 **Configuration & Setup**

### **Configuration Management**
- **`config.py`** - Centralized configuration system
  - **Key Functions**: `get_config()`, `update_config()`, `load_environment_config()`
  - **Purpose**: Environment-based configuration with validation
  - **Status**: ✅ Production Ready

### **Environment & Dependencies**
- **`requirements.txt`** - Python dependencies
  - **Key Dependencies**: FastAPI, Streamlit, TensorFlow, pandas, numpy
  - **Status**: ✅ Updated with Windows compatibility fixes

- **`environment.yml`** - Conda environment configuration
  - **Purpose**: Reproducible development environment
  - **Status**: ✅ Production Ready

## 🗄️ **Database & Data Management**

### **Database Layer**
- **`api/database.py`** - Database models and operations
  - **Key Classes**: `DatabaseManager`, `UserRepository`, `SubscriptionRepository`
  - **Key Functions**: `get_user_count()`, `create_user()`, `log_api_request()`
  - **Purpose**: SQLite database with user management and audit logging
  - **Status**: ✅ Production Ready (Added missing get_user_count method)

- **`database/postgres_adapter.py`** - PostgreSQL adapter for scaling
  - **Key Classes**: `PostgreSQLManager`, `AsyncUserRepository`, `AsyncSubscriptionRepository`
  - **Key Functions**: `initialize()`, `execute_query()`, `create_user()`
  - **Purpose**: Production PostgreSQL support with connection pooling
  - **Status**: ✅ Production Ready (Enhanced for deployment)

### **Data Processing**
- **`data/data_loader.py`** - Data fetching and preprocessing
  - **Key Functions**: `fetch_btc_data()`, `preprocess_data()`, `validate_data()`
  - **Purpose**: Automated BTC data collection and validation
  - **Status**: ✅ Production Ready

- **`data/feature_engineering.py`** - Technical indicators and features
  - **Key Functions**: `calculate_technical_indicators()`, `create_features()`
  - **Purpose**: 15+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
  - **Status**: ✅ Production Ready (Windows compatibility fixes)

- **`data/realtime_data.py`** - Real-time data integration
  - **Purpose**: Live price feeds and real-time updates
  - **Status**: 🔄 In Development

## 🤖 **Machine Learning Models**

### **Model Architecture**
- **`model.py`** - Main model training and prediction
  - **Key Functions**: `train_model()`, `predict()`, `evaluate_model()`
  - **Purpose**: LSTM-based ensemble with attention mechanism
  - **Status**: ✅ Production Ready

- **`models/bilstm_attention.py`** - Advanced Bi-LSTM with attention
  - **Key Classes**: `BiLSTMAttentionModel`, `AttentionLayer`
  - **Purpose**: State-of-the-art neural network architecture
  - **Status**: ✅ Production Ready

### **Model Persistence**
- **`btc_model.h5`** - Trained model weights
- **`btc_model.pkl`** - Model metadata and configuration
- **`btc_scaler.pkl`** - Data scaler for preprocessing
- **Status**: ✅ Production Ready (Enhanced with environment variable configuration)

## 🔒 **Security & Authentication**

### **Authentication System**
- **`api/auth.py`** - JWT authentication and security
  - **Key Functions**: `create_access_token()`, `verify_password()`, `get_current_user()`
  - **Purpose**: Secure user authentication with role-based access
  - **Status**: ✅ Production Ready

- **`api/rate_limiter.py`** - Rate limiting implementation
  - **Key Functions**: `check_rate_limit()`, `get_rate_limit_info()`
  - **Purpose**: Tiered rate limiting (Free: 60/min, Premium: 300/min, Admin: 1000/min)
  - **Status**: ✅ Production Ready

### **Security Features**
- **`security/advanced_security.py`** - Advanced security measures
  - **Purpose**: Input validation, sanitization, and security monitoring
  - **Status**: ✅ Production Ready

## 📊 **Monitoring & Analytics**

### **Health Monitoring**
- **`monitoring.py`** - System health and performance monitoring
  - **Key Functions**: `get_system_metrics()`, `log_performance_metrics()`
  - **Purpose**: Real-time system monitoring and alerting
  - **Status**: ✅ Production Ready

- **`health_checks.py`** - Health check endpoints
  - **Key Functions**: `check_database_health()`, `check_external_apis()`, `check_model_health()`
  - **Purpose**: API health monitoring and status reporting
  - **Status**: ✅ Production Ready (Enhanced with deployment fixes)
  - **Recent Security Fixes**:
    - ✅ PostgreSQL and SQLite database support
    - ✅ Circuit breaker pattern for external APIs
    - ✅ Environment variable configuration for model paths
    - ✅ Enhanced retry logic with exponential backoff

### **Analytics & Metrics**
- **`monitoring/advanced_monitoring.py`** - Advanced monitoring features
  - **Purpose**: Performance analytics and trend analysis
  - **Status**: 🔄 In Development

## 🚀 **Deployment & DevOps**

### **Deployment Scripts**
- **`run_app.ps1`** - Application startup script
  - **Purpose**: Automated application startup with error handling
  - **Status**: ✅ Production Ready

- **`restart_app.ps1`** - Application restart with process management
  - **Purpose**: Reliable app restarts with port conflict resolution
  - **Status**: ✅ Production Ready

- **`deploy_enhanced.ps1`** - Enhanced deployment script
  - **Purpose**: Production deployment with security checks
  - **Status**: ✅ Production Ready

### **Containerization**
- **`Dockerfile`** - Main application container
- **`Dockerfile.api`** - API-only container
- **`Dockerfile.web`** - Web dashboard container
- **`docker-compose.yml`** - Multi-service orchestration
- **Status**: ✅ Production Ready

### **Deployment Configuration**
- **`render.yaml`** - Render.com deployment configuration
  - **Purpose**: Production deployment with PostgreSQL database
  - **Status**: ✅ Production Ready (Enhanced with security fixes)
  - **Recent Security Fixes**:
    - ✅ PostgreSQL database configuration
    - ✅ Production environment variables
    - ✅ Secure CORS origins configuration
    - ✅ Disabled default user creation in production

## 📈 **Dashboard & User Interface**

### **Static Assets**
- **`static/css/mobile.css`** - Mobile-responsive styles
- **`static/manifest.json`** - PWA manifest
- **`static/sw.js`** - Service worker for offline functionality
- **Status**: ✅ Production Ready

## 🔄 **Background Tasks & Automation**

### **Task Management**
- **`celery_app.py`** - Celery task queue configuration
- **`tasks/`** - Background task modules
  - **`tasks/data_processing.py`** - Automated data processing
  - **`tasks/model_training.py`** - Scheduled model training
  - **`tasks/analytics.py`** - Analytics and reporting
  - **`tasks/maintenance.py`** - System maintenance tasks
  - **`tasks/notifications.py`** - User notification system
- **Status**: 🔄 In Development

## 📚 **Documentation**

### **User Guides**
- **`README.md`** - Main project documentation
- **`DASHBOARD_GUIDE.md`** - Dashboard usage guide
- **`USER_EXPERIENCE_GUIDE.md`** - User experience documentation
- **`SECURITY_GUIDE.md`** - Security implementation guide
- **Status**: ✅ Production Ready

### **Deployment & Operations**
- **`DEPLOYMENT_NEXT_STEPS.md`** - Comprehensive deployment guide
  - **Purpose**: Step-by-step deployment instructions for Render.com, PowerShell, and Docker
  - **Key Sections**: Security configuration, deployment checklist, verification steps
  - **Status**: ✅ Production Ready (New - 2025-06-26)
- **`DEPLOYMENT_READINESS.md`** - Deployment readiness assessment
- **`PRODUCTION_DEPLOYMENT_CHECKLIST.md`** - Production deployment checklist
- **`PRODUCTION_CHECKLIST.md`** - General production checklist
- **Status**: ✅ Production Ready

## 🧪 **Testing & Quality Assurance**

### **Test Files**
- **`test_*.py`** - Comprehensive test suite
  - **`test_health_checks.py`** - Health check testing
  - **`test_simple_api.py`** - API endpoint testing
  - **`test_training.py`** - Model training validation
  - **`test_realtime.py`** - Real-time functionality testing
- **Status**: ✅ Production Ready

## 🔧 **Error Handling & Resilience**

### **Error Management**
- **`error_handling.py`** - Production error handling and circuit breakers
  - **Key Classes**: `CircuitBreaker`, `ErrorHandler`, `RetryHandler`
  - **Key Functions**: `handle_api_error()`, `circuit_breaker()`, `retry()`
  - **Purpose**: Robust error handling with circuit breaker patterns
  - **Status**: ✅ Production Ready (Enhanced with deployment fixes)
  - **Recent Security Fixes**:
    - ✅ Circuit breaker pattern for external API calls
    - ✅ Retry logic with exponential backoff
    - ✅ Comprehensive error handling and logging
    - ✅ Production-ready error responses

## 📊 **Data Files**

### **Training Data**
- **`btc_forecast.csv`** - Historical BTC price data
- **`btc_training_log.csv`** - Training metrics and logs
- **`training_metrics.csv`** - Model performance metrics
- **`training_resource_log.csv`** - Resource usage during training
- **Status**: ✅ Production Ready

### **Model Outputs**
- **`training_results.json`** - Training session results
- **`training_plots/`** - Training visualization plots
- **Status**: ✅ Production Ready

## 🎯 **Recent Improvements (2025-06-26)**

### **Critical Fixes Applied**
1. **Deprecation Warning Fixes**:
   - Replaced `datetime.utcnow()` with `datetime.now(UTC)`
   - Updated FastAPI event handlers to use lifespan instead of on_event
   - Fixed all deprecation warnings in API endpoints

2. **Database Method Fixes**:
   - Added missing `get_user_count()` method to UserRepository
   - Fixed system status endpoint errors
   - Improved database error handling

3. **Code Quality Improvements**:
   - Enhanced error handling and logging
   - Improved type hints and documentation
   - Better code organization and structure

### **Performance Enhancements**
- Native pandas/numpy implementations (faster than pandas_ta)
- Optimized feature engineering pipeline
- Improved memory usage with metrics cleanup
- Enhanced request/response time tracking

### **Production Readiness**
- ✅ Full Windows compatibility
- ✅ Robust process management
- ✅ Reliable model loading with auto-recovery
- ✅ Comprehensive monitoring system
- ✅ Configuration-driven architecture
- ✅ Performance tracking and metrics

## 🚀 **Next Steps Priority**

### **Immediate (This Week)**
1. ✅ **Fix Deprecation Warnings** - COMPLETED
2. ✅ **Fix Database Methods** - COMPLETED
3. **Test API Stability** - IN PROGRESS
4. **Update Documentation** - IN PROGRESS

### **Short Term (Next 2 Weeks)**
1. **Real-time Data Integration** - WebSocket feeds
2. **Mobile Experience Enhancement** - PWA features
3. **Advanced Analytics** - Backtesting framework
4. **Performance Optimization** - Caching and async improvements

### **Medium Term (Next Month)**
1. **Portfolio Management** - Multi-asset tracking
2. **Risk Analytics** - VaR, Sharpe ratio calculations
3. **Social Features** - Prediction sharing and leaderboards
4. **Market Intelligence** - News sentiment integration

---

**Last Updated**: 2025-06-26  
**Version**: 2.2.0  
**Status**: ✅ Production Ready with Deployment Security Fixes 