"""
Subscription Management API Module
==================================

This module provides comprehensive subscription management features for the BTC forecasting application,
including tiered subscriptions, payment processing, usage tracking, and billing automation.

Key Features:
- Tiered subscription management (Free, Premium, Professional, Enterprise)
- Payment processing integration (Stripe, PayPal)
- Usage tracking and billing
- Subscription lifecycle management
- Payment security and compliance
- Subscription analytics and reporting

Author: BTC Forecast Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import uuid
import hashlib
import hmac
import stripe
import os
from pydantic import BaseModel, Field

from .auth import get_current_user, require_premium, require_admin
from .database import get_db, UserRepository, AuditRepository, SubscriptionRepository
from .rate_limiter import rate_limit_middleware
from config import get_config

# Initialize router
router = APIRouter(prefix="/subscriptions", tags=["Subscription Management"])
security = HTTPBearer()

# Configuration
config = get_config()
stripe.api_key = config.stripe.secret_key

# ===== PYDANTIC MODELS =====

class SubscriptionTier(BaseModel):
    """Subscription tier configuration."""
    name: str = Field(..., description="Tier name")
    price_id: str = Field(..., description="Stripe price ID")
    monthly_price: float = Field(..., description="Monthly price in USD")
    features: List[str] = Field(..., description="List of features included")
    rate_limit: int = Field(..., description="API rate limit per hour")
    max_predictions: int = Field(..., description="Maximum predictions per day")
    max_portfolios: int = Field(..., description="Maximum portfolios")
    priority_support: bool = Field(..., description="Priority support access")

class CreateSubscriptionRequest(BaseModel):
    """Request model for creating a subscription."""
    tier_name: str = Field(..., description="Subscription tier name")
    payment_method_id: str = Field(..., description="Stripe payment method ID")
    coupon_code: Optional[str] = Field(None, description="Optional coupon code")

class SubscriptionResponse(BaseModel):
    """Response model for subscription data."""
    id: str
    user_id: str
    tier_name: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    features: List[str]
    usage_stats: Dict[str, Any]

class UsageStats(BaseModel):
    """Usage statistics model."""
    api_calls_today: int
    api_calls_this_month: int
    predictions_today: int
    predictions_this_month: int
    portfolios_count: int
    storage_used_mb: float

class BillingHistoryItem(BaseModel):
    """Billing history item model."""
    id: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    description: str

# ===== SUBSCRIPTION TIERS =====

SUBSCRIPTION_TIERS = {
    "free": SubscriptionTier(
        name="Free",
        price_id="",  # No price ID for free tier
        monthly_price=0.0,
        features=[
            "Basic predictions (1-day forecast)",
            "5 technical indicators",
            "Basic portfolio tracking",
            "Community support"
        ],
        rate_limit=60,  # 60 requests per hour
        max_predictions=10,  # 10 predictions per day
        max_portfolios=1,
        priority_support=False
    ),
    "premium": SubscriptionTier(
        name="Premium",
        price_id=config.stripe.premium_price_id,
        monthly_price=29.99,
        features=[
            "Advanced predictions (7-day forecast)",
            "All 15+ technical indicators",
            "Portfolio management",
            "Risk analytics",
            "Real-time alerts",
            "Priority support"
        ],
        rate_limit=300,  # 300 requests per hour
        max_predictions=100,  # 100 predictions per day
        max_portfolios=5,
        priority_support=True
    ),
    "professional": SubscriptionTier(
        name="Professional",
        price_id=config.stripe.professional_price_id,
        monthly_price=99.99,
        features=[
            "All Premium features",
            "API access",
            "Custom indicators",
            "Advanced backtesting",
            "White-label options",
            "Dedicated support"
        ],
        rate_limit=1000,  # 1000 requests per hour
        max_predictions=500,  # 500 predictions per day
        max_portfolios=20,
        priority_support=True
    ),
    "enterprise": SubscriptionTier(
        name="Enterprise",
        price_id=config.stripe.enterprise_price_id,
        monthly_price=299.99,
        features=[
            "All Professional features",
            "Custom integrations",
            "Dedicated support",
            "SLA guarantees",
            "Custom model training",
            "On-premise deployment"
        ],
        rate_limit=5000,  # 5000 requests per hour
        max_predictions=2000,  # 2000 predictions per day
        max_portfolios=100,
        priority_support=True
    )
}

# ===== DATA MODELS =====

class Subscription:
    """Subscription model"""
    def __init__(self, user_id: str, tier: str, status: str = "active"):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.tier = tier
        self.status = status  # active, cancelled, suspended, expired
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.current_period_start = datetime.utcnow()
        self.current_period_end = datetime.utcnow() + timedelta(days=30)
        self.cancel_at_period_end = False
        self.payment_method_id = None
        self.stripe_subscription_id = None
        self.paypal_subscription_id = None

class Payment:
    """Payment model"""
    def __init__(self, subscription_id: str, amount: float, currency: str = "USD",
                 payment_method: str = "stripe", status: str = "pending"):
        self.id = str(uuid.uuid4())
        self.subscription_id = subscription_id
        self.amount = amount
        self.currency = currency
        self.payment_method = payment_method
        self.status = status  # pending, completed, failed, refunded
        self.created_at = datetime.utcnow()
        self.processed_at = None
        self.stripe_payment_intent_id = None
        self.paypal_payment_id = None
        self.failure_reason = None

class Usage:
    """Usage tracking model"""
    def __init__(self, user_id: str, feature: str, usage_date: datetime = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.feature = feature
        self.usage_date = usage_date or datetime.utcnow()
        self.count = 1

# ===== IN-MEMORY STORAGE (Replace with database in production) =====

subscriptions: Dict[str, Subscription] = {}
payments: Dict[str, Payment] = {}
usage_tracking: Dict[str, Usage] = {}

# ===== SUBSCRIPTION MANAGEMENT ENDPOINTS =====

@router.get("/tiers", response_model=List[SubscriptionTier])
async def get_subscription_tiers():
    """Get available subscription tiers."""
    return list(SUBSCRIPTION_TIERS.values())

@router.get("/current", response_model=SubscriptionResponse)
async def get_current_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription information."""
    subscription_repo = SubscriptionRepository(db)
    subscription = subscription_repo.get_active_subscription(current_user["id"])
    
    if not subscription:
        # Return free tier subscription
        return SubscriptionResponse(
            id="free",
            user_id=current_user["id"],
            tier_name="free",
            status="active",
            current_period_start=datetime.now(),
            current_period_end=datetime.now() + timedelta(days=30),
            cancel_at_period_end=False,
            features=SUBSCRIPTION_TIERS["free"].features,
            usage_stats=subscription_repo.get_usage_stats(current_user["id"]).dict()
        )
    
    tier = SUBSCRIPTION_TIERS.get(subscription.tier_name, SUBSCRIPTION_TIERS["free"])
    
    return SubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        tier_name=subscription.tier_name,
        status=subscription.status,
        current_period_start=subscription.current_period_start,
        current_period_end=subscription.current_period_end,
        cancel_at_period_end=subscription.cancel_at_period_end,
        features=tier.features,
        usage_stats=subscription_repo.get_usage_stats(current_user["id"]).dict()
    )

