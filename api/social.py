"""
Social Features API Module
==========================

This module provides social and community features for the BTC forecasting application,
including prediction sharing, community forums, leaderboards, and social media integration.

Key Features:
- User prediction sharing and social interaction
- Community forums and discussion boards
- Prediction accuracy leaderboards
- Social media integration (Twitter, Reddit)
- User reputation and gamification system
- Community moderation tools

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

from .auth import get_current_user, require_premium
from .database import get_db, UserRepository, AuditRepository
from config import get_config

# Initialize router
router = APIRouter(prefix="/social", tags=["Social Features"])
security = HTTPBearer()

# Configuration
config = get_config()

# ===== DATA MODELS =====

class PredictionShare:
    """Prediction sharing model"""
    def __init__(self, user_id: str, prediction_id: str, message: str, 
                 is_public: bool = True, tags: List[str] = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.prediction_id = prediction_id
        self.message = message
        self.is_public = is_public
        self.tags = tags or []
        self.created_at = datetime.utcnow()
        self.likes = 0
        self.comments = 0
        self.shares = 0

class CommunityPost:
    """Community forum post model"""
    def __init__(self, user_id: str, title: str, content: str, 
                 category: str, tags: List[str] = None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.title = title
        self.content = content
        self.category = category
        self.tags = tags or []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.views = 0
        self.likes = 0
        self.comments = 0
        self.is_pinned = False
        self.is_locked = False

class UserReputation:
    """User reputation and gamification model"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.points = 0
        self.level = 1
        self.accuracy_score = 0.0
        self.predictions_made = 0
        self.predictions_correct = 0
        self.community_contributions = 0
        self.last_updated = datetime.utcnow()

# ===== IN-MEMORY STORAGE (Replace with database in production) =====

prediction_shares: Dict[str, PredictionShare] = {}
community_posts: Dict[str, CommunityPost] = {}
user_reputations: Dict[str, UserReputation] = {}
leaderboard_cache: Dict[str, Any] = {}
leaderboard_cache_time = None

# ===== PREDICTION SHARING ENDPOINTS =====

