from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models import User, UserOTP, UserBehaviorProfile

class AuthRepository:
    """
    Handles all database operations for the Authentication module.
    Responsible for Users and OTP persistence.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def create_user(self, user_data: Dict[str, Any]) -> User:
        user = User(**user_data)
        self.db.add(user)
        self.db.flush() # Get ID before commit
        
        # Every user needs a behavior profile baseline
        profile = UserBehaviorProfile(user_id=user.id)
        self.db.add(profile)
        
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_otp(self, otp_data: Dict[str, Any]) -> UserOTP:
        otp = UserOTP(**otp_data)
        self.db.add(otp)
        self.db.commit()
        return otp

    def get_active_otp(self, email: str, otp_type: str) -> Optional[UserOTP]:
        """Fetch the most recent unused and non-expired OTP."""
        from sqlalchemy import func
        return self.db.query(UserOTP).filter(
            func.lower(UserOTP.email) == func.lower(email),
            UserOTP.otp_type == otp_type,
            UserOTP.is_used == False,
            UserOTP.expires_at > datetime.utcnow()
        ).order_by(UserOTP.created_at.desc()).first()



    def mark_otp_as_used(self, otp: UserOTP):
        otp.is_used = True
        self.db.commit()

    def increment_otp_attempts(self, otp: UserOTP):
        otp.failed_attempts += 1
        self.db.commit()
