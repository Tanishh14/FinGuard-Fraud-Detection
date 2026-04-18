"""
FinGuard Security Module
========================
Provides authentication, authorization, and RBAC (Role-Based Access Control).

Roles:
- end_user: Can generate transactions only
- fraud_analyst: Can view transactions, risk scores, explanations, and review flagged items
- admin: Full system access including model configs, thresholds, monitoring
- auditor: Read-only access to all data for compliance audits
"""
from datetime import datetime, timedelta
from typing import List, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.db.models import User, UserRole

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Optional OAuth2 scheme (doesn't raise error if token missing)
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ============================================================================
# Password Utilities
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    # Workaround for bcrypt 72 byte limit
    if len(password) > 72:
        import hashlib
        # Pre-hash long passwords using SHA256 hex digest (64 chars)
        password = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    if len(plain) > 72:
        import hashlib
        plain = hashlib.sha256(plain.encode()).hexdigest()
    return pwd_context.verify(plain, hashed)


# ============================================================================
# Token Utilities
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data (typically contains 'sub' for email, 'role', and 'name')
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Ensure standard claims are set
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "sub": str(data.get("sub", "")),
        "role": str(data.get("role", "customer")),
        "name": str(data.get("name", "User"))
    })
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGO)


def decode_token(token: str) -> dict:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGO])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )


# ============================================================================
# Database Dependency
# ============================================================================




# ============================================================================
# User Authentication
# ============================================================================

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    Checks Authorization header first, then fallback to 'access_token' cookie.
    """
    token = None
    
    # 1. Try Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    # 2. Fallback to HttpOnly Cookie
    if not token:
        token = request.cookies.get("access_token")
        
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    payload = decode_token(token)
    email = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token provided in header or cookie, None otherwise.
    """
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


# ============================================================================
# Role-Based Access Control (RBAC)
# ============================================================================

def require_roles(allowed_roles: List[str]):
    """
    Factory function to create role-checking dependency.
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user = Depends(require_roles(["admin"]))):
            ...
    """
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker


# Pre-built role checkers for common use cases

def admin_only(user: User = Depends(get_current_user)) -> User:
    """
    Require admin role.
    Admins have full system access.
    """
    if user.role != UserRole.ADMIN.value and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def fraud_analyst_only(user: User = Depends(get_current_user)) -> User:
    """
    Require fraud_analyst or admin role.
    Fraud analysts can review flagged transactions.
    """
    allowed = [UserRole.FRAUD_ANALYST.value, UserRole.ADMIN.value, "fraud_analyst", "admin"]
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fraud analyst access required"
        )
    return user


def auditor_only(user: User = Depends(get_current_user)) -> User:
    """
    Require auditor or admin role.
    Auditors have read-only access to all data.
    """
    allowed = [UserRole.AUDITOR.value, UserRole.ADMIN.value, "auditor", "admin"]
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Auditor access required"
        )
    return user


def analyst_or_auditor(user: User = Depends(get_current_user)) -> User:
    """
    Require fraud_analyst, auditor, or admin role.
    For endpoints accessible to both analysts and auditors.
    """
    allowed = [
        UserRole.FRAUD_ANALYST.value, 
        UserRole.AUDITOR.value, 
        UserRole.ADMIN.value,
        "fraud_analyst", "auditor", "admin"
    ]
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fraud analyst or auditor access required"
        )
    return user


def end_user_or_above(user: User = Depends(get_current_user)) -> User:
    """
    Any authenticated user (all roles allowed).
    This is essentially the same as get_current_user but more explicit.
    """
    return user


# ============================================================================
# Permission Helpers
# ============================================================================

def can_view_all_transactions(user: User) -> bool:
    """Check if user can view all transactions (not just their own)."""
    return user.role in [
        UserRole.FRAUD_ANALYST.value, 
        UserRole.AUDITOR.value, 
        UserRole.ADMIN.value,
        "fraud_analyst", "auditor", "admin"
    ]


def can_review_transactions(user: User) -> bool:
    """Check if user can review/approve/reject transactions."""
    return user.role in [
        UserRole.FRAUD_ANALYST.value, 
        UserRole.ADMIN.value,
        "fraud_analyst", "admin"
    ]


def can_modify_config(user: User) -> bool:
    """Check if user can modify system configuration."""
    return user.role in [UserRole.ADMIN.value, "admin"]


def can_export_data(user: User) -> bool:
    """Check if user can export audit data."""
    return user.role in [
        UserRole.AUDITOR.value, 
        UserRole.ADMIN.value,
        "auditor", "admin"
    ]


def filter_user_transactions(user: User, query):
    """
    Filter transaction query based on user role.
    End users only see their own transactions.
    Analysts/Auditors/Admins see all.
    """
    from app.db.models import Transaction
    
    if can_view_all_transactions(user):
        return query
    else:
        return query.filter(Transaction.user_id == user.id)
