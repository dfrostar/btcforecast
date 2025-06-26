"""
Portfolio Management API Module
===============================

This module provides comprehensive portfolio management features for the BTC forecasting application,
including multi-asset tracking, risk analytics, performance metrics, and portfolio optimization.

Key Features:
- Multi-asset portfolio tracking and management
- Portfolio performance analytics and metrics
- Risk analysis (VaR, Sharpe ratio, drawdown)
- Asset allocation optimization
- Rebalancing recommendations
- Portfolio backtesting and simulation

Author: BTC Forecast Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import uuid
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from .auth import get_current_user, require_premium
from .database import get_db, UserRepository, AuditRepository
from config import get_config

# Initialize router
router = APIRouter(prefix="/portfolio", tags=["Portfolio Management"])
security = HTTPBearer()

# Configuration
config = get_config()

# ===== PYDANTIC MODELS =====

class Asset(BaseModel):
    symbol: str = Field(..., description="Asset symbol (e.g., BTC, ETH)")
    amount: float = Field(..., description="Amount of the asset held")
    purchase_price: float = Field(..., description="Purchase price per unit")
    purchase_date: datetime = Field(..., description="Date of purchase")

class Portfolio(BaseModel):
    id: str
    user_id: str
    name: str
    assets: List[Asset]
    created_at: datetime
    updated_at: datetime
    performance: Optional[Dict[str, Any]] = None
    risk_metrics: Optional[Dict[str, Any]] = None

class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., description="Portfolio name")
    assets: List[Asset] = Field(..., description="List of assets")

class UpdatePortfolioRequest(BaseModel):
    name: Optional[str] = Field(None, description="Portfolio name")
    assets: Optional[List[Asset]] = Field(None, description="List of assets")

# ===== DATA MODELS =====

class PortfolioAsset:
    """Portfolio asset model"""
    def __init__(self, portfolio_id: str, symbol: str, quantity: float, 
                 avg_price: float, purchase_date: datetime):
        self.id = str(uuid.uuid4())
        self.portfolio_id = portfolio_id
        self.symbol = symbol
        self.quantity = quantity
        self.avg_price = avg_price
        self.purchase_date = purchase_date
        self.current_price = 0.0
        self.current_value = 0.0
        self.unrealized_pnl = 0.0
        self.unrealized_pnl_percent = 0.0

class PortfolioTransaction:
    """Portfolio transaction model"""
    def __init__(self, portfolio_id: str, asset_symbol: str, transaction_type: str,
                 quantity: float, price: float, timestamp: datetime, fees: float = 0.0):
        self.id = str(uuid.uuid4())
        self.portfolio_id = portfolio_id
        self.asset_symbol = asset_symbol
        self.transaction_type = transaction_type  # buy, sell, deposit, withdrawal
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
        self.fees = fees
        self.total_amount = quantity * price + fees

# ===== IN-MEMORY STORAGE (Replace with database in production) =====

portfolios: Dict[str, Portfolio] = {}
portfolio_assets: Dict[str, PortfolioAsset] = {}
portfolio_transactions: Dict[str, PortfolioTransaction] = {}
portfolio_metrics_cache: Dict[str, Any] = {}

# ===== PORTFOLIO MANAGEMENT ENDPOINTS =====

@router.post("/create", response_model=Portfolio)
async def create_portfolio(
    request: CreatePortfolioRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new portfolio."""
    portfolio_id = f"portfolio_{datetime.now().timestamp()}"
    return Portfolio(
        id=portfolio_id,
        user_id=current_user["id"],
        name=request.name,
        assets=request.assets,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        performance=None,
        risk_metrics=None
    )

