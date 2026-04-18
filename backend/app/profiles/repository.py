from typing import Optional, List
from sqlalchemy.orm import Session
from app.db.models import UserBehaviorProfile, Transaction

class ProfilesRepository:
    """
    Handles all database operations for the User Profiles module.
    """
    
    def __init__(self, db: Session):
        self.db = db

    def get_profile_by_user_id(self, user_id: int) -> Optional[UserBehaviorProfile]:
        return self.db.query(UserBehaviorProfile).filter(UserBehaviorProfile.user_id == user_id).first()

    def create_profile(self, user_id: int) -> UserBehaviorProfile:
        profile = UserBehaviorProfile(user_id=user_id)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_profile(self, profile: UserBehaviorProfile, update_data: dict) -> UserBehaviorProfile:
        for key, value in update_data.items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_profile(self, profile: UserBehaviorProfile):
        self.db.delete(profile)
        self.db.commit()

    def get_all_profiles(self) -> List[UserBehaviorProfile]:
        return self.db.query(UserBehaviorProfile).all()
