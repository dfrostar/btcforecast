# 🔒 BTC Forecasting API - Security Guide

## 📋 Overview
This guide provides comprehensive information about the security features implemented in the BTC Forecasting API, including authentication, authorization, rate limiting, and best practices for secure deployment.

## 🚀 **Security Features Implemented**

### **1. Authentication & Authorization**

#### **JWT Token Authentication**
- **Stateless Authentication**: Uses JSON Web Tokens (JWT) for secure, stateless authentication
- **Token Types**: Access tokens (30 minutes) and refresh tokens (7 days)
- **Secure Storage**: Tokens are stored securely and automatically refreshed

#### **User Roles & Permissions**
- **Free Users**: Basic access to core forecasting features
- **Premium Users**: Enhanced features, higher rate limits, advanced analytics
- **Admin Users**: Full system access, user management, audit logs

#### **Password Security**
- **Bcrypt Hashing**: Passwords are hashed using bcrypt with salt
- **Password Policies**: Enforced minimum requirements and complexity
- **Secure Storage**: No plain-text passwords stored

### **2. API Security**

#### **Rate Limiting**
- **Tiered Limits**: Different limits based on user role
  - Free: 60 requests per minute
  - Premium: 300 requests per minute
  - Admin: 1000 requests per minute
- **Rate Limit Headers**: Response headers show current usage and limits
- **Automatic Cleanup**: Old rate limit data automatically cleaned

#### **Input Validation & Sanitization**
- **Pydantic Models**: Comprehensive input validation using Pydantic
- **Type Checking**: Strict type checking for all inputs
- **Sanitization**: Automatic sanitization of user inputs
- **Error Handling**: Secure error messages without information leakage

#### **CORS Configuration**
- **Configurable Origins**: Set allowed origins for cross-origin requests
- **Secure Headers**: Proper CORS headers for security
- **Environment-based**: Different settings for development and production

### **3. Data Security**

#### **Database Security**
- **SQLite Encryption**: Database files can be encrypted
- **Secure Connections**: All database connections use secure protocols
- **Access Control**: Database access restricted to application only

#### **Audit Logging**
- **Comprehensive Logging**: All API requests and responses logged
- **User Tracking**: User actions tracked with timestamps
- **Security Events**: Failed authentication attempts logged
- **Data Access**: All data access logged for compliance

#### **Data Backup**
- **Automated Backups**: Regular database backups
- **Secure Storage**: Backups stored securely
- **Recovery Procedures**: Documented recovery processes

## 🔧 **Setup & Configuration**

### **1. Environment Configuration**

Create a `.env.production` file with the following settings:

```bash
# Security Configuration
JWT_SECRET_KEY=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FREE=60
RATE_LIMIT_PREMIUM=300
RATE_LIMIT_ADMIN=1000

# CORS Settings
CORS_ORIGINS=["https://yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true

# Database
DATABASE_URL=sqlite:///btcforecast_production.db
DATABASE_ENCRYPTION_KEY=your-database-encryption-key

# Monitoring
AUDIT_LOGGING_ENABLED=true
SECURITY_LOGGING_ENABLED=true
```

### **2. SSL/TLS Configuration**

For production deployment, configure SSL certificates:

```bash
# SSL Certificate paths
SSL_CERT_PATH=/path/to/your/certificate.pem
SSL_KEY_PATH=/path/to/your/private-key.pem
SSL_ENABLED=true
```

### **3. Firewall Configuration**

Configure firewall rules for the application:

```powershell
# Allow API port
New-NetFirewallRule -DisplayName "BTC Forecast API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# Allow frontend port
New-NetFirewallRule -DisplayName "BTC Forecast Frontend" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

## 👥 **User Management**

### **1. User Registration**

Users can register through the API:

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "role": "free"
  }'
```

### **2. User Login**

Users authenticate to get JWT tokens:

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "SecurePassword123!"
  }'
```

Response includes access and refresh tokens:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### **3. API Key Generation**

Users can generate API keys for programmatic access:

```bash
curl -X POST "http://localhost:8000/auth/api-key" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### **4. Using Authentication**

