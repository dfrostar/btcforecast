"""
Configuration management for BTC Forecasting API
"""
import os
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class APIConfig:
    """API configuration settings"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    log_level: str = "INFO"

@dataclass
class ModelConfig:
    """Model configuration settings"""
    model_path: str = "btc_model.pkl"
    scaler_path: str = "btc_scaler.pkl"
    sequence_length: int = 30
    test_size: float = 0.2
    random_state: int = 42
    retrain_on_startup: bool = False

@dataclass
class DataConfig:
    """Data configuration settings"""
    default_start_date: str = "2014-01-01"
    default_end_date: Optional[str] = None
    default_interval: str = "1d"
    cache_dir: str = "cache"
    max_data_points: int = 10000

@dataclass
class FeatureConfig:
    """Feature engineering configuration"""
    use_technical_indicators: bool = True
    use_sentiment: bool = False
    use_external_data: bool = False
    feature_selection_method: str = "correlation"

@dataclass
class StripeConfig:
    """Stripe payment configuration"""
    secret_key: str = "sk_test_your_stripe_secret_key"
    publishable_key: str = "pk_test_your_stripe_publishable_key"
    webhook_secret: str = "whsec_your_webhook_secret"
    premium_price_id: str = "price_premium_monthly"
    professional_price_id: str = "price_professional_monthly"
    enterprise_price_id: str = "price_enterprise_monthly"

@dataclass
class CeleryConfig:
    """Celery background processing configuration"""
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    task_serializer: str = "json"
    accept_content: list = field(default_factory=lambda: ["json"])
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True
    task_always_eager: bool = False
    worker_prefetch_multiplier: int = 1
    worker_max_tasks_per_child: int = 1000
    result_expires: int = 3600
    beat_schedule: dict = field(default_factory=dict)

@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 10

@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = "sqlite:///btcforecast.db"
    host: str = "localhost"
    port: int = 5432
    name: str = "btcforecast"
    user: str = "btcforecast"
    password: str = "btcforecast"
    ssl_mode: str = "prefer"
    pool_size: int = 10
    max_overflow: int = 20

@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration"""
    prometheus_port: int = 9090
    grafana_port: int = 3000
    jaeger_host: str = "localhost"
    jaeger_port: int = 14268
    monitoring_interval: int = 60
    health_check_interval: int = 30
    metrics_retention_days: int = 30

@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = "change-this-in-production-with-a-strong-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    bcrypt_rounds: int = 12
    api_key_expiration_days: int = 365
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    cors_origins: list = field(default_factory=lambda: ["*"])
    enable_https: bool = True
    ssl_cert_path: str = "ssl/cert.pem"
    ssl_key_path: str = "ssl/key.pem"

@dataclass
class OAuthConfig:
    """OAuth configuration"""
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/auth/callback"

@dataclass
class EmailConfig:
    """Email configuration"""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = "noreply@btcforecast.com"
    enable_ssl: bool = True

@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    environment: str = "development"
    region: str = "us-east-1"
    instance_type: str = "t3.micro"
    auto_scaling: bool = False
    min_instances: int = 1
    max_instances: int = 10
    load_balancer: bool = True
    ssl_certificate_arn: str = ""