@router.post("/create", response_model=Dict[str, Any])
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription."""
    if request.tier_name not in SUBSCRIPTION_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription tier"
        )
    
    tier = SUBSCRIPTION_TIERS[request.tier_name]
    
    if tier.name == "Free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create paid subscription for free tier"
        )
    
    subscription_repo = SubscriptionRepository(db)
    
    # Check if user already has an active subscription
    existing_subscription = subscription_repo.get_active_subscription(current_user["id"])
    if existing_subscription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an active subscription"
        )
    
    try:
        # Create Stripe customer if not exists
        user_repo = UserRepository(db)
        user = user_repo.get_user_by_id(current_user["id"])
        
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user.id}
            )
            user_repo.update_stripe_customer_id(user.id, customer.id)
            stripe_customer_id = customer.id
        else:
            stripe_customer_id = user.stripe_customer_id
        
        # Apply coupon if provided
        coupon_id = None
        if request.coupon_code:
            try:
                coupon = stripe.Coupon.retrieve(request.coupon_code)
                coupon_id = coupon.id
            except stripe.error.InvalidRequestError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid coupon code"
                )
        
        # Create Stripe subscription
        subscription_data = {
            "customer": stripe_customer_id,
            "items": [{"price": tier.price_id}],
            "payment_behavior": "default_incomplete",
            "payment_settings": {"save_default_payment_method": "on_subscription"},
            "expand": ["latest_invoice.payment_intent"],
        }
        
        if coupon_id:
            subscription_data["coupon"] = coupon_id
        
        stripe_subscription = stripe.Subscription.create(**subscription_data)
        
        # Save subscription to database
        subscription = subscription_repo.create_subscription(
            user_id=current_user["id"],
            stripe_subscription_id=stripe_subscription.id,
            tier_name=request.tier_name,
            status=stripe_subscription.status,
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
            cancel_at_period_end=stripe_subscription.cancel_at_period_end
        )
        
        return {
            "subscription_id": subscription.id,
            "stripe_subscription_id": stripe_subscription.id,
            "status": stripe_subscription.status,
            "client_secret": stripe_subscription.latest_invoice.payment_intent.client_secret
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment processing error: {str(e)}"
        )

@router.post("/cancel")
async def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel current subscription at period end."""
    subscription_repo = SubscriptionRepository(db)
    subscription = subscription_repo.get_active_subscription(current_user["id"])
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    try:
        # Cancel Stripe subscription
        stripe_subscription = stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update database
        subscription_repo.update_subscription(
            subscription.id,
            cancel_at_period_end=True
        )
        
        return {"message": "Subscription will be canceled at the end of the current period"}
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error canceling subscription: {str(e)}"
        )

