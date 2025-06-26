# BTC Forecasting Multi-Region Deployment

This directory contains the complete multi-region deployment configuration for the BTC Forecasting application, including load balancing, monitoring, security, and background processing.

## Architecture Overview

### Multi-Region Setup
- **US East (Primary)**: 3 API servers, 2 Celery workers
- **US West (Secondary)**: 2 API servers, 1 Celery worker  
- **EU West (Tertiary)**: 2 API servers, 1 Celery worker

### Infrastructure Components

#### Load Balancing
- **Nginx**: Primary load balancer with SSL termination and rate limiting
- **HAProxy**: Advanced load balancer with health checks and session persistence
- **Global Load Balancing**: Geographic distribution based on latency

#### Monitoring & Observability
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Dashboards and visualization
- **Jaeger**: Distributed tracing
- **Elasticsearch + Kibana**: Log aggregation and analysis
- **Filebeat**: Log shipping

#### Service Discovery & Secrets
- **Consul**: Service discovery and health checks
- **Vault**: Secrets management and encryption

#### Background Processing
- **Celery**: Distributed task queue
- **Redis**: Message broker and caching
- **Flower**: Celery monitoring dashboard

#### Data Storage
- **PostgreSQL**: Primary database with replication
- **Redis**: Caching and session storage

## Quick Start

### Prerequisites
- Docker and Docker Compose
- PowerShell 7+ (for deployment scripts)
- At least 8GB RAM and 4 CPU cores

### 1. Environment Setup
```powershell
# Copy environment template
Copy-Item .env.example .env.production

# Edit environment variables
notepad .env.production
```

### 2. SSL Certificate Setup
```bash
# Generate self-signed certificates for development
mkdir -p deployment/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/nginx/ssl/key.pem \
  -out deployment/nginx/ssl/cert.pem

# For production, use proper certificates
cp your-cert.pem deployment/nginx/ssl/cert.pem
cp your-key.pem deployment/nginx/ssl/key.pem
```

### 3. Deploy to Development
```powershell
# Deploy to development environment
.\deployment\scripts\deploy_multi_region.ps1 -Environment dev -Region all -Action deploy

# Check health
.\deployment\scripts\deploy_multi_region.ps1 -Environment dev -Region all -Action health-check
```

### 4. Access Services
- **API**: https://localhost/api/
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Jaeger**: http://localhost:16686
- **Consul**: http://localhost:8500
- **Vault**: http://localhost:8200 (dev-token)
- **Flower**: http://localhost:5555
- **Kibana**: http://localhost:5601

## Deployment Scripts

### PowerShell Deployment Script
The main deployment script (`deploy_multi_region.ps1`) provides comprehensive deployment management:

```powershell
# Deploy to production
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Region all -Action deploy

# Rolling update
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Region us-east-1 -Action update

# Health check
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Region all -Action health-check

# Rollback
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Action rollback

# Backup
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Action backup

# Monitor
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Action monitor
```

### Script Features
- **Health Checks**: Comprehensive service health validation
- **Rolling Updates**: Zero-downtime deployments
- **Automatic Rollback**: Failed deployment recovery
- **Backup/Restore**: Database and configuration backup
- **Monitoring Integration**: Dashboard access
- **Multi-Region Support**: Geographic deployment management

## Configuration Files

### Docker Compose (`multi_region.yml`)
- Multi-region service definitions
- Resource limits and scaling
- Health checks and restart policies
- Volume mounts and networking

### Nginx Configuration (`nginx/nginx.conf`)
- SSL termination and security headers
- Rate limiting and load balancing
- Gzip compression and caching
- Health check endpoints

### HAProxy Configuration (`haproxy/haproxy.cfg`)
- Advanced load balancing algorithms
- Session persistence
- Health checks and failover
- SSL configuration

### Prometheus Configuration (`monitoring/prometheus.yml`)
- Service discovery and metrics collection
- Alerting rules integration
- Multi-region monitoring setup

### Alert Rules (`monitoring/alert_rules.yml`)
- API performance alerts
- System health monitoring
- Business metrics alerts
- Security and infrastructure alerts

## Monitoring & Alerting

