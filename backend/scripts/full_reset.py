import sys
import os
from sqlalchemy import text

# Path fix - allows running from backend/ without setting PYTHONPATH
_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from app.db.session import engine
from app.db.models import Base

def full_reset():
    print("WARNING: This will delete ALL data and tables in the database.")
    print("Proceeding with nuclear database reset...")
    
    try:
        with engine.connect() as conn:
            # We need to end any transaction before dropping schema
            conn.execute(text("COMMIT"))
            
            # Nuclear option for Postgres
            print("Dropping public schema...")
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            conn.execute(text("COMMIT"))
            print("DONE: Public schema reset.")
        
        # Recreate all tables based on current models
        print("Recreating tables from models...")
        Base.metadata.create_all(bind=engine)
        print("DONE: All tables recreated.")
        
        print("\n[OK] Database completely cleared and reset.")
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}")

if __name__ == "__main__":
    full_reset()
