# 🚀 Render.com Deployment Guide for BTC Forecasting API

## 📋 **Prerequisites**
- GitHub account with your BTC Forecasting project
- Render.com account (free tier available)
- All code changes committed and pushed to GitHub

## 🎯 **Quick Deployment Steps**

### **1. Prepare Your Repository**
```bash
# Ensure all files are committed
git add .
git commit -m "Production Ready: Updated for Render.com deployment"
git push origin main
```

### **2. Deploy on Render.com**

#### **Option A: Using render.yaml (Recommended)**
1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Render will automatically detect `render.yaml` and configure the service
5. Click "Apply" to deploy

#### **Option B: Manual Configuration**
1. Go to [render.com](https://render.com) and sign up/login
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `btc-forecast-api`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python api_simple.py`
   - **Plan**: Free

### **3. Environment Variables**
Set these in Render dashboard under "Environment":

| Variable | Value | Description |
|----------|-------|-------------|
| `SECRET_KEY` | `your-strong-secret-key` | Strong secret for JWT tokens |
| `ENVIRONMENT` | `production` | Production environment flag |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `*` | CORS origins (update for production) |
| `API_HOST` | `0.0.0.0` | Host binding |
| `API_PORT` | `8000` | Port (Render sets PORT automatically) |

### **4. Automatic Deployment**
- Render will automatically deploy on every push to `main` branch
- Health checks run every 30 seconds
- Logs are available in real-time

## 🔧 **Configuration Details**

### **Health Checks**
- **Path**: `/health`
- **Interval**: 30 seconds
- **Timeout**: 30 seconds
- **Retries**: 3

### **Port Configuration**
- Render automatically sets `PORT` environment variable
- API uses `os.getenv("PORT", 8001)` for flexibility
- No manual port configuration needed

### **Database**
- Currently using SQLite (file-based)
- For production scale, consider PostgreSQL add-on
- Database file persists between deployments

## 📊 **Monitoring & Logs**

### **Access Logs**
1. Go to your service in Render dashboard
2. Click "Logs" tab
3. View real-time application logs
4. Filter by log level (INFO, ERROR, etc.)

### **Health Monitoring**
- Service status visible in dashboard
- Automatic restarts on health check failures
- Performance metrics available

### **API Endpoints**
- **Health Check**: `https://your-app.onrender.com/health`
- **API Docs**: `https://your-app.onrender.com/docs`
- **Status**: `https://your-app.onrender.com/status`

## 🔒 **Security Considerations**

### **Production Security**
1. **Change Default Secret Key**: Update `SECRET_KEY` in environment variables
2. **CORS Configuration**: Restrict `CORS_ORIGINS` to your frontend domain
3. **Rate Limiting**: Already configured (100 requests/minute)
4. **Input Validation**: All endpoints validated
5. **HTTPS**: Automatically provided by Render

### **Environment Variables**
- Never commit secrets to Git
- Use Render's environment variable management
- Generate strong secret keys

## 🚀 **Scaling Options**

### **Free Tier**
- 750 hours/month
- Sleeps after 15 minutes of inactivity
- Perfect for development and testing

### **Paid Plans**
- Always-on service
- Custom domains
- SSL certificates
- Higher resource limits

## 🔄 **Continuous Deployment**

### **Automatic Updates**
1. Push changes to `main` branch
2. Render automatically detects changes
3. Builds and deploys new version
4. Zero-downtime deployments

### **Manual Deployments**
- Available in Render dashboard
- Rollback to previous versions
- Preview deployments

## 📝 **Troubleshooting**

### **Common Issues**

#### **Build Failures**
- Check `requirements.txt` for compatibility
- Verify Python version (3.11)
- Check build logs in Render dashboard

#### **Runtime Errors**
- Check application logs
- Verify environment variables
- Test locally with same configuration

#### **Health Check Failures**
- Ensure `/health` endpoint returns 200
- Check application startup
- Verify port configuration

### **Debug Commands**
```bash
# Test locally with production settings
ENVIRONMENT=production python api_simple.py

# Check health endpoint
curl http://localhost:8000/health

# Test all endpoints
curl http://localhost:8000/status
curl http://localhost:8000/docs
```

## 📞 **Support**

### **Render Support**
- [Render Documentation](https://render.com/docs)
- [Community Forum](https://community.render.com)
- [Status Page](https://status.render.com)

### **Application Support**
- Check logs in Render dashboard
- Review health check status
- Monitor API response times

---

**Last Updated**: 2025-06-26  
**Version**: 1.0.0  
**Status**: ✅ Production Ready 