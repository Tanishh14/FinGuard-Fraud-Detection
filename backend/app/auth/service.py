import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, Response

from app.auth.repository import AuthRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.core.mail import mail_service
from app.core.config import settings
from app.db.models import User, UserOTP

class AuthService:
    """
    Business logic layer for Authentication.
    Orchestrates registration, login, 2FA, and session management.
    """
    
    def __init__(self, repo: AuthRepository):
        self.repo = repo

    def initiate_registration(self, payload: Dict[str, Any]):
        """Starts registration by sending an OTP."""
        if self.repo.get_user_by_email(payload['email']):
            raise HTTPException(400, "Email already registered")
            
        if self.repo.get_user_by_username(payload['username']):
            raise HTTPException(400, "Username already taken")

        otp_code = self._generate_secure_otp()
        
        # We store the full payload in reference_id to re-create the user later
        self.repo.create_otp({
            "email": payload['email'],
            "otp_code": otp_code,
            "otp_type": "registration",
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
            "reference_id": json.dumps(payload)
        })

        sent = mail_service.send_otp_email(payload['email'], otp_code, "Registration")
        if not sent:
            raise HTTPException(500, "Failed to send verification email.")
        
        return {"message": "Verification code sent to your email."}

    def verify_and_register(self, email: str, otp_code: str, response: Response):
        """Finalizes registration after OTP is verified."""
        otp = self._get_valid_otp(email, otp_code, "registration")
        
        reg_data = json.loads(otp.reference_id)
        user = self.repo.create_user({
            "email": reg_data['email'],
            "username": reg_data['username'],
            "hashed_password": hash_password(reg_data['password']),
            "role": reg_data.get('role', 'user'),
            "is_2fa_enabled": reg_data.get('is_2fa_enabled', False)
        })
        
        self.repo.mark_otp_as_used(otp)
        return self._create_session(user, response)

    def authenticate(self, email: str, password: str, response: Response):
        """Handles initial login attempt. Triggers 2FA if enabled."""
        user = self.repo.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(401, "Invalid email or password")

        if user.is_2fa_enabled:
            return self._trigger_login_mfa(user)

        return self._create_session(user, response)

    def verify_login_otp(self, email: str, otp_code: str, response: Response):
        """Verifies 2FA code during login."""
        otp = self._get_valid_otp(email, otp_code, "login")
        user = self.repo.get_user_by_email(email)
        
        self.repo.mark_otp_as_used(otp)
        return self._create_session(user, response)

    # --- Internal Helpers ---

    def _generate_secure_otp(self, length: int = 6) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(length))

    def _get_valid_otp(self, email: str, code: str, otp_type: str) -> UserOTP:
        """Centralized OTP verification with attempt tracking."""
        otp = self.repo.get_active_otp(email, otp_type)
        if not otp:
            raise HTTPException(401, "No active verification code found or code expired.")

        if otp.failed_attempts >= 3:
            self.repo.mark_otp_as_used(otp)
            raise HTTPException(403, "Too many failed attempts. Please request a new code.")

        # Strip whitespace just in case of frontend issues or copy-paste artifacts
        if otp.otp_code.strip() != code.strip():
            self.repo.increment_otp_attempts(otp)
            remaining = 3 - otp.failed_attempts
            raise HTTPException(401, f"Invalid code. {remaining} attempts remaining.")
            
        return otp


    def _trigger_login_mfa(self, user: User):
        """Generates and sends 2FA code."""
        otp_code = self._generate_secure_otp()
        self.repo.create_otp({
            "email": user.email,
            "otp_code": otp_code,
            "otp_type": "login",
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        })
        
        mail_service.send_otp_email(user.email, otp_code, "Login Verification")
        
        return {
            "access_token": "", 
            "token_type": "bearer",
            "role": user.role,
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "is_2fa_enabled": user.is_2fa_enabled,
            "require_otp": True
        }

    def _create_session(self, user: User, response: Response):
        """Generates JWT and sets HttpOnly cookie."""
        token = create_access_token({
            "sub": user.email, 
            "role": user.role,
            "name": user.username or user.email.split('@')[0]
        })
        
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="none",
            secure=False # Should be settings.PRODUCTION or similar in real app
        )
        
        return {
            "access_token": token, 
            "token_type": "bearer",
            "role": user.role,
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "is_2fa_enabled": user.is_2fa_enabled,
            "require_otp": False
        }
