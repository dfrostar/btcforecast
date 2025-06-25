"""
Real-time Data Integration Module
================================

This module provides real-time cryptocurrency price data from multiple exchanges
using WebSocket connections. It's part of the competitive edge implementation
to provide live market data and enhance user experience.

Key Features:
- Multi-exchange WebSocket connections (Binance, Coinbase, Kraken)
- Real-time price aggregation and validation
- Automatic reconnection and error handling
- Data normalization across exchanges
- Price alert system integration

Author: BTC Forecasting Team
Date: 2025-06-25
Version: 1.0.0
"""

import asyncio
import websockets
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
import aiohttp
import pandas as pd
import numpy as np
from threading import Thread, Lock
import queue

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PriceData:
    """Structured price data from exchanges."""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    exchange: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None

@dataclass
class ExchangeConfig:
    """Configuration for exchange connections."""
    name: str
    websocket_url: str
    api_url: str
    symbols: List[str]
    ping_interval: int = 30
    reconnect_delay: int = 5
    max_reconnect_attempts: int = 10

class WebSocketManager:
    """Manages WebSocket connections to multiple exchanges."""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.price_data: Dict[str, PriceData] = {}
        self.subscribers: List[Callable] = []
        self.running = False
        self.lock = Lock()
        self.price_queue = queue.Queue()
        
        # Exchange configurations
        self.exchanges = {
            'binance': ExchangeConfig(
                name='Binance',
                websocket_url='wss://stream.binance.com:9443/ws/',
                api_url='https://api.binance.com/api/v3',
                symbols=['btcusdt', 'ethusdt', 'adausdt', 'dotusdt', 'solusdt']
            ),
            'coinbase': ExchangeConfig(
                name='Coinbase',
                websocket_url='wss://ws-feed.pro.coinbase.com',
                api_url='https://api.pro.coinbase.com',
                symbols=['BTC-USD', 'ETH-USD', 'ADA-USD', 'DOT-USD', 'SOL-USD']
            ),
            'kraken': ExchangeConfig(
                name='Kraken',
                websocket_url='wss://ws.kraken.com',
                api_url='https://api.kraken.com/0',
                symbols=['XBT/USD', 'ETH/USD', 'ADA/USD', 'DOT/USD', 'SOL/USD']
            )
        }
    
    async def start(self):
        """Start all WebSocket connections."""
        self.running = True
        logger.info("Starting real-time data connections...")
        
        # Start connections for each exchange
        tasks = []
        for exchange_id, config in self.exchanges.items():
            task = asyncio.create_task(self._connect_exchange(exchange_id, config))
            tasks.append(task)
        
        # Start price processing thread
        self.price_thread = Thread(target=self._process_price_queue, daemon=True)
        self.price_thread.start()
        
        # Wait for all connections
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop(self):
        """Stop all WebSocket connections."""
        self.running = False
        logger.info("Stopping real-time data connections...")
        
        for connection in self.connections.values():
            if connection and not connection.closed:
                await connection.close()
    
    async def _connect_exchange(self, exchange_id: str, config: ExchangeConfig):
        """Connect to a specific exchange."""
        reconnect_attempts = 0
        
        while self.running and reconnect_attempts < config.max_reconnect_attempts:
            try:
                logger.info(f"Connecting to {config.name}...")
                
                # Create WebSocket connection
                connection = await websockets.connect(config.websocket_url)
                self.connections[exchange_id] = connection
                
                # Subscribe to price feeds
                await self._subscribe_to_feeds(connection, exchange_id, config)
                
                # Reset reconnect attempts on successful connection
                reconnect_attempts = 0
                
                # Listen for messages
                async for message in connection:
                    if not self.running:
                        break
                    
                    await self._process_message(exchange_id, message)
                    
            except Exception as e:
                logger.error(f"Error connecting to {config.name}: {e}")
                reconnect_attempts += 1
                
                if self.running:
                    await asyncio.sleep(config.reconnect_delay)
    
    async def _subscribe_to_feeds(self, connection, exchange_id: str, config: ExchangeConfig):
        """Subscribe to price feeds for the exchange."""
        if exchange_id == 'binance':
            # Binance subscription
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol}@ticker" for symbol in config.symbols],
                "id": 1
            }
            await connection.send(json.dumps(subscribe_msg))
            
        elif exchange_id == 'coinbase':
            # Coinbase subscription
            subscribe_msg = {
                "type": "subscribe",
                "product_ids": config.symbols,
                "channels": ["ticker"]
            }
            await connection.send(json.dumps(subscribe_msg))
            
        elif exchange_id == 'kraken':
            # Kraken subscription
            subscribe_msg = {
                "event": "subscribe",
                "pair": config.symbols,
                "subscription": {"name": "ticker"}
            }
            await connection.send(json.dumps(subscribe_msg))
    
    async def _process_message(self, exchange_id: str, message: str):
        """Process incoming WebSocket messages."""
        try:
            data = json.loads(message)
            
            if exchange_id == 'binance':
                await self._process_binance_message(data)
            elif exchange_id == 'coinbase':
                await self._process_coinbase_message(data)
            elif exchange_id == 'kraken':
                await self._process_kraken_message(data)
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON message from {exchange_id}")
        except Exception as e:
            logger.error(f"Error processing message from {exchange_id}: {e}")
    
    async def _process_binance_message(self, data: Dict):
        """Process Binance ticker message."""
        if 's' in data and 'c' in data:  # Symbol and close price
            symbol = data['s'].lower()
            price_data = PriceData(
                symbol=symbol,
                price=float(data['c']),
                volume=float(data['v']),
                timestamp=datetime.fromtimestamp(data['E'] / 1000),
                exchange='Binance',
                bid=float(data.get('b', 0)),
                ask=float(data.get('a', 0)),
                high_24h=float(data.get('h', 0)),
                low_24h=float(data.get('l', 0))
            )
            self.price_queue.put(price_data)
    
    async def _process_coinbase_message(self, data: Dict):
        """Process Coinbase ticker message."""
        if data.get('type') == 'ticker' and 'product_id' in data:
            symbol = data['product_id'].lower().replace('-', '')
            price_data = PriceData(
                symbol=symbol,
                price=float(data['price']),
                volume=float(data['size']),
                timestamp=datetime.fromisoformat(data['time'].replace('Z', '+00:00')),
                exchange='Coinbase',
                bid=float(data.get('best_bid', 0)),
                ask=float(data.get('best_ask', 0)),
                high_24h=float(data.get('high_24h', 0)),
                low_24h=float(data.get('low_24h', 0))
            )
            self.price_queue.put(price_data)
    
    async def _process_kraken_message(self, data: Dict):
        """Process Kraken ticker message."""
        if isinstance(data, list) and len(data) > 1:
            ticker_data = data[1]
            if isinstance(ticker_data, dict) and 'c' in ticker_data:
                symbol = data[3].lower().replace('/', '')
                price_data = PriceData(
                    symbol=symbol,
                    price=float(ticker_data['c'][0]),
                    volume=float(ticker_data['v'][1]),
                    timestamp=datetime.now(),
                    exchange='Kraken',
                    bid=float(ticker_data.get('b', [0])[0]),
                    ask=float(ticker_data.get('a', [0])[0]),
                    high_24h=float(ticker_data.get('h', [0])[1]),
                    low_24h=float(ticker_data.get('l', [0])[1])
                )
                self.price_queue.put(price_data)
    
    def _process_price_queue(self):
        """Process price data from the queue in a separate thread."""
        while self.running:
            try:
                price_data = self.price_queue.get(timeout=1)
                
                with self.lock:
                    # Update price data
                    key = f"{price_data.symbol}_{price_data.exchange}"
                    self.price_data[key] = price_data
                    
                    # Notify subscribers
                    for subscriber in self.subscribers:
                        try:
                            subscriber(price_data)
                        except Exception as e:
                            logger.error(f"Error in subscriber callback: {e}")
                            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing price queue: {e}")
    
    def subscribe(self, callback: Callable[[PriceData], None]):
        """Subscribe to price updates."""
        self.subscribers.append(callback)
    
    def get_latest_price(self, symbol: str, exchange: Optional[str] = None) -> Optional[PriceData]:
        """Get the latest price for a symbol."""
        with self.lock:
            if exchange:
                key = f"{symbol}_{exchange}"
                return self.price_data.get(key)
            else:
                # Return the most recent price from any exchange
                latest = None
                for key, price_data in self.price_data.items():
                    if key.startswith(f"{symbol}_"):
                        if latest is None or price_data.timestamp > latest.timestamp:
                            latest = price_data
                return latest
    
    def get_aggregated_price(self, symbol: str) -> Optional[Dict]:
        """Get aggregated price data from all exchanges."""
        with self.lock:
            prices = []
            for key, price_data in self.price_data.items():
                if key.startswith(f"{symbol}_"):
                    prices.append(price_data)
            
            if not prices:
                return None
            
            # Calculate weighted average price
            total_volume = sum(p.volume for p in prices)
            if total_volume > 0:
                weighted_price = sum(p.price * p.volume for p in prices) / total_volume
            else:
                weighted_price = sum(p.price for p in prices) / len(prices)
            
            return {
                'symbol': symbol,
                'price': weighted_price,
                'volume': total_volume,
                'timestamp': max(p.timestamp for p in prices),
                'sources': len(prices),
                'prices': {p.exchange: p.price for p in prices}
            }

