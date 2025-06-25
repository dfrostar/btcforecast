"""
WebSocket API Module
===================

This module provides WebSocket endpoints for real-time cryptocurrency data
as part of the competitive edge implementation. It integrates with the
realtime_data module to provide live price feeds and alerts.

Key Features:
- Real-time price streaming
- Price alert management
- Multi-exchange data aggregation
- WebSocket connection management

Author: BTC Forecasting Team
Date: 2025-06-25
Version: 1.0.0
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import real-time data module
from data.realtime_data import (
    websocket_manager, 
    price_alert_system,
    get_current_price,
    add_price_alert,
    get_price_history,
    PriceData
)

# Import authentication
from api.auth import get_current_user, User

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for real-time data."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        """Disconnect a WebSocket client."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket client."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_to_user(self, user_id: str, message: str):
        """Send a message to all connections of a specific user."""
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for connection in disconnected:
                self.disconnect(connection, user_id)

# Global connection manager
manager = ConnectionManager()

# Pydantic models for WebSocket messages
class PriceAlertRequest(BaseModel):
    symbol: str
    target_price: float
    alert_type: str = "above"  # "above" or "below"

class PriceAlertResponse(BaseModel):
    id: str
    symbol: str
    target_price: float
    alert_type: str
    created_at: datetime
    status: str

class PriceDataResponse(BaseModel):
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    exchange: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None

# WebSocket endpoint for real-time price data
async def websocket_endpoint(websocket: WebSocket, user_id: Optional[str] = None):
    """WebSocket endpoint for real-time price data streaming."""
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message(
            json.dumps({
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.now().isoformat(),
                "message": "Connected to real-time price feed"
            }),
            websocket
        )
        
        # Send current prices for all symbols
        symbols = ['btcusdt', 'ethusdt', 'adausdt', 'dotusdt', 'solusdt']
        for symbol in symbols:
            price_data = get_current_price(symbol)
            if price_data:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "price_update",
                        "data": price_data,
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(websocket, message, user_id)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "message": "Internal server error",
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        manager.disconnect(websocket, user_id)

async def handle_websocket_message(websocket: WebSocket, message: Dict, user_id: Optional[str]):
    """Handle incoming WebSocket messages."""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # Subscribe to specific symbol updates
        symbol = message.get("symbol", "btcusdt")
        await manager.send_personal_message(
            json.dumps({
                "type": "subscription",
                "symbol": symbol,
                "status": "subscribed",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
    
    elif message_type == "price_alert":
        # Create a price alert
        if not user_id:
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "message": "Authentication required for price alerts",
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )
            return
        
        try:
            alert_request = PriceAlertRequest(**message.get("data", {}))
            
            # Create alert callback
            async def alert_callback(alert, price_data):
                await manager.send_to_user(user_id, json.dumps({
                    "type": "price_alert_triggered",
                    "alert": {
                        "id": alert["id"],
                        "symbol": alert["symbol"],
                        "target_price": alert["target_price"],
                        "current_price": price_data.price,
                        "triggered_at": alert["triggered_at"].isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }))
            
            # Add the alert
            add_price_alert(
                user_id=user_id,
                symbol=alert_request.symbol,
                target_price=alert_request.target_price,
                alert_type=alert_request.alert_type,
                callback=alert_callback
            )
            
            await manager.send_personal_message(
                json.dumps({
                    "type": "price_alert_created",
                    "alert": {
                        "symbol": alert_request.symbol,
                        "target_price": alert_request.target_price,
                        "alert_type": alert_request.alert_type,
                        "created_at": datetime.now().isoformat()
                    },
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )
            
        except Exception as e:
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "message": f"Error creating price alert: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }),
                websocket
            )
    
    elif message_type == "get_price":
        # Get current price for a symbol
        symbol = message.get("symbol", "btcusdt")
        price_data = get_current_price(symbol)
        
        await manager.send_personal_message(
            json.dumps({
                "type": "price_data",
                "symbol": symbol,
                "data": price_data,
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
    
    elif message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(
            json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )

# Price update callback for WebSocket manager
async def price_update_callback(price_data: PriceData):
    """Callback function for price updates from WebSocket manager."""
    # Broadcast price update to all connected clients
    message = json.dumps({
        "type": "price_update",
        "data": {
            "symbol": price_data.symbol,
            "price": price_data.price,
            "volume": price_data.volume,
            "timestamp": price_data.timestamp.isoformat(),
            "exchange": price_data.exchange,
            "bid": price_data.bid,
            "ask": price_data.ask,
            "high_24h": price_data.high_24h,
            "low_24h": price_data.low_24h
        },
        "timestamp": datetime.now().isoformat()
    })
    
    await manager.broadcast(message)

# Register the callback with the WebSocket manager
websocket_manager.subscribe(price_update_callback)

# REST API endpoints for WebSocket functionality
async def get_current_prices(symbols: Optional[List[str]] = None) -> Dict[str, Any]:
    """Get current prices for specified symbols."""
    if not symbols:
        symbols = ['btcusdt', 'ethusdt', 'adausdt', 'dotusdt', 'solusdt']
    
    prices = {}
    for symbol in symbols:
        price_data = get_current_price(symbol)
        if price_data:
            prices[symbol] = price_data
    
    return {
        "prices": prices,
        "timestamp": datetime.now().isoformat(),
        "total_symbols": len(prices)
    }

async def create_price_alert(
    user_id: str,
    symbol: str,
    target_price: float,
    alert_type: str = "above"
) -> PriceAlertResponse:
    """Create a price alert for a user."""
    try:
        # Create alert callback
        async def alert_callback(alert, price_data):
            await manager.send_to_user(user_id, json.dumps({
                "type": "price_alert_triggered",
                "alert": {
                    "id": alert["id"],
                    "symbol": alert["symbol"],
                    "target_price": alert["target_price"],
                    "current_price": price_data.price,
                    "triggered_at": alert["triggered_at"].isoformat()
                },
                "timestamp": datetime.now().isoformat()
            }))
        
        # Add the alert
        add_price_alert(
            user_id=user_id,
            symbol=symbol,
            target_price=target_price,
            alert_type=alert_type,
            callback=alert_callback
        )
        
        return PriceAlertResponse(
            id=f"{user_id}_{symbol}_{target_price}_{alert_type}",
            symbol=symbol,
            target_price=target_price,
            alert_type=alert_type,
            created_at=datetime.now(),
            status="active"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating alert: {str(e)}")

async def get_user_alerts(user_id: str) -> List[Dict[str, Any]]:
    """Get all price alerts for a user."""
    if user_id in price_alert_system.alerts:
        return price_alert_system.alerts[user_id]
    return []

async def delete_price_alert(user_id: str, alert_id: str) -> Dict[str, str]:
    """Delete a price alert."""
    if user_id in price_alert_system.alerts:
        # Find and remove the alert
        alerts = price_alert_system.alerts[user_id]
        for i, alert in enumerate(alerts):
            if alert["id"] == alert_id:
                del alerts[i]
                return {"message": "Alert deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Alert not found")

# Export main functions and classes
__all__ = [
    'ConnectionManager',
    'manager',
    'websocket_endpoint',
    'get_current_prices',
    'create_price_alert',
    'get_user_alerts',
    'delete_price_alert',
    'PriceAlertRequest',
    'PriceAlertResponse',
    'PriceDataResponse'
] 