@dataclass
class AppConfig:
    """Main application configuration"""
    api: APIConfig = field(default_factory=APIConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    data: DataConfig = field(default_factory=DataConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    stripe: StripeConfig = field(default_factory=StripeConfig)
    celery: CeleryConfig = field(default_factory=CeleryConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    oauth: OAuthConfig = field(default_factory=OAuthConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    deployment: DeploymentConfig = field(default_factory=DeploymentConfig)
    
    # Additional configuration properties
    enable_docs: bool = True
    dashboard_url: str = "http://localhost:8501"
    renewal_url: str = "http://localhost:8000/billing"
    
    # Environment-based overrides
    def __post_init__(self):
        # Override with environment variables if present
        self.api.host = os.getenv("API_HOST", self.api.host)
        self.api.port = int(os.getenv("API_PORT", self.api.port))
        self.api.log_level = os.getenv("LOG_LEVEL", self.api.log_level)
        
        self.model.retrain_on_startup = os.getenv("RETRAIN_ON_STARTUP", "false").lower() == "true"
        
        # Override additional properties
        self.enable_docs = os.getenv("ENABLE_DOCS", "true").lower() == "true"
        self.security.secret_key = os.getenv("SECRET_KEY", self.security.secret_key)
        
        # Parse CORS origins from environment
        cors_env = os.getenv("CORS_ORIGINS", "*")
        if cors_env == "*":
            self.security.cors_origins = ["*"]
        else:
            self.security.cors_origins = [origin.strip() for origin in cors_env.split(",")]
        
        # Stripe configuration
        self.stripe.secret_key = os.getenv("STRIPE_SECRET_KEY", self.stripe.secret_key)
        self.stripe.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", self.stripe.publishable_key)
        self.stripe.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", self.stripe.webhook_secret)
        self.stripe.premium_price_id = os.getenv("STRIPE_PREMIUM_PRICE_ID", self.stripe.premium_price_id)
        self.stripe.professional_price_id = os.getenv("STRIPE_PROFESSIONAL_PRICE_ID", self.stripe.professional_price_id)
        self.stripe.enterprise_price_id = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", self.stripe.enterprise_price_id)
        
        # Redis configuration
        self.redis.host = os.getenv("REDIS_HOST", self.redis.host)
        self.redis.port = int(os.getenv("REDIS_PORT", self.redis.port))
        self.redis.password = os.getenv("REDIS_PASSWORD", self.redis.password)
        self.redis.ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
        
        # Database configuration
        self.database.url = os.getenv("DATABASE_URL", self.database.url)
        self.database.host = os.getenv("DB_HOST", self.database.host)
        self.database.port = int(os.getenv("DB_PORT", self.database.port))
        self.database.name = os.getenv("DB_NAME", self.database.name)
        self.database.user = os.getenv("DB_USER", self.database.user)
        self.database.password = os.getenv("DB_PASSWORD", self.database.password)
        
        # Celery configuration
        self.celery.broker_url = os.getenv("CELERY_BROKER_URL", self.celery.broker_url)
        self.celery.result_backend = os.getenv("CELERY_RESULT_BACKEND", self.celery.result_backend)
        self.celery.task_always_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
        
        # Monitoring configuration
        self.monitoring.prometheus_port = int(os.getenv("PROMETHEUS_PORT", self.monitoring.prometheus_port))
        self.monitoring.grafana_port = int(os.getenv("GRAFANA_PORT", self.monitoring.grafana_port))
        self.monitoring.jaeger_host = os.getenv("JAEGER_HOST", self.monitoring.jaeger_host)
        self.monitoring.jaeger_port = int(os.getenv("JAEGER_PORT", self.monitoring.jaeger_port))
        self.monitoring.monitoring_interval = int(os.getenv("MONITORING_INTERVAL", self.monitoring.monitoring_interval))
        
        # Security configuration
        self.security.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", self.security.jwt_expiration_hours))
        self.security.bcrypt_rounds = int(os.getenv("BCRYPT_ROUNDS", self.security.bcrypt_rounds))
        self.security.api_key_expiration_days = int(os.getenv("API_KEY_EXPIRATION_DAYS", self.security.api_key_expiration_days))
        self.security.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", self.security.rate_limit_requests))
        self.security.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", self.security.rate_limit_window))
        self.security.enable_https = os.getenv("ENABLE_HTTPS", "true").lower() == "true"
        
        # OAuth configuration
        self.oauth.google_client_id = os.getenv("GOOGLE_CLIENT_ID", self.oauth.google_client_id)
        self.oauth.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", self.oauth.google_client_secret)
        self.oauth.github_client_id = os.getenv("GITHUB_CLIENT_ID", self.oauth.github_client_id)
        self.oauth.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET", self.oauth.github_client_secret)
        
        # Email configuration
        self.email.smtp_server = os.getenv("SMTP_SERVER", self.email.smtp_server)
        self.email.smtp_port = int(os.getenv("SMTP_PORT", self.email.smtp_port))
        self.email.smtp_username = os.getenv("SMTP_USERNAME", self.email.smtp_username)
        self.email.smtp_password = os.getenv("SMTP_PASSWORD", self.email.smtp_password)
        self.email.from_email = os.getenv("FROM_EMAIL", self.email.from_email)
        
        # Deployment configuration
        self.deployment.environment = os.getenv("ENVIRONMENT", self.deployment.environment)
        self.deployment.region = os.getenv("REGION", self.deployment.region)
        self.deployment.auto_scaling = os.getenv("AUTO_SCALING", "false").lower() == "true"
        self.deployment.load_balancer = os.getenv("LOAD_BALANCER", "true").lower() == "true"
        
        # Create cache directory if it doesn't exist
        Path(self.data.cache_dir).mkdir(exist_ok=True)
    
    def get(self, key: str, default=None):
        """Dictionary-like access for backward compatibility"""
        if hasattr(self, key):
            return getattr(self, key)
        return default
    
    @property
    def REDIS_URL(self) -> str:
        """Get Redis URL for Celery"""
        if self.redis.password:
            return f"redis://:{self.redis.password}@{self.redis.host}:{self.redis.port}/{self.redis.db}"
        return f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
    
    @property
    def DATABASE_URL(self) -> str:
        """Get database URL"""
        if self.database.url.startswith("sqlite"):
            return self.database.url
        return f"postgresql://{self.database.user}:{self.database.password}@{self.database.host}:{self.database.port}/{self.database.name}"
    
    @property
    def SECRET_KEY(self) -> str:
        """Get secret key"""
        return self.security.secret_key
    
    @property
    def jwt_secret_key(self) -> str:
        """Get JWT secret key for backward compatibility"""
        return self.security.secret_key

# Global configuration instance
config = AppConfig()

def get_config() -> AppConfig:
    """Get the global configuration instance"""
    return config

def get_settings() -> AppConfig:
    """Get settings for dependency injection"""
    return config

def update_config(**kwargs):
    """Update configuration with new values"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
        else:
            # Try to update nested configs
            for attr_name in dir(config):
                attr = getattr(config, attr_name)
                if hasattr(attr, key):
                    setattr(attr, key, value)
                    break 