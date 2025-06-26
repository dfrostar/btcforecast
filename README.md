# 🚀 BTC Forecasting API - Production Ready

Advanced Bitcoin price forecasting system with machine learning models, real-time predictions, and comprehensive analytics dashboard.

## 🎯 **Live Demo**
- **API**: [https://btc-forecast-api.onrender.com](https://btc-forecast-api.onrender.com)
- **Health Check**: [https://btc-forecast-api.onrender.com/health](https://btc-forecast-api.onrender.com/health)
- **API Documentation**: [https://btc-forecast-api.onrender.com/docs](https://btc-forecast-api.onrender.com/docs)

## ✅ **Production Status**
- **Deployment**: ✅ Render.com (Auto-deploy from GitHub)
- **Security**: ✅ JWT Authentication, Rate Limiting, Input Validation
- **Monitoring**: ✅ Health Checks, Performance Metrics, Audit Logging
- **Database**: ✅ SQLite with User Management and Audit Logs
- **CI/CD**: ✅ GitHub Actions with Automated Testing

## 🚀 **Quick Start**

### **Local Development**
```bash
# Clone repository
git clone https://github.com/yourusername/btcforecast.git
cd btcforecast

# Install dependencies
pip install -r requirements.txt

# Start API
python api_simple.py

# Access API
curl http://localhost:8001/health
```

### **Production Deployment**
See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for detailed deployment instructions.

## 📊 **API Endpoints**

### **Health & Status**
- `GET /health` - Basic health check
- `GET /health/detailed` - Comprehensive health status
- `GET /status` - System status and metrics

### **Authentication**
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /users/me` - Current user info
- `GET /users/profile` - User profile

### **Forecasting**
- `POST /forecast` - Get BTC price predictions
- `GET /model/status` - Model performance metrics
- `POST /model/train` - Retrain model

## 🔧 **Features**

### **Machine Learning**
- **Model**: Bi-LSTM with Attention Mechanism
- **Accuracy**: 57.5% R² Score
- **Features**: 15+ Technical Indicators
- **Training**: Automated with Cross-validation

### **Security**
- **Authentication**: JWT Tokens
- **Rate Limiting**: Tiered (Free: 60/min, Premium: 300/min)
- **Input Validation**: Comprehensive Sanitization
- **Audit Logging**: Complete API Request/Response Tracking

### **Monitoring**
- **Health Checks**: Real-time System Monitoring
- **Performance Metrics**: Response Times, Success Rates
- **Error Tracking**: Comprehensive Error Handling
- **Logging**: Structured Logging with Correlation IDs

## 🛠 **Technology Stack**

- **Backend**: FastAPI (Python 3.11)
- **ML Framework**: TensorFlow/Keras
- **Database**: SQLite (Production: PostgreSQL)
- **Authentication**: JWT + bcrypt
- **Deployment**: Render.com + Docker
- **CI/CD**: GitHub Actions
- **Monitoring**: Built-in Health Checks

## 📈 **Performance Metrics**

- **Model Accuracy**: 57.5% R² Score
- **Mean Absolute Error**: $9,566
- **Root Mean Square Error**: $11,133
- **Training Time**: 20.3 seconds
- **API Response Time**: < 200ms average

## 🔄 **Development Workflow**

### **Local Development**
1. Make changes to code
2. Test locally: `python api_simple.py`
3. Run tests: `python -m pytest` (if available)
4. Commit changes: `git commit -m "Feature: description"`

### **Production Deployment**
1. Push to `main` branch
2. GitHub Actions runs tests automatically
3. Render.com deploys automatically
4. Health checks verify deployment

## 📚 **Documentation**

- [API Documentation](https://btc-forecast-api.onrender.com/docs) - Interactive API docs
- [Deployment Guide](RENDER_DEPLOYMENT.md) - Render.com deployment
- [Code Index](CODE_INDEX.md) - Complete codebase overview
- [Roadmap](ROADMAP.md) - Development roadmap and milestones
- [Security Guide](SECURITY_GUIDE.md) - Security implementation details

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test locally
5. Commit: `git commit -m "Feature: description"`
6. Push: `git push origin feature-name`
7. Create a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

- **Issues**: [GitHub Issues](https://github.com/yourusername/btcforecast/issues)
- **Documentation**: [API Docs](https://btc-forecast-api.onrender.com/docs)
- **Status**: [Health Check](https://btc-forecast-api.onrender.com/health)

---

**Last Updated**: 2025-06-26  
**Version**: 2.1.0  
**Status**: ✅ Production Ready on Render.com