@router.post("/reactivate")
async def reactivate_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate a subscription that was scheduled for cancellation."""
    subscription_repo = SubscriptionRepository(db)
    subscription = subscription_repo.get_active_subscription(current_user["id"])
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    if not subscription.cancel_at_period_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is not scheduled for cancellation"
        )
    
    try:
        # Reactivate Stripe subscription
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        # Update database
        subscription_repo.update_subscription(
            subscription.id,
            cancel_at_period_end=False
        )
        
        return {"message": "Subscription reactivated successfully"}
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reactivating subscription: {str(e)}"
        )

@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current usage statistics."""
    subscription_repo = SubscriptionRepository(db)
    return subscription_repo.get_usage_stats(current_user["id"])

@router.get("/billing-history", response_model=List[BillingHistoryItem])
async def get_billing_history(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get billing history for the current user."""
    subscription_repo = SubscriptionRepository(db)
    subscription = subscription_repo.get_active_subscription(current_user["id"])
    
    if not subscription:
        return []
    
    try:
        # Get invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=subscription.stripe_customer_id,
            limit=50
        )
        
        billing_history = []
        for invoice in invoices.data:
            billing_history.append(BillingHistoryItem(
                id=invoice.id,
                amount=invoice.amount_paid / 100,  # Convert from cents
                currency=invoice.currency.upper(),
                status=invoice.status,
                created_at=datetime.fromtimestamp(invoice.created),
                description=invoice.description or f"Invoice for {invoice.period_start}"
            ))
        
        return billing_history
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error retrieving billing history: {str(e)}"
        )

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks for subscription events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.stripe.webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    subscription_repo = SubscriptionRepository(db)
    
    if event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        subscription_repo.update_subscription_from_stripe(subscription)
    
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        subscription_repo.cancel_subscription(subscription.id)
    
    elif event["type"] == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        subscription_repo.handle_successful_payment(invoice)
    
    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        subscription_repo.handle_failed_payment(invoice)
    
    return {"status": "success"}

# ===== ADMIN ENDPOINTS =====

@router.get("/admin/all", response_model=List[SubscriptionResponse])
async def get_all_subscriptions(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all subscriptions (admin only)."""
    subscription_repo = SubscriptionRepository(db)
    subscriptions = subscription_repo.get_all_subscriptions()
    
    result = []
    for subscription in subscriptions:
        tier = SUBSCRIPTION_TIERS.get(subscription.tier_name, SUBSCRIPTION_TIERS["free"])
        result.append(SubscriptionResponse(
            id=subscription.id,
            user_id=subscription.user_id,
            tier_name=subscription.tier_name,
            status=subscription.status,
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            features=tier.features,
            usage_stats=subscription_repo.get_usage_stats(subscription.user_id).dict()
        ))
    
    return result

@router.get("/admin/stats")
async def get_subscription_stats(
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get subscription statistics (admin only)."""
    subscription_repo = SubscriptionRepository(db)
    stats = subscription_repo.get_subscription_stats()
    
    return {
        "total_subscriptions": stats.total_subscriptions,
        "active_subscriptions": stats.active_subscriptions,
        "monthly_revenue": stats.monthly_revenue,
        "subscriptions_by_tier": stats.subscriptions_by_tier,
        "churn_rate": stats.churn_rate,
        "average_revenue_per_user": stats.average_revenue_per_user
    }

# ===== HELPER FUNCTIONS =====

def get_user_tier(user_id: str, db: Session) -> SubscriptionTier:
    """Get the current subscription tier for a user."""
    subscription_repo = SubscriptionRepository(db)
    subscription = subscription_repo.get_active_subscription(user_id)
    
    if subscription and subscription.status == "active":
        return SUBSCRIPTION_TIERS.get(subscription.tier_name, SUBSCRIPTION_TIERS["free"])
    
    return SUBSCRIPTION_TIERS["free"]

def check_subscription_limit(user_id: str, db: Session, limit_type: str) -> bool:
    """Check if user has exceeded subscription limits."""
    subscription_repo = SubscriptionRepository(db)
    usage = subscription_repo.get_usage_stats(user_id)
    tier = get_user_tier(user_id, db)
    
    if limit_type == "api_calls":
        return usage.api_calls_today < tier.rate_limit
    elif limit_type == "predictions":
        return usage.predictions_today < tier.max_predictions
    elif limit_type == "portfolios":
        return usage.portfolios_count < tier.max_portfolios
    
    return True

async def get_user_usage(user_id: str) -> Dict[str, Any]:
    """Get current usage for user"""
    try:
        # Get current period usage
        current_date = datetime.utcnow().strftime('%Y-%m-%d')
        current_hour = datetime.utcnow().strftime('%Y-%m-%d-%H')
        
        usage_data = {}
        
        # Aggregate usage by feature and time period
        for usage_key, usage in usage_tracking.items():
            if usage.user_id == user_id:
                feature = usage.feature
                usage_date = usage.usage_date.strftime('%Y-%m-%d')
                usage_hour = usage.usage_date.strftime('%Y-%m-%d-%H')
                
                # Daily usage
                daily_key = f"{feature}_daily"
                if usage_date == current_date:
                    usage_data[daily_key] = usage_data.get(daily_key, 0) + usage.count
                
                # Hourly usage (for API calls)
                if feature == "api_calls" and usage_hour == current_hour:
                    usage_data["api_calls_hourly"] = usage_data.get("api_calls_hourly", 0) + usage.count
        
        return usage_data
        
    except Exception as e:
        print(f"Error getting user usage: {e}")
        return {}

async def get_user_info(user_id: str, db: Session) -> dict:
    """Get user information for display"""
    # Implement user lookup from database
    return {
        "id": user_id,
        "username": f"user_{user_id[:8]}",
        "email": f"user_{user_id[:8]}@example.com"
    } 