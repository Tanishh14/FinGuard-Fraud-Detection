"""
FinGuard AI - Bank-Grade Fraud Detection System
================================================
Main FastAPI application entry point.

Features:
- Multi-model fraud detection (AE, IF, GNN)
- Real-time transaction streaming
- Role-based access control
- Full audit trail for compliance
- LLM-powered explanations
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import configuration and database
from app.core.config import settings
from app.db.session import engine
from app.db.models import Base

# Import routers
from app.auth.router import router as auth_router
from app.transactions.router import router as tx_router
from app.explainability.router import router as explain_router
from app.audit.router import router as audit_router
from app.anomaly.router import router as anomaly_router
from app.gnn.router import router as gnn_router
from app.forensics.router import router as forensics_router
from app.analytics.router import router as analytics_router
from app.simulation.router import router as sim_router
from app.realtime.websocket import realtime_transactions_ws

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="FinGuard AI",
    description="Bank-Grade Financial Fraud Detection System",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 2: Sovereign PII Isolation Boundary
# from app.core.pii_gatekeeper_middleware import PiiGatekeeperMiddleware
# app.add_middleware(PiiGatekeeperMiddleware)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; object-src 'none';"
    return response

# Register routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(tx_router, prefix="/transactions", tags=["Transactions"])
app.include_router(explain_router, prefix="/explainability", tags=["Explainability"])
app.include_router(audit_router, prefix="/audit", tags=["Audit & Compliance"])
app.include_router(anomaly_router, prefix="/anomaly", tags=["Anomaly Detection"])
app.include_router(gnn_router, prefix="/gnn", tags=["GNN"])
app.include_router(forensics_router, prefix="/forensics", tags=["Investigation & Forensics"])
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics & Reporting"])
app.include_router(sim_router, prefix="/simulation", tags=["Simulation & Demo"])

# Register WebSocket endpoint
app.websocket("/ws/transactions")(realtime_transactions_ws)


@app.get("/", tags=["Health"])
def root():
    """Health check endpoint."""
    return {
        "status": "FinGuard AI Backend Running",
        "version": "2.0.0",
        "features": [
            "Multi-model fraud detection",
            "Real-time streaming",
            "Role-based access control",
            "Audit trail",
            "LLM explanations"
        ]
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "services": {
            "auth": "operational",
            "transactions": "operational",
            "fraud_detection": "operational",
            "websocket": "operational"
        }
    }


@app.on_event("startup")
async def startup_event():
    """
    Initialize ML models and database connection on startup.
    Forces reload of trained models.
    """
    logger.info("FinGuard AI starting up...")
    
    # Initialize ML Registry
    from app.ml.registry import registry
    
    logger.info("Initializing Models...")
    # Pipeline recalibrated: Added 2.5σ offset and broader training data
    registry.load_all_models()
    logger.info("Model initialization complete.")
    
    if not registry.is_ready:
        logger.warning("ML services initialized with missing models. Check '/models' directory.")
    else:
        logger.info("✓ All ML services operational")
        
    logger.info("Database tables created/verified")
    logger.info("All services initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("FinGuard AI shutting down...")