@router.post("/predictions/share")
async def share_prediction(
    prediction_id: str,
    message: str,
    is_public: bool = True,
    tags: List[str] = Query(default=[]),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Share a prediction with the community
    
    Args:
        prediction_id: ID of the prediction to share
        message: User's message about the prediction
        is_public: Whether the share is public or private
        tags: List of tags for categorization
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Share details with ID and metadata
    """
    try:
        # Validate prediction exists (implement prediction validation)
        # prediction = await validate_prediction(prediction_id, current_user["id"])
        
        # Create share
        share = PredictionShare(
            user_id=current_user["id"],
            prediction_id=prediction_id,
            message=message,
            is_public=is_public,
            tags=tags
        )
        
        prediction_shares[share.id] = share
        
        # Update user reputation
        update_user_reputation(current_user["id"], "prediction_shared", 10)
        
        # Log activity
        audit_repo = AuditRepository(db)
        audit_repo.log_activity(
            user_id=current_user["id"],
            action="prediction_shared",
            details={
                "prediction_id": prediction_id,
                "share_id": share.id,
                "is_public": is_public,
                "tags": tags
            }
        )
        
        return {
            "success": True,
            "share_id": share.id,
            "message": "Prediction shared successfully",
            "share": {
                "id": share.id,
                "prediction_id": share.prediction_id,
                "message": share.message,
                "is_public": share.is_public,
                "tags": share.tags,
                "created_at": share.created_at.isoformat(),
                "user_id": share.user_id
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share prediction: {str(e)}"
        )

@router.get("/predictions/feed")
async def get_prediction_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    tags: List[str] = Query(default=[]),
    user_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get public prediction feed with filtering and pagination
    
    Args:
        page: Page number for pagination
        limit: Number of items per page
        tags: Filter by tags
        user_id: Filter by specific user
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Paginated list of shared predictions
    """
    try:
        # Filter shares
        shares = list(prediction_shares.values())
        
        # Apply filters
        if user_id:
            shares = [s for s in shares if s.user_id == user_id]
        
        if tags:
            shares = [s for s in shares if any(tag in s.tags for tag in tags)]
        
        # Only show public shares or user's own shares
        shares = [s for s in shares if s.is_public or s.user_id == current_user["id"]]
        
        # Sort by creation date (newest first)
        shares.sort(key=lambda x: x.created_at, reverse=True)
        
        # Pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_shares = shares[start_idx:end_idx]
        
        # Enrich with user data and prediction details
        enriched_shares = []
        for share in paginated_shares:
            # Get user info (implement user lookup)
            user_info = get_user_info(share.user_id, db)
            
            # Get prediction details (implement prediction lookup)
            prediction_info = get_prediction_info(share.prediction_id, db)
            
            enriched_shares.append({
                "id": share.id,
                "prediction_id": share.prediction_id,
                "message": share.message,
                "tags": share.tags,
                "created_at": share.created_at.isoformat(),
                "likes": share.likes,
                "comments": share.comments,
                "shares": share.shares,
                "user": user_info,
                "prediction": prediction_info,
                "is_own": share.user_id == current_user["id"]
            })
        
        return {
            "success": True,
            "shares": enriched_shares,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(shares),
                "pages": (len(shares) + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prediction feed: {str(e)}"
        )

# ===== COMMUNITY FORUM ENDPOINTS =====

@router.post("/posts/create")
async def create_community_post(
    title: str,
    content: str,
    category: str,
    tags: List[str] = Query(default=[]),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new community forum post
    
    Args:
        title: Post title
        content: Post content
        category: Post category (general, strategy, news, etc.)
        tags: List of tags
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created post details
    """
    try:
        # Validate input
        if len(title.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title must be at least 5 characters long"
            )
        
        if len(content.strip()) < 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content must be at least 20 characters long"
            )
        
        # Create post
        post = CommunityPost(
            user_id=current_user["id"],
            title=title.strip(),
            content=content.strip(),
            category=category,
            tags=tags
        )
        
        community_posts[post.id] = post
        
        # Update user reputation
        update_user_reputation(current_user["id"], "post_created", 15)
        
        # Log activity
        audit_repo = AuditRepository(db)
        audit_repo.log_activity(
            user_id=current_user["id"],
            action="post_created",
            details={
                "post_id": post.id,
                "title": post.title,
                "category": post.category
            }
        )
        
        return {
            "success": True,
            "post_id": post.id,
            "message": "Post created successfully",
            "post": {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "category": post.category,
                "tags": post.tags,
                "created_at": post.created_at.isoformat(),
                "user_id": post.user_id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create post: {str(e)}"
        )

@router.get("/posts")
async def get_community_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None),
    tags: List[str] = Query(default=[]),
    sort_by: str = Query("newest", regex="^(newest|popular|trending)$"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get community forum posts with filtering and sorting
    
    Args:
        page: Page number for pagination
        limit: Number of items per page
        category: Filter by category
        tags: Filter by tags
        sort_by: Sort method (newest, popular, trending)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Paginated list of community posts
    """
    try:
        # Filter posts
        posts = list(community_posts.values())
        
        # Apply filters
        if category:
            posts = [p for p in posts if p.category == category]
        
        if tags:
            posts = [p for p in posts if any(tag in p.tags for tag in tags)]
        
        # Sort posts
        if sort_by == "newest":
            posts.sort(key=lambda x: x.created_at, reverse=True)
        elif sort_by == "popular":
            posts.sort(key=lambda x: x.likes + x.comments, reverse=True)
        elif sort_by == "trending":
            # Simple trending algorithm (likes + comments in last 24h)
            recent_posts = [p for p in posts if p.created_at > datetime.utcnow() - timedelta(days=1)]
            recent_posts.sort(key=lambda x: x.likes + x.comments, reverse=True)
            posts = recent_posts + [p for p in posts if p.created_at <= datetime.utcnow() - timedelta(days=1)]
        
        # Pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_posts = posts[start_idx:end_idx]
        
        # Enrich with user data
        enriched_posts = []
        for post in paginated_posts:
            user_info = get_user_info(post.user_id, db)
            
            enriched_posts.append({
                "id": post.id,
                "title": post.title,
                "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
                "category": post.category,
                "tags": post.tags,
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat(),
                "views": post.views,
                "likes": post.likes,
                "comments": post.comments,
                "is_pinned": post.is_pinned,
                "is_locked": post.is_locked,
                "user": user_info,
                "is_own": post.user_id == current_user["id"]
            })
        
        return {
            "success": True,
            "posts": enriched_posts,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(posts),
                "pages": (len(posts) + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get community posts: {str(e)}"
        )

# ===== LEADERBOARD ENDPOINTS =====

@router.get("/leaderboard")
async def get_leaderboard(
    category: str = Query("accuracy", regex="^(accuracy|predictions|reputation|community)$"),
    timeframe: str = Query("all_time", regex="^(week|month|all_time)$"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user leaderboards by different categories
    
    Args:
        category: Leaderboard category (accuracy, predictions, reputation, community)
        timeframe: Time period (week, month, all_time)
        limit: Number of users to return
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Leaderboard data with user rankings
    """
    try:
        global leaderboard_cache_time
        # Check cache
        cache_key = f"{category}_{timeframe}_{limit}"
        if (leaderboard_cache_time and 
            leaderboard_cache_time > datetime.utcnow() - timedelta(minutes=15) and
            cache_key in leaderboard_cache):
            return leaderboard_cache[cache_key]
        
        # Calculate leaderboard
        leaderboard = calculate_leaderboard(category, timeframe, limit, db)
        
        # Cache result
        leaderboard_cache[cache_key] = {
            "success": True,
            "category": category,
            "timeframe": timeframe,
            "leaderboard": leaderboard,
            "cached_at": datetime.utcnow().isoformat()
        }
        leaderboard_cache_time = datetime.utcnow()
        
        return leaderboard_cache[cache_key]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get leaderboard: {str(e)}"
        )

# ===== SOCIAL MEDIA INTEGRATION =====

@router.post("/social/share")
async def share_to_social_media(
    share_id: str,
    platforms: List[str] = Query(default=["twitter"]),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Share a prediction or post to social media platforms
    
    Args:
        share_id: ID of the share to post
        platforms: List of platforms to share to
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Sharing results for each platform
    """
    try:
        # Validate share exists
        if share_id not in prediction_shares:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share not found"
            )
        
        share = prediction_shares[share_id]
        
        # Check permissions
        if not share.is_public and share.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot share private content"
            )
        
        results = {}
        
        # Share to each platform
        for platform in platforms:
            if platform == "twitter":
                results["twitter"] = share_to_twitter(share, current_user)
            elif platform == "reddit":
                results["reddit"] = share_to_reddit(share, current_user)
            else:
                results[platform] = {"success": False, "error": "Platform not supported"}
        
        # Update share count
        share.shares += 1
        
        # Log activity
        audit_repo = AuditRepository(db)
        audit_repo.log_activity(
            user_id=current_user["id"],
            action="social_share",
            details={
                "share_id": share_id,
                "platforms": platforms,
                "results": results
            }
        )
        
        return {
            "success": True,
            "share_id": share_id,
            "platforms": results,
            "message": "Shared to social media platforms"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share to social media: {str(e)}"
        )

# ===== USER REPUTATION ENDPOINTS =====

@router.get("/reputation/{user_id}")
async def get_user_reputation(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user reputation and gamification data
    
    Args:
        user_id: User ID to get reputation for
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        User reputation and achievement data
    """
    try:
        # Get or create reputation
        if user_id not in user_reputations:
            user_reputations[user_id] = UserReputation(user_id)
        
        reputation = user_reputations[user_id]
        
        # Calculate level and achievements
        level = calculate_level(reputation.points)
        achievements = get_user_achievements(user_id, db)
        
        return {
            "success": True,
            "user_id": user_id,
            "reputation": {
                "points": reputation.points,
                "level": level,
                "accuracy_score": reputation.accuracy_score,
                "predictions_made": reputation.predictions_made,
                "predictions_correct": reputation.predictions_correct,
                "community_contributions": reputation.community_contributions,
                "last_updated": reputation.last_updated.isoformat()
            },
            "achievements": achievements
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user reputation: {str(e)}"
        )

# ===== HELPER FUNCTIONS =====

def update_user_reputation(user_id: str, action: str, points: int):
    """Update user reputation based on actions"""
    if user_id not in user_reputations:
        user_reputations[user_id] = UserReputation(user_id)
    
    reputation = user_reputations[user_id]
    reputation.points += points
    reputation.last_updated = datetime.utcnow()
    
    # Update specific metrics based on action
    if action == "prediction_shared":
        reputation.community_contributions += 1
    elif action == "post_created":
        reputation.community_contributions += 1

def get_user_info(user_id: str, db: Session) -> dict:
    """Get user information for display"""
    # Implement user lookup from database
    return {
        "id": user_id,
        "username": f"user_{user_id[:8]}",
        "avatar": None,
        "level": 1
    }

def get_prediction_info(prediction_id: str, db: Session) -> dict:
    """Get prediction information for display"""
    # Implement prediction lookup from database
    return {
        "id": prediction_id,
        "target_price": 50000,
        "confidence": 0.75,
        "timeframe": "1d"
    }

def calculate_leaderboard(category: str, timeframe: str, limit: int, db: Session) -> List[dict]:
    """Calculate leaderboard based on category and timeframe"""
    # Implement leaderboard calculation
    # This would typically query the database for user statistics
    
    # Mock data for now
    leaderboard = []
    for i in range(min(limit, 50)):
        leaderboard.append({
            "rank": i + 1,
            "user_id": f"user_{i}",
            "username": f"User{i}",
            "score": 1000 - (i * 10),
            "details": {
                "accuracy": 0.85 - (i * 0.01),
                "predictions": 100 - i,
                "reputation": 1000 - (i * 10)
            }
        })
    
    return leaderboard

def calculate_level(points: int) -> int:
    """Calculate user level based on points"""
    return max(1, points // 100 + 1)

def get_user_achievements(user_id: str, db: Session) -> List[dict]:
    """Get user achievements and badges"""
    # Implement achievement system
    return [
        {
            "id": "first_prediction",
            "name": "First Prediction",
            "description": "Made your first prediction",
            "earned_at": "2025-01-01T00:00:00Z",
            "icon": "��"
        }
    ]

def share_to_twitter(share: PredictionShare, user: dict) -> dict:
    """Share to Twitter (mock implementation)"""
    # Implement Twitter API integration
    return {
        "success": True,
        "tweet_id": "123456789",
        "url": "https://twitter.com/user/status/123456789"
    }

def share_to_reddit(share: PredictionShare, user: dict) -> dict:
    """Share to Reddit (mock implementation)"""
    # Implement Reddit API integration
    return {
        "success": True,
        "post_id": "abc123",
        "url": "https://reddit.com/r/cryptocurrency/comments/abc123"
    }

# ===== ADMIN ENDPOINTS =====

@router.post("/admin/moderate")
async def moderate_content(
    content_id: str,
    content_type: str,
    action: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(require_premium),
    db: Session = Depends(get_db)
):
    """
    Moderate community content (admin only)
    
    Args:
        content_id: ID of content to moderate
        content_type: Type of content (post, share, comment)
        action: Moderation action (hide, delete, warn)
        reason: Reason for moderation
        current_user: Current authenticated user (must be admin)
        db: Database session
    
    Returns:
        Moderation result
    """
    try:
        # Check admin permissions
        if current_user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Implement moderation logic
        if content_type == "post" and content_id in community_posts:
            post = community_posts[content_id]
            if action == "hide":
                post.is_locked = True
            elif action == "delete":
                del community_posts[content_id]
        
        # Log moderation action
        audit_repo = AuditRepository(db)
        audit_repo.log_activity(
            user_id=current_user["id"],
            action="content_moderated",
            details={
                "content_id": content_id,
                "content_type": content_type,
                "action": action,
                "reason": reason
            }
        )
        
        return {
            "success": True,
            "message": f"Content {action} successfully",
            "content_id": content_id,
            "action": action
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to moderate content: {str(e)}"
        ) 