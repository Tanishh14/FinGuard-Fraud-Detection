from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core.config import settings
from app.db.session import get_db
from app.db.models import User

def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    # Try to get token from header first
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    # If not in header, try cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # DEVELOPMENT BYPASS: Allow test tokens for easier auditing and testing
    if token.startswith("test-token-"):
        role = token.replace("test-token-", "")
        email = f"{role}@finguard.test"
        
        # Check if mock user exists, if not create one
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                email=email,
                hashed_password="hashed_bypass",
                role=role
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGO]
        )
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def require_analyst(user: User = Depends(get_current_user)):
    if user.role not in ["fraud_analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Fraud Analyst or Admin access required")
    return user

def require_analyst_or_admin(user: User = Depends(get_current_user)):
    # Legacy support, maps to require_analyst
    return require_analyst(user)

def require_auditor_access(user: User = Depends(get_current_user)):
    if user.role not in ["auditor", "admin"]:
        raise HTTPException(status_code=403, detail="Auditor access required")
    return user
