#!/usr/bin/env python3
"""
Advanced Security System for BTC Forecast Application
API key management, OAuth integration, and enhanced security features
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
import secrets
import hashlib
import hmac
import base64
import json
import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from enum import Enum

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Security schemes
security = HTTPBearer()

class PermissionLevel(Enum):
    """Permission levels for API access"""
    READ_ONLY = "read_only"
    STANDARD = "standard"
    PREMIUM = "premium"
    ADMIN = "admin"

class SecurityLevel(Enum):
    """Security levels for different operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class APIKey(BaseModel):
    """API Key model."""
    key_id: str
    user_id: str
    name: str
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    is_active: bool

class OAuthToken(BaseModel):
    """OAuth token model."""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str]
    scope: Optional[str]

class SecurityAuditLog(BaseModel):
    """Security audit log model."""
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource: str
    ip_address: str
    user_agent: str
    success: bool
    details: Optional[Dict[str, Any]]

class AdvancedSecurity:
    """
    Advanced security system with comprehensive security features
    """
    
    def __init__(self):
        self.settings = settings
        self.api_keys = {}  # In-memory storage (use database in production)
        self.oauth_tokens = {}  # In-memory storage (use database in production)
        self.audit_logs = []  # In-memory storage (use database in production)
        self.encryption_key = self._generate_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self.rsa_private_key = None
        self.rsa_public_key = None
        self._setup_rsa_keys()
        
        # Security policies
        self.security_policies = {
            "password_min_length": 12,
            "password_require_uppercase": True,
            "password_require_lowercase": True,
            "password_require_numbers": True,
            "password_require_special": True,
            "max_login_attempts": 5,
            "lockout_duration_minutes": 30,
            "session_timeout_minutes": 60,
            "api_key_expiry_days": 365,
            "oauth_token_expiry_minutes": 60
        }
        
        # Rate limiting
        self.rate_limits = {
            PermissionLevel.READ_ONLY: {"requests_per_minute": 60},
            PermissionLevel.STANDARD: {"requests_per_minute": 300},
            PermissionLevel.PREMIUM: {"requests_per_minute": 1000},
            PermissionLevel.ADMIN: {"requests_per_minute": 5000}
        }
        
        # Initialize security features
        self._setup_security_features()
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key"""
        try:
            # Use existing key if available
            if hasattr(settings, 'ENCRYPTION_KEY') and settings.ENCRYPTION_KEY:
                return base64.urlsafe_b64decode(settings.ENCRYPTION_KEY)
            
            # Generate new key
            key = Fernet.generate_key()
            logger.info("Generated new encryption key")
            return key
            
        except Exception as e:
            logger.error(f"Failed to generate encryption key: {e}")
            raise
    
    def _setup_rsa_keys(self):
        """Setup RSA keys for asymmetric encryption"""
        try:
            # Generate RSA key pair
            self.rsa_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.rsa_public_key = self.rsa_private_key.public_key()
            
            logger.info("RSA keys generated successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup RSA keys: {e}")
    
    def _setup_security_features(self):
        """Setup security features."""
        try:
            # Generate RSA key pair for asymmetric encryption
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
            
            # Save public key
            public_key_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            with open("security/public_key.pem", "wb") as f:
                f.write(public_key_pem)
            
            logger.info("Security features initialized")
            
        except Exception as e:
            logger.error(f"Security features setup failed: {e}")
    
    def create_api_key(self, user_id: str, permission_level: PermissionLevel, 
                      description: str = None, expiry_days: int = None) -> Dict[str, Any]:
        """
        Create a new API key for a user
        
        Args:
            user_id: User ID
            permission_level: Permission level for the API key
            description: Optional description for the key
            expiry_days: Days until key expires (uses default if None)
            
        Returns:
            Dict containing API key details
        """
        try:
            # Generate API key
            api_key_id = secrets.token_urlsafe(32)
            api_key_secret = secrets.token_urlsafe(64)
            
            # Hash the secret for storage
            hashed_secret = hashlib.sha256(api_key_secret.encode()).hexdigest()
            
            # Set expiry
            if expiry_days is None:
                expiry_days = self.security_policies["api_key_expiry_days"]
            
            expiry_date = datetime.now() + timedelta(days=expiry_days)
            
            # Create API key record
            api_key_data = {
                "id": api_key_id,
                "user_id": user_id,
                "hashed_secret": hashed_secret,
                "permission_level": permission_level.value,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "expires_at": expiry_date.isoformat(),
                "is_active": True,
                "last_used": None,
                "usage_count": 0
            }
            
            # Store API key (this would save to database)
            self._store_api_key(api_key_data)
            
            # Log security event
            self.log_security_event(
                "api_key_created",
                user_id=user_id,
                api_key_id=api_key_id,
                permission_level=permission_level.value
            )
            
            # Return API key details (secret only shown once)
            return {
                "api_key_id": api_key_id,
                "api_key_secret": api_key_secret,  # Only returned once
                "permission_level": permission_level.value,
                "description": description,
                "expires_at": expiry_date.isoformat(),
                "created_at": api_key_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise
    
    def validate_api_key(self, api_key_id: str, api_key_secret: str) -> Optional[Dict[str, Any]]:
        """
        Validate an API key
        
        Args:
            api_key_id: API key ID
            api_key_secret: API key secret
            
        Returns:
            API key data if valid, None otherwise
        """
        try:
            # Get API key from storage
            api_key_data = self._get_api_key(api_key_id)
            
            if not api_key_data:
                logger.warning(f"API key not found: {api_key_id}")
                return None
            
            # Check if key is active
            if not api_key_data.get("is_active", False):
                logger.warning(f"API key is inactive: {api_key_id}")
                return None
            
            # Check if key is expired
            expires_at = datetime.fromisoformat(api_key_data["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(f"API key is expired: {api_key_id}")
                self._deactivate_api_key(api_key_id)
                return None
            
            # Validate secret
            hashed_secret = hashlib.sha256(api_key_secret.encode()).hexdigest()
            if not hmac.compare_digest(api_key_data["hashed_secret"], hashed_secret):
                logger.warning(f"Invalid API key secret: {api_key_id}")
                return None
            
            # Update usage statistics
            self._update_api_key_usage(api_key_id)
            
            # Log successful validation
            self.log_security_event(
                "api_key_validated",
                user_id=api_key_data["user_id"],
                api_key_id=api_key_id
            )
            
            return api_key_data
            
        except Exception as e:
            logger.error(f"Failed to validate API key: {e}")
            return None
    
    def revoke_api_key(self, api_key_id: str, user_id: str = None) -> bool:
        """
        Revoke an API key
        
        Args:
            api_key_id: API key ID to revoke
            user_id: User ID (for verification)
            
        Returns:
            True if revoked successfully, False otherwise
        """
        try:
            # Get API key data
            api_key_data = self._get_api_key(api_key_id)
            
            if not api_key_data:
                logger.warning(f"API key not found for revocation: {api_key_id}")
                return False
            
            # Verify user ownership if provided
            if user_id and api_key_data["user_id"] != user_id:
                logger.warning(f"User {user_id} attempted to revoke API key {api_key_id} owned by {api_key_data['user_id']}")
                return False
            
            # Deactivate API key
            self._deactivate_api_key(api_key_id)
            
            # Log security event
            self.log_security_event(
                "api_key_revoked",
                user_id=api_key_data["user_id"],
                api_key_id=api_key_id,
                revoked_by=user_id
            )
            
            logger.info(f"API key revoked: {api_key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return False
    
    def create_oauth_token(self, user_id: str, client_id: str, scope: List[str], 
                          token_type: str = "access") -> Dict[str, Any]:
        """
        Create OAuth token
        
        Args:
            user_id: User ID
            client_id: OAuth client ID
            scope: List of scopes
            token_type: Type of token (access, refresh)
            
        Returns:
            Dict containing OAuth token details
        """
        try:
            # Generate token
            token = secrets.token_urlsafe(64)
            
            # Set expiry based on token type
            if token_type == "access":
                expiry_minutes = self.security_policies["oauth_token_expiry_minutes"]
            else:  # refresh token
                expiry_minutes = 60 * 24 * 30  # 30 days
            
            expiry_date = datetime.now() + timedelta(minutes=expiry_minutes)
            
            # Create token data
            token_data = {
                "token": token,
                "user_id": user_id,
                "client_id": client_id,
                "scope": scope,
                "token_type": token_type,
                "created_at": datetime.now().isoformat(),
                "expires_at": expiry_date.isoformat(),
                "is_active": True
            }
            
            # Store token
            self._store_oauth_token(token_data)
            
            # Log security event
            self.log_security_event(
                "oauth_token_created",
                user_id=user_id,
                client_id=client_id,
                token_type=token_type,
                scope=scope
            )
            
            return {
                "access_token": token if token_type == "access" else None,
                "refresh_token": token if token_type == "refresh" else None,
                "token_type": token_type,
                "expires_in": expiry_minutes * 60,  # seconds
                "scope": scope
            }
            
        except Exception as e:
            logger.error(f"Failed to create OAuth token: {e}")
            raise
    
    def validate_oauth_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate OAuth token
        
        Args:
            token: OAuth token to validate
            
        Returns:
            Token data if valid, None otherwise
        """
        try:
            # Get token data
            token_data = self._get_oauth_token(token)
            
            if not token_data:
                logger.warning(f"OAuth token not found: {token[:10]}...")
                return None
            
            # Check if token is active
            if not token_data.get("is_active", False):
                logger.warning(f"OAuth token is inactive: {token[:10]}...")
                return None
            
            # Check if token is expired
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(f"OAuth token is expired: {token[:10]}...")
                self._deactivate_oauth_token(token)
                return None
            
            # Log successful validation
            self.log_security_event(
                "oauth_token_validated",
                user_id=token_data["user_id"],
                client_id=token_data["client_id"]
            )
            
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to validate OAuth token: {e}")
            return None
    
    def encrypt_data(self, data: Union[str, bytes, Dict[str, Any]]) -> str:
        """
        Encrypt data using Fernet symmetric encryption
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        try:
            # Convert data to bytes if needed
            if isinstance(data, dict):
                data_bytes = json.dumps(data).encode()
            elif isinstance(data, str):
                data_bytes = data.encode()
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                raise ValueError("Data must be string, bytes, or dict")
            
            # Encrypt data
            encrypted_data = self.fernet.encrypt(data_bytes)
            
            # Return as base64 string
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> Union[str, Dict[str, Any]]:
        """
        Decrypt data using Fernet symmetric encryption
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted data
        """
        try:
            # Decode base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt data
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            
            # Try to parse as JSON first, then as string
            try:
                return json.loads(decrypted_bytes.decode())
            except json.JSONDecodeError:
                return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise
    
    def encrypt_asymmetric(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data using RSA asymmetric encryption
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        try:
            # Convert data to bytes if needed
            if isinstance(data, str):
                data_bytes = data.encode()
            elif isinstance(data, bytes):
                data_bytes = data
            else:
                raise ValueError("Data must be string or bytes")
            
            # Encrypt using public key
            encrypted_data = self.rsa_public_key.encrypt(
                data_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Return as base64 string
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt data asymmetrically: {e}")
            raise
    
    def decrypt_asymmetric(self, encrypted_data: str) -> str:
        """
        Decrypt data using RSA asymmetric encryption
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted data as string
        """
        try:
            # Decode base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            
            # Decrypt using private key
            decrypted_bytes = self.rsa_private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"Failed to decrypt data asymmetrically: {e}")
            raise
    
    def hash_password(self, password: str, salt: str = None) -> Dict[str, str]:
        """
        Hash password using PBKDF2
        
        Args:
            password: Password to hash
            salt: Optional salt (generates new one if None)
            
        Returns:
            Dict containing hash and salt
        """
        try:
            if salt is None:
                salt = secrets.token_hex(32)
            
            # Generate hash using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            
            hash_bytes = kdf.derive(password.encode())
            hash_hex = base64.urlsafe_b64encode(hash_bytes).decode()
            
            return {
                "hash": hash_hex,
                "salt": salt
            }
            
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise
    
    def verify_password(self, password: str, hash_value: str, salt: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Password to verify
            hash_value: Stored hash
            salt: Stored salt
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            # Generate hash for comparison
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            
            hash_bytes = kdf.derive(password.encode())
            hash_hex = base64.urlsafe_b64encode(hash_bytes).decode()
            
            return hmac.compare_digest(hash_value, hash_hex)
            
        except Exception as e:
            logger.error(f"Failed to verify password: {e}")
            return False
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            warnings = []
            
            # Check minimum length
            if len(password) < self.security_policies["password_min_length"]:
                errors.append(f"Password must be at least {self.security_policies['password_min_length']} characters")
            
            # Check for uppercase
            if self.security_policies["password_require_uppercase"] and not any(c.isupper() for c in password):
                errors.append("Password must contain at least one uppercase letter")
            
            # Check for lowercase
            if self.security_policies["password_require_lowercase"] and not any(c.islower() for c in password):
                errors.append("Password must contain at least one lowercase letter")
            
            # Check for numbers
            if self.security_policies["password_require_numbers"] and not any(c.isdigit() for c in password):
                errors.append("Password must contain at least one number")
            
            # Check for special characters
            if self.security_policies["password_require_special"] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                errors.append("Password must contain at least one special character")
            
            # Check for common patterns
            if password.lower() in ["password", "123456", "qwerty", "admin"]:
                warnings.append("Password is too common")
            
            # Check for sequential characters
            if any(password[i:i+3] in "abcdefghijklmnopqrstuvwxyz" for i in range(len(password)-2)):
                warnings.append("Password contains sequential characters")
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "strength_score": self._calculate_password_strength(password)
            }
            
        except Exception as e:
            logger.error(f"Failed to validate password strength: {e}")
            return {"is_valid": False, "errors": ["Password validation failed"], "warnings": [], "strength_score": 0}
    
    def _calculate_password_strength(self, password: str) -> int:
        """Calculate password strength score (0-100)"""
        try:
            score = 0
            
            # Length contribution
            score += min(len(password) * 4, 40)
            
            # Character variety contribution
            if any(c.isupper() for c in password):
                score += 10
            if any(c.islower() for c in password):
                score += 10
            if any(c.isdigit() for c in password):
                score += 10
            if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
                score += 10
            
            # Complexity bonus
            unique_chars = len(set(password))
            score += min(unique_chars * 2, 20)
            
            return min(score, 100)
            
        except Exception as e:
            logger.error(f"Failed to calculate password strength: {e}")
            return 0
    
    def check_permission(self, user_permission: PermissionLevel, required_permission: PermissionLevel) -> bool:
        """
        Check if user has required permission level
        
        Args:
            user_permission: User's permission level
            required_permission: Required permission level
            
        Returns:
            True if user has sufficient permissions, False otherwise
        """
        try:
            permission_hierarchy = {
                PermissionLevel.READ_ONLY: 1,
                PermissionLevel.STANDARD: 2,
                PermissionLevel.PREMIUM: 3,
                PermissionLevel.ADMIN: 4
            }
            
            user_level = permission_hierarchy.get(user_permission, 0)
            required_level = permission_hierarchy.get(required_permission, 0)
            
            return user_level >= required_level
            
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return False
    
    def get_rate_limit(self, permission_level: PermissionLevel) -> Dict[str, int]:
        """
        Get rate limit for permission level
        
        Args:
            permission_level: Permission level
            
        Returns:
            Rate limit configuration
        """
        try:
            return self.rate_limits.get(permission_level, {"requests_per_minute": 60})
        except Exception as e:
            logger.error(f"Failed to get rate limit: {e}")
            return {"requests_per_minute": 60}
    
    def log_security_event(self, event_type: str, **kwargs):
        """
        Log security event
        
        Args:
            event_type: Type of security event
            **kwargs: Additional event data
        """
        try:
            event_data = {
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "ip_address": kwargs.get("ip_address"),
                "user_agent": kwargs.get("user_agent"),
                **kwargs
            }
            
            # Log to security log
            logger.warning(f"Security event: {event_type}", extra=event_data)
            
            # Store in database (this would save to security_events table)
            self._store_security_event(event_data)
            
            # Check for suspicious activity
            self._check_suspicious_activity(event_data)
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    def _check_suspicious_activity(self, event_data: Dict[str, Any]):
        """Check for suspicious activity patterns"""
        try:
            # Implementation to detect suspicious activity
            # This would analyze patterns and trigger alerts if needed
            pass
        except Exception as e:
            logger.error(f"Failed to check suspicious activity: {e}")
    
    # Database operations (placeholder implementations)
    def _store_api_key(self, api_key_data: Dict[str, Any]):
        """Store API key in database"""
        # Implementation would save to database
        pass
    
    def _get_api_key(self, api_key_id: str) -> Optional[Dict[str, Any]]:
        """Get API key from database"""
        # Implementation would retrieve from database
        return None
    
    def _update_api_key_usage(self, api_key_id: str):
        """Update API key usage statistics"""
        # Implementation would update database
        pass
    
    def _deactivate_api_key(self, api_key_id: str):
        """Deactivate API key"""
        # Implementation would update database
        pass
    
    def _store_oauth_token(self, token_data: Dict[str, Any]):
        """Store OAuth token in database"""
        # Implementation would save to database
        pass
    
    def _get_oauth_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get OAuth token from database"""
        # Implementation would retrieve from database
        return None
    
    def _deactivate_oauth_token(self, token: str):
        """Deactivate OAuth token"""
        # Implementation would update database
        pass
    
    def _store_security_event(self, event_data: Dict[str, Any]):
        """Store security event in database"""
        # Implementation would save to database
        pass

# Global security instance
security_system = AdvancedSecurity()

# Dependency functions for FastAPI
async def get_current_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> APIKey:
    """Get current API key from request."""
    try:
        api_key = credentials.credentials
        api_key_record = security_system.validate_api_key(api_key)
        
        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        return api_key_record
        
    except Exception as e:
        logger.error(f"API key validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

async def get_current_oauth_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current OAuth user from request."""
    try:
        access_token = credentials.credentials
        payload = security_system.validate_oauth_token(access_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OAuth token"
            )
        
        return payload
        
    except Exception as e:
        logger.error(f"OAuth token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OAuth token"
        )

def require_permission(required_permission: PermissionLevel):
    """Decorator to require specific permission level"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract API key from request
            request = kwargs.get('request')
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request object not found"
                )
            
            # Get API key from headers
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required"
                )
            
            # Validate API key
            api_key_record = security_system.validate_api_key(api_key)
            if not api_key_record:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            
            # Check permission
            if not security_system.check_permission(api_key_record, required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{required_permission}' required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_security_system() -> AdvancedSecurity:
    """Get the global security system instance."""
    return security_system 