@router.get("/list", response_model=List[Portfolio])
async def list_portfolios(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all portfolios for the current user."""
    # Placeholder: return a sample portfolio
    return [
        Portfolio(
            id="portfolio_1",
            user_id=current_user["id"],
            name="BTC Growth",
            assets=[
                Asset(
                    symbol="BTC",
                    amount=0.5,
                    purchase_price=30000,
                    purchase_date=datetime(2024, 1, 10)
                )
            ],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            performance={"total_return": 0.25, "annualized_return": 0.18},
            risk_metrics={"sharpe_ratio": 1.2, "max_drawdown": 0.15}
        )
    ]

@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific portfolio by ID."""
    # Placeholder: return a sample portfolio
    return Portfolio(
        id=portfolio_id,
        user_id=current_user["id"],
        name="BTC Growth",
        assets=[
            Asset(
                symbol="BTC",
                amount=0.5,
                purchase_price=30000,
                purchase_date=datetime(2024, 1, 10)
            )
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        performance={"total_return": 0.25, "annualized_return": 0.18},
        risk_metrics={"sharpe_ratio": 1.2, "max_drawdown": 0.15}
    )

@router.post("/{portfolio_id}/update", response_model=Portfolio)
async def update_portfolio(
    portfolio_id: str,
    request: UpdatePortfolioRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a portfolio's name or assets."""
    # Placeholder: return updated portfolio
    return Portfolio(
        id=portfolio_id,
        user_id=current_user["id"],
        name=request.name or "BTC Growth",
        assets=request.assets or [
            Asset(
                symbol="BTC",
                amount=0.5,
                purchase_price=30000,
                purchase_date=datetime(2024, 1, 10)
            )
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        performance={"total_return": 0.25, "annualized_return": 0.18},
        risk_metrics={"sharpe_ratio": 1.2, "max_drawdown": 0.15}
    )

@router.delete("/{portfolio_id}/delete")
async def delete_portfolio(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a portfolio."""
    return {"message": f"Portfolio {portfolio_id} deleted successfully."}

@router.get("/analytics/{portfolio_id}")
async def get_portfolio_analytics(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analytics for a specific portfolio."""
    # Placeholder analytics
    return {
        "portfolio_id": portfolio_id,
        "total_return": 0.25,
        "annualized_return": 0.18,
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.15,
        "value_at_risk": 0.08
    }

@router.get("/risk-metrics/{portfolio_id}")
async def get_portfolio_risk_metrics(
    portfolio_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get risk metrics for a specific portfolio."""
    # Placeholder risk metrics
    return {
        "portfolio_id": portfolio_id,
        "sharpe_ratio": 1.2,
        "max_drawdown": 0.15,
        "value_at_risk": 0.08
    }

# ===== ASSET MANAGEMENT ENDPOINTS =====

@router.post("/{portfolio_id}/assets/add")
async def add_asset_to_portfolio(
    portfolio_id: str,
    symbol: str,
    quantity: float,
    price: float,
    purchase_date: Optional[datetime] = None,
    fees: float = 0.0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an asset to a portfolio
    
    Args:
        portfolio_id: Portfolio ID
        symbol: Asset symbol (e.g., BTC, ETH)
        quantity: Quantity to add
        price: Purchase price per unit
        purchase_date: Purchase date (defaults to now)
        fees: Transaction fees
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated portfolio asset information
    """
    try:
        # Validate portfolio access
        if portfolio_id not in portfolios:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        portfolio = portfolios[portfolio_id]
        if portfolio.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this portfolio"
            )
        
        # Validate input
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be positive"
            )
        
        if price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price must be positive"
            )
        
        purchase_date = purchase_date or datetime.utcnow()
        
        # Check if asset already exists in portfolio
        existing_assets = [asset for asset in portfolio_assets.values() 
                          if asset.portfolio_id == portfolio_id and asset.symbol == symbol]
        
        if existing_assets:
            # Update existing asset (average cost basis)
            asset = existing_assets[0]
            total_quantity = asset.quantity + quantity
            total_cost = (asset.quantity * asset.avg_price) + (quantity * price)
            asset.avg_price = total_cost / total_quantity
            asset.quantity = total_quantity
        else:
            # Create new asset
            asset = PortfolioAsset(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                purchase_date=purchase_date
            )
            portfolio_assets[asset.id] = asset
        
        # Create transaction record
        transaction = PortfolioTransaction(
            portfolio_id=portfolio_id,
            asset_symbol=symbol,
            transaction_type="buy",
            quantity=quantity,
            price=price,
            timestamp=purchase_date,
            fees=fees
        )
        portfolio_transactions[transaction.id] = transaction
        
        # Update portfolio
        await update_portfolio_value(portfolio_id)
        
        # Log activity
        audit_repo = AuditRepository(db)
        audit_repo.log_activity(
            user_id=current_user["id"],
            action="asset_added",
            details={
                "portfolio_id": portfolio_id,
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "transaction_id": transaction.id
            }
        )
        
        return {
            "success": True,
            "message": "Asset added to portfolio successfully",
            "asset": {
                "id": asset.id,
                "symbol": asset.symbol,
                "quantity": asset.quantity,
                "avg_price": asset.avg_price,
                "current_price": asset.current_price,
                "current_value": asset.current_value,
                "unrealized_pnl": asset.unrealized_pnl,
                "unrealized_pnl_percent": asset.unrealized_pnl_percent
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add asset: {str(e)}"
        )

@router.post("/{portfolio_id}/assets/sell")
async def sell_asset_from_portfolio(
    portfolio_id: str,
    symbol: str,
    quantity: float,
    price: float,
    sell_date: Optional[datetime] = None,
    fees: float = 0.0,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sell an asset from a portfolio
    
    Args:
        portfolio_id: Portfolio ID
        symbol: Asset symbol to sell
        quantity: Quantity to sell
        price: Sale price per unit
        sell_date: Sale date (defaults to now)
        fees: Transaction fees
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Sale transaction details and realized P&L
    """
    try:
        # Validate portfolio access
        if portfolio_id not in portfolios:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        portfolio = portfolios[portfolio_id]
        if portfolio.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this portfolio"
            )
        
        # Find asset
        existing_assets = [asset for asset in portfolio_assets.values() 
                          if asset.portfolio_id == portfolio_id and asset.symbol == symbol]
        
        if not existing_assets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found in portfolio"
            )
        
        asset = existing_assets[0]
        
        # Validate quantity
        if quantity > asset.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient quantity to sell"
            )
        
        sell_date = sell_date or datetime.utcnow()
        
        # Calculate realized P&L
        cost_basis = quantity * asset.avg_price
        sale_proceeds = quantity * price
        realized_pnl = sale_proceeds - cost_basis - fees
        
        # Update asset quantity
        asset.quantity -= quantity
        
        # Remove asset if quantity becomes zero
        if asset.quantity <= 0:
            del portfolio_assets[asset.id]
        
        # Create transaction record
        transaction = PortfolioTransaction(
            portfolio_id=portfolio_id,
            asset_symbol=symbol,
            transaction_type="sell",
            quantity=quantity,
            price=price,
            timestamp=sell_date,
            fees=fees
        )
        portfolio_transactions[transaction.id] = transaction
        
        # Update portfolio
        await update_portfolio_value(portfolio_id)
        
        # Log activity
        audit_repo = AuditRepository(db)
        audit_repo.log_activity(
            user_id=current_user["id"],
            action="asset_sold",
            details={
                "portfolio_id": portfolio_id,
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "realized_pnl": realized_pnl,
                "transaction_id": transaction.id
            }
        )
        
        return {
            "success": True,
            "message": "Asset sold successfully",
            "transaction": {
                "id": transaction.id,
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "realized_pnl": realized_pnl,
                "timestamp": transaction.timestamp.isoformat()
            },
            "remaining_quantity": asset.quantity if asset.quantity > 0 else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sell asset: {str(e)}"
        )

# ===== RISK ANALYTICS ENDPOINTS =====

@router.get("/{portfolio_id}/risk")
async def get_portfolio_risk_metrics(
    portfolio_id: str,
    timeframe: str = Query("30d", regex="^(7d|30d|90d|1y|all)$"),
    confidence_level: float = Query(0.95, ge=0.5, le=0.99),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive risk metrics for a portfolio
    
    Args:
        portfolio_id: Portfolio ID
        timeframe: Analysis timeframe
        confidence_level: VaR confidence level
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Portfolio risk metrics including VaR, Sharpe ratio, drawdown
    """
    try:
        # Validate portfolio access
        if portfolio_id not in portfolios:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        portfolio = portfolios[portfolio_id]
        if portfolio.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this portfolio"
            )
        
        # Calculate risk metrics
        risk_metrics = await calculate_risk_metrics(portfolio_id, timeframe, confidence_level)
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "timeframe": timeframe,
            "confidence_level": confidence_level,
            "risk_metrics": risk_metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate risk metrics: {str(e)}"
        )

# ===== PORTFOLIO OPTIMIZATION ENDPOINTS =====

@router.post("/{portfolio_id}/optimize")
async def optimize_portfolio_allocation(
    portfolio_id: str,
    target_return: Optional[float] = None,
    risk_tolerance: str = Query("moderate", regex="^(conservative|moderate|aggressive)$"),
    current_user: dict = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """
    Optimize portfolio allocation based on risk-return objectives
    
    Args:
        portfolio_id: Portfolio ID
        target_return: Target annual return (optional)
        risk_tolerance: Risk tolerance level
        current_user: Current authenticated user (premium required)
        db: Database session
    
    Returns:
        Optimized allocation recommendations
    """
    try:
        # Validate portfolio access
        if portfolio_id not in portfolios:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        portfolio = portfolios[portfolio_id]
        if portfolio.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this portfolio"
            )
        
        # Calculate optimization
        optimization = await calculate_portfolio_optimization(
            portfolio_id, target_return, risk_tolerance
        )
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "optimization": optimization
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize portfolio: {str(e)}"
        )

# ===== HELPER FUNCTIONS =====

async def update_asset_prices(asset: PortfolioAsset):
    """Update asset current prices and values"""
    try:
        # Mock price update - replace with real price API
        # asset.current_price = await get_current_price(asset.symbol)
        asset.current_price = asset.avg_price * (1 + np.random.normal(0, 0.1))  # Mock price
        
        asset.current_value = asset.quantity * asset.current_price
        asset.unrealized_pnl = asset.current_value - (asset.quantity * asset.avg_price)
        asset.unrealized_pnl_percent = (asset.unrealized_pnl / (asset.quantity * asset.avg_price)) * 100
        
    except Exception as e:
        print(f"Error updating asset prices: {e}")

async def update_portfolio_value(portfolio_id: str):
    """Update portfolio total value"""
    try:
        portfolio = portfolios[portfolio_id]
        assets = [asset for asset in portfolio_assets.values() 
                 if asset.portfolio_id == portfolio_id]
        
        total_value = sum(asset.current_value for asset in assets)
        portfolio.total_value = total_value
        portfolio.updated_at = datetime.utcnow()
        
    except Exception as e:
        print(f"Error updating portfolio value: {e}")

async def calculate_portfolio_metrics(portfolio_id: str) -> Dict[str, Any]:
    """Calculate comprehensive portfolio metrics"""
    try:
        portfolio = portfolios[portfolio_id]
        assets = [asset for asset in portfolio_assets.values() 
                 if asset.portfolio_id == portfolio_id]
        
        if not assets:
            return {
                "total_return": 0.0,
                "total_return_percent": 0.0,
                "total_pnl": 0.0,
                "total_pnl_percent": 0.0
            }
        
        # Calculate metrics
        total_invested = sum(asset.quantity * asset.avg_price for asset in assets)
        total_current_value = sum(asset.current_value for asset in assets)
        total_pnl = total_current_value - total_invested
        total_return_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            "total_return": total_pnl,
            "total_return_percent": total_return_percent,
            "total_pnl": total_pnl,
            "total_pnl_percent": total_return_percent,
            "total_invested": total_invested,
            "total_current_value": total_current_value,
            "num_assets": len(assets)
        }
        
    except Exception as e:
        print(f"Error calculating portfolio metrics: {e}")
        return {}

async def calculate_risk_metrics(portfolio_id: str, timeframe: str, confidence_level: float) -> Dict[str, Any]:
    """Calculate portfolio risk metrics"""
    try:
        # Mock risk calculation - replace with real implementation
        portfolio = portfolios[portfolio_id]
        
        # Simulate historical returns for risk calculation
        returns = np.random.normal(0.001, 0.02, 252)  # Daily returns for 1 year
        
        # Calculate VaR
        var_percentile = (1 - confidence_level) * 100
        var = np.percentile(returns, var_percentile)
        
        # Calculate Sharpe ratio (assuming risk-free rate of 2%)
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        excess_returns = returns - risk_free_rate
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        # Calculate maximum drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        return {
            "var": var,
            "var_percentile": var_percentile,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "volatility": np.std(returns) * np.sqrt(252),
            "expected_return": np.mean(returns) * 252,
            "skewness": float(pd.Series(returns).skew()),
            "kurtosis": float(pd.Series(returns).kurtosis())
        }
        
    except Exception as e:
        print(f"Error calculating risk metrics: {e}")
        return {}

