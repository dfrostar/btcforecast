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
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
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
class AppConfig:
    """Main application configuration"""
    api: APIConfig = field(default_factory=APIConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    data: DataConfig = field(default_factory=DataConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    
    # Additional configuration properties
    enable_docs: bool = True
    cors_origins: list = field(default_factory=lambda: ["*"])
    jwt_secret_key: str = "your-secret-key-change-in-production"
    
    # Environment-based overrides
    def __post_init__(self):
        # Override with environment variables if present
        self.api.host = os.getenv("API_HOST", self.api.host)
        self.api.port = int(os.getenv("API_PORT", self.api.port))
        self.api.log_level = os.getenv("LOG_LEVEL", self.api.log_level)
        
        self.model.retrain_on_startup = os.getenv("RETRAIN_ON_STARTUP", "false").lower() == "true"
        
        # Override additional properties
        self.enable_docs = os.getenv("ENABLE_DOCS", "true").lower() == "true"
        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", self.jwt_secret_key)
        
        # Parse CORS origins from environment
        cors_env = os.getenv("CORS_ORIGINS", "*")
        if cors_env == "*":
            self.cors_origins = ["*"]
        else:
            self.cors_origins = [origin.strip() for origin in cors_env.split(",")]
        
        # Create cache directory if it doesn't exist
        Path(self.data.cache_dir).mkdir(exist_ok=True)
    
    def get(self, key: str, default=None):
        """Dictionary-like access for backward compatibility"""
        if hasattr(self, key):
            return getattr(self, key)
        return default

# Global configuration instance
config = AppConfig()

def get_config() -> AppConfig:
    """Get the global configuration instance"""
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