class PriceAlertSystem:
    """Price alert system for real-time notifications."""
    
    def __init__(self):
        self.alerts: Dict[str, List[Dict]] = defaultdict(list)
        self.triggered_alerts: List[Dict] = []
    
    def add_alert(self, user_id: str, symbol: str, target_price: float, 
                  alert_type: str = 'above', callback: Optional[Callable] = None):
        """Add a price alert."""
        alert = {
            'id': f"{user_id}_{symbol}_{target_price}_{alert_type}",
            'user_id': user_id,
            'symbol': symbol,
            'target_price': target_price,
            'alert_type': alert_type,
            'callback': callback,
            'created_at': datetime.now(),
            'triggered': False
        }
        self.alerts[user_id].append(alert)
        logger.info(f"Added price alert: {alert['id']}")
    
    def check_alerts(self, price_data: PriceData):
        """Check if any alerts should be triggered."""
        symbol = price_data.symbol
        current_price = price_data.price
        
        for user_id, user_alerts in self.alerts.items():
            for alert in user_alerts:
                if alert['symbol'] == symbol and not alert['triggered']:
                    triggered = False
                    
                    if alert['alert_type'] == 'above' and current_price >= alert['target_price']:
                        triggered = True
                    elif alert['alert_type'] == 'below' and current_price <= alert['target_price']:
                        triggered = True
                    
                    if triggered:
                        alert['triggered'] = True
                        alert['triggered_at'] = datetime.now()
                        alert['triggered_price'] = current_price
                        
                        self.triggered_alerts.append(alert)
                        
                        # Execute callback if provided
                        if alert['callback']:
                            try:
                                alert['callback'](alert, price_data)
                            except Exception as e:
                                logger.error(f"Error in alert callback: {e}")
                        
                        logger.info(f"Price alert triggered: {alert['id']} at {current_price}")