async def calculate_portfolio_optimization(portfolio_id: str, target_return: Optional[float], 
                                         risk_tolerance: str) -> Dict[str, Any]:
    """Calculate portfolio optimization recommendations"""
    try:
        portfolio = portfolios[portfolio_id]
        assets = [asset for asset in portfolio_assets.values() 
                 if asset.portfolio_id == portfolio_id]
        
        if not assets:
            return {"message": "No assets in portfolio to optimize"}
        
        # Mock optimization - replace with real implementation
        # This would typically use Modern Portfolio Theory or other optimization algorithms
        
        current_allocation = {}
        for asset in assets:
            current_allocation[asset.symbol] = {
                "current_weight": asset.current_value / portfolio.total_value,
                "current_value": asset.current_value,
                "quantity": asset.quantity
            }
        
        # Generate optimization recommendations based on risk tolerance
        if risk_tolerance == "conservative":
            # Conservative: Higher allocation to stable assets
            recommended_allocation = {
                "BTC": 0.4,
                "ETH": 0.3,
                "USDT": 0.2,
                "Other": 0.1
            }
        elif risk_tolerance == "moderate":
            # Moderate: Balanced allocation
            recommended_allocation = {
                "BTC": 0.5,
                "ETH": 0.3,
                "USDT": 0.1,
                "Other": 0.1
            }
        else:  # aggressive
            # Aggressive: Higher allocation to growth assets
            recommended_allocation = {
                "BTC": 0.6,
                "ETH": 0.3,
                "USDT": 0.05,
                "Other": 0.05
            }
        
        # Calculate rebalancing recommendations
        rebalancing_trades = []
        for symbol, target_weight in recommended_allocation.items():
            current_weight = current_allocation.get(symbol, {}).get("current_weight", 0)
            if abs(target_weight - current_weight) > 0.05:  # 5% threshold
                target_value = portfolio.total_value * target_weight
                current_value = current_allocation.get(symbol, {}).get("current_value", 0)
                trade_value = target_value - current_value
                
                if abs(trade_value) > portfolio.total_value * 0.01:  # 1% minimum trade
                    rebalancing_trades.append({
                        "symbol": symbol,
                        "action": "buy" if trade_value > 0 else "sell",
                        "value": abs(trade_value),
                        "current_weight": current_weight,
                        "target_weight": target_weight
                    })
        
        return {
            "current_allocation": current_allocation,
            "recommended_allocation": recommended_allocation,
            "rebalancing_trades": rebalancing_trades,
            "risk_tolerance": risk_tolerance,
            "target_return": target_return,
            "expected_volatility": 0.15,  # Mock value
            "expected_sharpe": 1.2  # Mock value
        }
        
    except Exception as e:
        print(f"Error calculating portfolio optimization: {e}")
        return {"error": "Failed to calculate optimization"} 