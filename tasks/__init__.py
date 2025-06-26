"""
Background Tasks Package for BTC Forecasting Application
Organized task modules for different processing categories
"""

from . import model_training
from . import data_processing
from . import notifications
from . import analytics
from . import maintenance

__all__ = [
    "model_training",
    "data_processing", 
    "notifications",
    "analytics",
    "maintenance"
]

__version__ = "2.0.0"
__author__ = "BTC Forecast Team" 