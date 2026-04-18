"""
FinGuard API Schemas
=====================
Pydantic models for request/response validation.
Supports all user roles and transaction lifecycle.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class UserRoleEnum(str, Enum):
    END_USER = "end_user"
    FRAUD_ANALYST = "fraud_analyst"
    ADMIN = "admin"
    AUDITOR = "auditor"


class TransactionStatusEnum(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    BLOCKED = "BLOCKED"
    UNDER_REVIEW = "UNDER_REVIEW"


class AnalystActionEnum(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str
    role: str = "end_user"
    is_2fa_enabled: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    email: str
    username: Optional[str] = None
    is_2fa_enabled: bool = False
    require_otp: bool = False
    temp_token: Optional[str] = None
    
    model_config = {
        "protected_namespaces": ()
    }


class OTPVerifyRequest(BaseModel):
    email: str
    otp_code: str
    otp_type: str # registration, login, appeal
    reference_id: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    role: str
    is_active: bool
    is_2fa_enabled: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class TransactionIn(BaseModel):
    """Input schema for creating a new transaction."""
    user_id: int
    recipient_name: str
    merchant: str
    merchant_id: Optional[str] = None
    amount: float = Field(..., gt=0, description="Transaction amount (must be positive)")
    device_id: str
    ip_address: str
    location: str
    account_id: Optional[int] = None
    currency: str = "INR"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = {
        "protected_namespaces": ()
    }


class TransactionScores(BaseModel):
    """Score breakdown from all fraud detection models."""
    ae_score: float = Field(..., ge=0, le=1, description="Autoencoder anomaly score")
    if_score: float = Field(..., ge=0, le=1, description="Isolation Forest score")
    gnn_score: float = Field(..., ge=0, le=1, description="Graph Neural Network score")
    rule_score: float = Field(..., ge=0, le=1, description="Rule-based score")
    final_risk_score: float = Field(..., ge=0, le=1, description="Final fused risk score")


class TransactionOut(BaseModel):
    """Output schema for transaction details."""
    id: int
    user_id: int
    merchant: str
    amount: float
    currency: str = "INR"
    device_id: str
    ip_address: str
    location: str
    timestamp: datetime
    
    # User baseline at transaction time
    avg_user_spend: float
    std_user_spend: Optional[float] = 0.0
    user_tx_count: Optional[int] = 0
    
    # Multi-model scores
    ae_score: Optional[float] = 0.0
    if_score: Optional[float] = 0.0
    gnn_score: Optional[float] = 0.0
    rule_score: Optional[float] = 0.0
    final_risk_score: Optional[float] = 0.0
    risk_score: float = 0.0  # Legacy field
    
    # Risk analysis
    risk_flags: Optional[List[str]] = []
    
    # Decision
    status: str = "PENDING"
    decision: str = "PENDING"  # Legacy field
    auto_decision: Optional[str] = None
    
    # Explainability
    explanation: Optional[str] = None
    explanation_model: Optional[str] = None
    
    # Similarity Propagation
    similarity_triggered: bool = False
    inherited_from_transaction_id: Optional[int] = None
    
    # Review tracking
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Model metadata
    model_version: Optional[str] = None
    scoring_latency_ms: Optional[float] = None
    latency_ms: Optional[float] = None # Feature 3: Explicit Latency
    model_contributions: Optional[Dict[str, float]] = None # Feature 2: Contribution Breakdown
    intelligence: Optional[Dict[str, Any]] = None
    username: Optional[str] = None

    # Appeal Data
    is_appealed: bool = False
    appeal_reason: Optional[str] = None
    appeal_urgency: Optional[str] = None
    appeal_timestamp: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class TransactionProcessResult(BaseModel):
    """Full result from transaction processing pipeline."""
    transaction_id: int
    user_id: int
    amount: float
    merchant: str
    location: str
    timestamp: str
    scores: TransactionScores
    risk_flags: List[str]
    decision: str
    explanation: str
    model_version: str
    scoring_latency_ms: float
    audit_id: int
    
    # Similarity Propagation
    similarity_triggered: bool = False
    inherited_from_transaction_id: Optional[int] = None

    model_config = {
        "protected_namespaces": ()
    }


class TransactionStats(BaseModel):
    """Transaction statistics for dashboard."""
    total_transactions: int
    approved: int
    flagged: int
    blocked: int
    total_amount: float
    fraud_prevented_amount: float
    avg_risk_score: float
    approval_rate: float


# ============================================================================
# ANALYST REVIEW SCHEMAS
# ============================================================================

class ReviewRequest(BaseModel):
    """Request to review a flagged transaction."""
    action: AnalystActionEnum
    notes: Optional[str] = None


class ReviewQueueItem(BaseModel):
    """Item in the analyst review queue."""
    tx_id: int
    user_id: int
    amount: float
    merchant: str
    location: str
    timestamp: datetime
    risk_score: float
    status: str
    risk_flags: List[str]
    explanation: Optional[str]
    audit_id: Optional[int]

class AppealRequest(BaseModel):
    """Request to appeal a blocked transaction."""
    reason: str = Field(..., min_length=1, max_length=1000)
    urgency: str = "MEDIUM" # HIGH, MEDIUM, LOW


# ============================================================================
# AUDIT SCHEMAS
# ============================================================================

class AuditLogOut(BaseModel):
    """Audit log entry."""
    audit_id: int
    tx_id: int
    timestamp: datetime
    input_features: Dict[str, Any]
    user_profile_snapshot: Optional[Dict[str, Any]]
    scores: TransactionScores
    rule_flags: List[str]
    model_version: str
    threshold_config: Dict[str, float]
    auto_decision: str
    final_decision: str
    explanation: Optional[str]
    explanation_model: Optional[str]
    analyst_id: Optional[int]
    analyst_action: Optional[str]
    analyst_notes: Optional[str]
    analyst_action_time: Optional[datetime]
    scoring_latency_ms: Optional[float]

    model_config = {
        "protected_namespaces": ()
    }


class AuditExportRequest(BaseModel):
    """Request to export audit logs."""
    start_date: datetime
    end_date: datetime
    format: str = "json"  # json or csv


# ============================================================================
# USER PROFILE SCHEMAS
# ============================================================================

class UserProfileOut(BaseModel):
    """User behavioral profile."""
    user_id: int
    avg_amount: float
    std_amount: float
    min_amount: Optional[float]
    max_amount: Optional[float]
    tx_per_day: float
    total_tx_count: int
    night_tx_ratio: float
    weekend_tx_ratio: float
    geo_entropy: float
    top_merchants: Dict[str, int]
    top_locations: Dict[str, int]
    known_devices: List[str]
    profile_maturity: str
    last_updated: Optional[datetime]

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


# ============================================================================
# ADMIN SCHEMAS
# ============================================================================

class ModelConfigIn(BaseModel):
    """Input for model configuration update."""
    name: str
    flag_threshold: float = Field(..., ge=0, le=1)
    block_threshold: float = Field(..., ge=0, le=1)
    ae_weight: float = Field(..., ge=0, le=1)
    if_weight: float = Field(..., ge=0, le=1)
    gnn_weight: float = Field(..., ge=0, le=1)
    rule_weight: float = Field(..., ge=0, le=1)

    @field_validator('block_threshold')
    def block_must_be_higher(cls, v, values):
        if 'flag_threshold' in values and v < values['flag_threshold']:
            raise ValueError('block_threshold must be >= flag_threshold')
        return v


class ModelConfigOut(BaseModel):
    """Model configuration."""
    id: int
    name: str
    is_active: bool
    flag_threshold: float
    block_threshold: float
    ae_weight: float
    if_weight: float
    gnn_weight: float
    rule_weight: float
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "protected_namespaces": ()
    }


class ModelHealthStats(BaseModel):
    """Model performance statistics."""
    total_transactions: int
    auto_approved: int
    auto_flagged: int
    auto_blocked: int
    analyst_reviewed: int
    false_positive_rate: float
    false_negative_rate: float
    avg_scoring_latency_ms: float

    model_config = {
        "protected_namespaces": ()
    }


# ============================================================================
# WEBSOCKET SCHEMAS
# ============================================================================

class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # NEW_TRANSACTION, ANALYST_ACTION, SYSTEM_ALERT
    data: Dict[str, Any]
