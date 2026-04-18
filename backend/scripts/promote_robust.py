import sys
import os

# Add the parent directory (backend) to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

from app.db.session import SessionLocal
from app.db.models import User, UserRole

def promote_latest_user():
    db = SessionLocal()
    try:
        # Get latest user
        user = db.query(User).order_by(User.id.desc()).first()
        if user:
            print(f"Promoting user {user.email} (ID: {user.id}) from {user.role} to ADMIN...")
            user.role = UserRole.ADMIN.value
            db.commit()
            print("Success! User is now an ADMIN.")
        else:
            print("No users found.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    promote_latest_user()
