import os
from pydantic_settings import BaseSettings

# Get directory of THIS file (app/core)
core_dir = os.path.dirname(os.path.abspath(__file__))
# app dir
app_dir = os.path.dirname(core_dir)
# backend dir
backend_dir = os.path.dirname(app_dir)
db_path = os.path.join(backend_dir, "finguard_v2.db")

class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{db_path}"
    JWT_SECRET: str = "DYNAMIC_SECRET_REQUIRED"
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "finguard@example.com"
    USE_CONSOLE_MAILER: bool = True
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS Configuration - Must specify exact origins for credentials to work
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return origins if origins else ["http://localhost:3000", "http://localhost:5173"]

    model_config = {
        "env_file": os.path.join(backend_dir, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