Include the token in API requests:

```bash
# Using Bearer token
curl -X POST "http://localhost:8000/predict" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'

# Using API key
curl -X POST "http://localhost:8000/predict" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'
```

## 🔍 **Monitoring & Auditing**

### **1. Health Monitoring**

Check system health and security status:

```bash
# Basic health check
curl "http://localhost:8000/health"

# Detailed health status
curl "http://localhost:8000/health/detailed"

# Performance metrics
curl "http://localhost:8000/health/metrics"
```

### **2. Audit Logs**

Admin users can access audit logs:

```bash
curl "http://localhost:8000/admin/audit-log?limit=100" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### **3. User Analytics**

Track user activity and API usage:

```bash
curl "http://localhost:8000/admin/metrics?hours=24" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

## 🛡️ **Security Best Practices**

### **1. Password Security**

- Use strong, unique passwords
- Enable two-factor authentication if available
- Regularly rotate passwords
- Never share passwords or API keys

### **2. API Key Management**

- Generate unique API keys for each application
- Rotate API keys regularly
- Store API keys securely
- Never commit API keys to version control

### **3. Network Security**

- Use HTTPS in production
- Configure proper firewall rules
- Monitor network traffic
- Use VPN for remote access

### **4. Application Security**

- Keep dependencies updated
- Monitor security advisories
- Regular security audits
- Implement proper error handling

## 🚨 **Security Incident Response**

### **1. Detecting Security Issues**

Monitor for:
- Failed authentication attempts
- Unusual API usage patterns
- System performance degradation
- Unauthorized access attempts

### **2. Responding to Incidents**

1. **Immediate Response**
   - Isolate affected systems
   - Preserve evidence
   - Notify stakeholders

2. **Investigation**
   - Review audit logs
   - Analyze security events
   - Identify root cause

3. **Recovery**
   - Implement security fixes
   - Restore from backups if needed
   - Update security measures

4. **Post-Incident**
   - Document lessons learned
   - Update security procedures
   - Conduct security review

## 📊 **Security Metrics**

### **1. Key Performance Indicators**

- **Authentication Success Rate**: >95%
- **API Response Time**: <500ms
- **Rate Limit Violations**: <1%
- **Security Incidents**: 0 per month

### **2. Monitoring Alerts**

Set up alerts for:
- High rate of failed logins
- Unusual API usage patterns
- System performance issues
- Security configuration changes

## 🔧 **Troubleshooting**

### **1. Common Issues**

#### **Authentication Failures**
```bash
# Check token validity
curl "http://localhost:8000/auth/profile" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Regenerate token if needed
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "password"}'
```

#### **Rate Limit Exceeded**
```bash
# Check rate limit status
curl "http://localhost:8000/health/metrics" \
  -H "X-API-Key: YOUR_API_KEY"

# Response includes rate limit headers
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 45
# X-RateLimit-Reset: 1640995200
```

#### **Database Issues**
```bash
# Check database health
curl "http://localhost:8000/health/detailed"

# Backup database
.\backup_production.ps1
```

### **2. Security Checklist**

Before going to production:

- [ ] Change default passwords
- [ ] Update JWT secret key
- [ ] Configure SSL certificates
- [ ] Set up firewall rules
- [ ] Configure monitoring
- [ ] Test backup procedures
- [ ] Review audit logging
- [ ] Update CORS settings
- [ ] Configure rate limits
- [ ] Test authentication flow

## 📞 **Support & Resources**

### **1. Security Documentation**
- [API Documentation](http://localhost:8000/docs)
- [Security Configuration Guide](SECURITY_CONFIG.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

### **2. Security Contacts**
- **Security Issues**: security@btcforecast.com
- **Technical Support**: support@btcforecast.com
- **Emergency**: +1-555-SECURITY

### **3. Security Updates**
- Subscribe to security advisories
- Monitor GitHub security alerts
- Regular security reviews
- Automated dependency updates

---

**Last Updated**: 2025-06-25  
**Version**: 1.0.0  
**Security Level**: Production Ready 