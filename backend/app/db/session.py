from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from app.core.config import settings
import math

class StandardDeviation:
    def __init__(self):
        self.M = 0.0
        self.S = 0.0
        self.k = 0

    def step(self, value):
        if value is None:
            return
        try:
            val = float(value)
        except (ValueError, TypeError):
            return
        self.k += 1
        delta = val - self.M
        self.M += delta / self.k
        self.S += delta * (val - self.M)

    def finalize(self):
        if self.k < 2:
            return 0.0
        return math.sqrt(self.S / (self.k - 1))

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Only execute for SQLite connections
    cursor = dbapi_connection.cursor()
    # Check if this is a SQLite connection by looking for specific SQLite attributes/methods
    # or simply by checking the connection class name safely
    conn_type = str(type(dbapi_connection)).lower()
    
    if "sqlite" in conn_type:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Register custom aggregate function only for SQLite
        # PostgreSQL has native STDDEV support
        try:
            dbapi_connection.create_aggregate("stddev", 1, StandardDeviation)
        except Exception:
            pass
    
    cursor.close()

engine = create_engine(
    settings.DATABASE_URL, 
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=40
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