# Global instances
websocket_manager = WebSocketManager()
price_alert_system = PriceAlertSystem()

# Initialize price alert system with websocket manager
websocket_manager.subscribe(price_alert_system.check_alerts)

async def start_realtime_data():
    """Start the real-time data system."""
    await websocket_manager.start()

async def stop_realtime_data():
    """Stop the real-time data system."""
    await websocket_manager.stop()

def get_current_price(symbol: str = 'btcusdt') -> Optional[Dict]:
    """Get current price for a symbol."""
    return websocket_manager.get_aggregated_price(symbol)

def add_price_alert(user_id: str, symbol: str, target_price: float, 
                   alert_type: str = 'above', callback: Optional[Callable] = None):
    """Add a price alert."""
    price_alert_system.add_alert(user_id, symbol, target_price, alert_type, callback)

def get_price_history(symbol: str = 'btcusdt', hours: int = 24) -> List[Dict]:
    """Get price history for the last N hours."""
    # This would typically query a database
    # For now, return empty list as placeholder
    return []

# Export main classes and functions
__all__ = [
    'WebSocketManager',
    'PriceAlertSystem',
    'PriceData',
    'start_realtime_data',
    'stop_realtime_data',
    'get_current_price',
    'add_price_alert',
    'get_price_history'
] 