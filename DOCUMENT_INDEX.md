# DOCUMENT_INDEX.md

## 📚 **Documentation Overview**
This index provides quick access to all documentation files in the BTC Forecasting project.

---

## 🚀 **Core Documentation**

### **Getting Started**
- `README.md` — Main project overview, setup instructions, and quick start guide
- `ROADMAP.md` — Project roadmap, milestones, and development timeline
- `IMPROVEMENTS.md` — **NEW** - Comprehensive list of recent improvements and enhancements

### **Technical Documentation**
- `CODE_INDEX.md` — Structured index of all code files and their purposes
- `RECURSIVE_FORECASTING.md` — Technical details on recursive forecasting implementation

---

## 📖 **Documentation by Category**

### **Setup & Installation**
- `README.md` — Complete setup guide
- `requirements.txt` — Python dependencies
- `environment.yml` — Conda environment specification
- `Dockerfile` — Container configuration
- `docker-compose.yml` — Multi-service deployment

### **Development & Architecture**
- `CODE_INDEX.md` — Code organization and file structure
- `CURSOR_GLOBAL_RULES.md` — **NEW** - Comprehensive global rules for Cursor to maintain project organization standards
- `config.py` — **NEW** - Configuration management system
- `monitoring.py` — **NEW** - Health monitoring and metrics system

### **API Documentation**
- `api/main.py` — API endpoints and functionality
- Interactive docs available at: `http://127.0.0.1:8000/docs`
- OpenAPI schema at: `http://127.0.0.1:8000/openapi.json`

### **Model & Data**
- `RECURSIVE_FORECASTING.md` — Advanced forecasting techniques
- `models/bilstm_attention.py` — Model architecture documentation
- `data/feature_engineering.py` — Feature engineering implementation

### **Operations & Monitoring**
- `IMPROVEMENTS.md` — **NEW** - Recent improvements and system enhancements
- `restart_app.ps1` — **ENHANCED** - Application restart script with port management
- `run_app.ps1` — Streamlit app startup script
- `run_enhanced_training.ps1` — Enhanced training script

---

## 🔧 **Quick Reference**

### **API Endpoints**
- `GET /` — API information and available endpoints
- `GET /health` — Basic health check
- `GET /health/detailed` — **NEW** - Comprehensive health status
- `GET /health/metrics` — **NEW** - Performance metrics
- `POST /train` — Train the forecasting model
- `POST /predict` — Get price predictions
- `POST /forecast/recursive` — Advanced recursive forecasting
- `GET /status` — Model status and information

### **Configuration**
- Environment variables supported for all settings
- Configuration file: `config.py`
- Monitoring metrics: `api_metrics.json`

### **Troubleshooting**
- Port conflicts: Use `restart_app.ps1`
- Model loading issues: Check scikit-learn version
- Windows compatibility: ✅ Fully resolved
- Performance monitoring: Use `/health/detailed` endpoint

---

## 📈 **Recent Updates**

### **Version 2.1.0 (2025-06-24)**
- ✅ **Windows Compatibility**: Fixed pandas_ta dependency issues
- ✅ **Process Management**: Enhanced restart script with port detection
- ✅ **Model Compatibility**: Automatic retraining on version conflicts
- ✅ **Configuration System**: Centralized configuration management
- ✅ **Health Monitoring**: Comprehensive metrics and monitoring
- ✅ **Performance Tracking**: Request/response time monitoring

### **Key Improvements**
1. **Reliability**: Robust error handling and automatic recovery
2. **Monitoring**: Real-time health checks and performance metrics
3. **Maintainability**: Configuration-driven architecture
4. **Compatibility**: Full Windows support and version management

---

## 🎯 **Documentation Best Practices**

### **For Contributors**
1. **Update this index** when adding new documentation
2. **Link related documents** for easy navigation
3. **Include code examples** in technical docs
4. **Maintain version information** for all documents

### **For Users**
1. **Start with README.md** for setup instructions
2. **Check IMPROVEMENTS.md** for latest enhancements
3. **Use CODE_INDEX.md** to understand code structure
4. **Monitor health** via `/health/detailed` endpoint

---

**Last Updated**: 2025-06-24  
**Total Documents**: 8  
**Status**: ✅ Complete and Up-to-Date

### Dependency Compatibility Note
- numpy is pinned to 1.24.4 and pandas_ta to 0.3.14b0 for technical indicator support.
- Always run scripts via run_app.ps1 or run_enhanced_training.ps1 to ensure dependencies are installed.

### Conda Environment Management
- Use `environment.yml` to create and manage your environment.
- Commands:
  - `conda env create -f environment.yml`
  - `conda activate btcforecast`
  - `conda env update -f environment.yml --prune`
- This ensures all dependencies are compatible and avoids pip/conda conflicts.

## Codebase Management
- See [CODE_INDEX.md](./CODE_INDEX.md) for a detailed, maintainable index of all code, scripts, and their purposes.
- Best practices: Update CODE_INDEX.md with every structural change, and use it as a navigation and onboarding tool for contributors. 