### Key Metrics
- **API Performance**: Response time, error rate, throughput
- **System Health**: CPU, memory, disk usage
- **Business Metrics**: Prediction accuracy, volume, data freshness
- **Infrastructure**: Service availability, load balancer health

### Alert Severity Levels
- **Critical**: Service down, high error rates, security issues
- **Warning**: High resource usage, performance degradation
- **Info**: Normal operational events

### Alert Channels
- Email notifications
- Slack integration
- Webhook endpoints
- PagerDuty integration

## Security Features

### API Security
- API key management with rate limiting
- OAuth 2.0 integration
- Request signing and validation
- Audit logging

### Infrastructure Security
- SSL/TLS encryption
- Secrets management with Vault
- Network isolation
- Security headers

### Access Control
- Role-based permissions
- API key scopes
- IP whitelisting
- Session management

## Background Processing

### Celery Tasks
- **Model Training**: Automated model retraining
- **Data Processing**: Market data updates
- **Notifications**: Email and webhook alerts
- **Analytics**: Report generation
- **Maintenance**: System cleanup and optimization

### Task Queues
- `model_training`: High-priority model updates
- `data_processing`: Market data ingestion
- `notifications`: User alerts and notifications
- `analytics`: Report generation
- `maintenance`: System maintenance tasks

### Monitoring
- **Flower**: Real-time task monitoring
- **Prometheus**: Task metrics and alerts
- **Logs**: Detailed task execution logs

## Scaling & Performance

### Horizontal Scaling
- API servers scale independently per region
- Celery workers scale based on queue depth
- Database read replicas for read-heavy workloads

### Load Balancing
- Round-robin distribution with health checks
- Geographic routing for reduced latency
- Session persistence for stateful operations

### Caching Strategy
- Redis for API response caching
- Database query result caching
- Static asset caching with CDN

## Disaster Recovery

### Backup Strategy
- **Database**: Daily automated backups
- **Configuration**: Version-controlled configs
- **Application Data**: Regular data exports

### Recovery Procedures
- **Service Recovery**: Automatic failover
- **Data Recovery**: Point-in-time restoration
- **Region Failover**: Geographic redundancy

### Business Continuity
- **Multi-Region**: Geographic redundancy
- **Load Balancing**: Automatic failover
- **Monitoring**: Real-time health checks

## Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

#### Health Check Failures
```bash
# Check service status
docker-compose ps

# Test health endpoint
curl http://localhost:8001/health

# Check monitoring
curl http://localhost:9090/-/healthy
```

#### Performance Issues
```bash
# Check resource usage
docker stats

# Monitor logs
docker-compose logs -f

# Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=up
```

### Debug Commands
```powershell
# Check all services
.\deployment\scripts\deploy_multi_region.ps1 -Environment production -Region all -Action health-check

# View logs
docker-compose logs -f [service-name]

# Access service shell
docker exec -it [container-name] /bin/bash

# Check network connectivity
docker network inspect btcforecast-network
```

## Production Checklist

### Pre-Deployment
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database migrations applied
- [ ] Backup strategy tested
- [ ] Monitoring configured
- [ ] Security audit completed

### Deployment
- [ ] Health checks passing
- [ ] Load balancer configured
- [ ] SSL certificates valid
- [ ] Monitoring dashboards accessible
- [ ] Backup system operational
- [ ] Alerting configured

### Post-Deployment
- [ ] Performance metrics normal
- [ ] Error rates acceptable
- [ ] User acceptance testing passed
- [ ] Documentation updated
- [ ] Team notified of deployment

## Support & Maintenance

### Regular Maintenance
- **Daily**: Health check reviews
- **Weekly**: Performance analysis
- **Monthly**: Security updates
- **Quarterly**: Capacity planning

### Monitoring Schedule
- **24/7**: Automated monitoring
- **Business Hours**: Manual review
- **Weekly**: Trend analysis
- **Monthly**: Capacity review

### Contact Information
- **DevOps Team**: devops@btcforecast.com
- **On-Call**: +1-555-0123
- **Documentation**: https://docs.btcforecast.com
- **Status Page**: https://status.btcforecast.com

## License

This deployment configuration is part of the BTC Forecasting project and is licensed under the MIT License. 