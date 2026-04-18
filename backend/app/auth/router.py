from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import User
from app.core.dependencies import get_db, get_current_user
from app.schemas.api import RegisterRequest, LoginRequest, TokenResponse, OTPVerifyRequest
from app.auth.service import AuthService
from app.auth.repository import AuthRepository

router = APIRouter(tags=["Authentication"])

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    repo = AuthRepository(db)
    return AuthService(repo)

@router.post("/register")
def register(payload: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.initiate_registration(payload.model_dump())

@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, 
    response: Response, 
    auth_service: AuthService = Depends(get_auth_service)
):
    return auth_service.authenticate(payload.email, payload.password, response)

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    payload: OTPVerifyRequest, 
    response: Response, 
    auth_service: AuthService = Depends(get_auth_service)
):
    if payload.otp_type == "registration":
        return auth_service.verify_and_register(payload.email, payload.otp_code, response)
    
    return auth_service.verify_login_otp(payload.email, payload.otp_code, response)

@router.post("/logout")
def logout(response: Response, auth_service: AuthService = Depends(get_auth_service)):
    # Standard logout: just clear the cookie
    response.delete_cookie(key="access_token", httponly=True, samesite="none", secure=False)
    return {"message": "Logged out successfully"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return the current user's profile information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_2fa_enabled": current_user.is_2fa_enabled,
        "created_at": current_user.created_at
    }

@router.post("/toggle-2fa")
def toggle_2fa(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Note: This remains in the router for now as it's a simple toggle, 
    but could be moved to profile service later."""
    current_user.is_2fa_enabled = not current_user.is_2fa_enabled
    db.commit()
    return {"message": "2FA status updated", "is_2fa_enabled": current_user.is_2fa_enabled}
