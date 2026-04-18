"""
FinGuard Bank-Grade Database Models
====================================
Comprehensive schema for production-ready fraud detection system
with full regulatory compliance and audit capabilities.

Roles:
- end_user: Generates transactions only
- fraud_analyst: Views transactions, risk scores, explanations
- admin: Model configs, thresholds, system monitoring
- auditor: Read-only access, full traceability
"""
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, 
    Index, Boolean, Text, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    END_USER = "end_user"
    FRAUD_ANALYST = "fraud_analyst"
    ADMIN = "admin"
    AUDITOR = "auditor"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class AnalystAction(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class MerchantRiskLevel(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"


# ============================================================================
# USER & AUTHENTICATION MODELS
# ============================================================================

class User(Base):
    """
    Extended User model with RBAC support.
    Roles: end_user, fraud_analyst, admin, auditor
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    
    # RBAC
    role = Column(String(50), default=UserRole.END_USER.value, index=True)
    is_active = Column(Boolean, default=True)
    is_2fa_enabled = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="user", foreign_keys="Transaction.user_id")
    behavior_profile = relationship("UserBehaviorProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    devices = relationship("UserDevice", back_populates="user")
    accounts = relationship("UserAccount", back_populates="user")
    reviewed_transactions = relationship("Transaction", back_populates="reviewer", foreign_keys="Transaction.reviewed_by")
    audit_actions = relationship("AuditLog", back_populates="analyst", foreign_keys="AuditLog.analyst_id")
    assigned_cases = relationship("InvestigationCase", back_populates="analyst")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# ============================================================================
# USER BEHAVIOR PROFILE (Online Learning)
# ============================================================================

class UserBehaviorProfile(Base):
    """
    Persistent behavioral baseline for each user.
    Updated incrementally after each transaction (online learning).
    Used by anomaly detection models and rule-based checks.
    """
    __tablename__ = "user_behavior_profiles"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    
    # Spending Statistics (Welford's algorithm for incremental updates)
    avg_amount = Column(Float, default=0.0)
    std_amount = Column(Float, default=0.0)
    min_amount = Column(Float, nullable=True)
    max_amount = Column(Float, nullable=True)
    
    # For Welford's online variance calculation
    _m2 = Column(Float, default=0.0)  # Sum of squared differences
    
    # Transaction Frequency
    tx_per_day = Column(Float, default=0.0)
    total_tx_count = Column(Integer, default=0)
    
    # Time Patterns
    night_tx_ratio = Column(Float, default=0.0)  # 10PM-6AM transactions ratio
    night_tx_count = Column(Integer, default=0)
    weekend_tx_ratio = Column(Float, default=0.0)
    weekend_tx_count = Column(Integer, default=0)
    
    # Geographic Patterns
    geo_entropy = Column(Float, default=0.0)  # Location diversity
    top_locations = Column(JSON, default=dict)  # {location: count}
    
    # Merchant Patterns
    top_merchants = Column(JSON, default=dict)  # {merchant: count}
    merchant_category_dist = Column(JSON, default=dict)  # {category: count}
    
    # Device Patterns
    known_devices = Column(JSON, default=list)  # List of device_ids
    known_ips = Column(JSON, default=list)  # List of IP ranges
    
    # Velocity Tracking
    last_tx_timestamp = Column(DateTime, nullable=True)
    tx_count_last_hour = Column(Integer, default=0)
    tx_count_last_day = Column(Integer, default=0)
    amount_last_hour = Column(Float, default=0.0)
    amount_last_day = Column(Float, default=0.0)
    
    # Profile Metadata
    first_tx_date = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    profile_maturity = Column(String(20), default="new")  # new, developing, mature
    
    # Relationship
    user = relationship("User", back_populates="behavior_profile")

    def __repr__(self):
        return f"<UserBehaviorProfile user_id={self.user_id} tx_count={self.total_tx_count}>"


class UserOTP(Base):
    """
    Stores temporary OTPs for various verification flows.
    """
    __tablename__ = "user_otps"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True, nullable=False)
    otp_code = Column(String(10), nullable=False)
    otp_type = Column(String(50), nullable=False) # registration, login, appeal
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    failed_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for specific flows
    reference_id = Column(Text, nullable=True) # e.g. tx_id or JSON payload
    
    def __repr__(self):
        return f"<UserOTP {self.email} type={self.otp_type} used={self.is_used}>"


# ============================================================================
# DEVICE & ACCOUNT LINKING
# ============================================================================

class UserDevice(Base):
    """
    Track devices associated with users for fraud ring detection.
    Devices shared across multiple users may indicate collusion.
    """
    __tablename__ = "user_devices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    device_id = Column(String(255), index=True, nullable=False)
    device_fingerprint = Column(String(512), nullable=True)  # Browser/device fingerprint
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    
    # Trust & Risk
    trust_score = Column(Float, default=0.5)  # 0.0 (untrusted) to 1.0 (trusted)
    is_verified = Column(Boolean, default=False)
    
    # Usage Tracking
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    tx_count = Column(Integer, default=0)
    
    # Relationship
    user = relationship("User", back_populates="devices")

    __table_args__ = (
        Index("idx_device_user", "device_id", "user_id"),
    )

    def __repr__(self):
        return f"<UserDevice {self.device_id} user={self.user_id}>"


class UserAccount(Base):
    """
    Bank accounts linked to users.
    Supports multiple accounts per user.
    """
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_number = Column(String(50), unique=True, index=True)
    account_type = Column(String(50))  # savings, current, credit, wallet
    
    # Account Status
    is_active = Column(Boolean, default=True)
    is_primary = Column(Boolean, default=False)
    
    # Limits
    daily_limit = Column(Float, nullable=True)
    monthly_limit = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

    def __repr__(self):
        return f"<UserAccount {self.account_number} ({self.account_type})>"


# ============================================================================
# MERCHANT PROFILES
# ============================================================================

class MerchantProfile(Base):
    """
    Merchant risk profiles and statistics.
    Used for merchant-level fraud detection.
    """
    __tablename__ = "merchant_profiles"

    merchant_id = Column(String(255), primary_key=True, index=True)
    merchant_name = Column(String(255), nullable=False)
    category = Column(String(100), index=True)  # retail, food, travel, crypto, gambling
    
    # Risk Assessment
    risk_level = Column(String(20), default=MerchantRiskLevel.NORMAL.value)
    risk_score = Column(Float, default=0.0)
    is_verified = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    
    # Statistics
    avg_transaction = Column(Float, default=0.0)
    total_tx_count = Column(Integer, default=0)
    fraud_tx_count = Column(Integer, default=0)
    fraud_rate = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = relationship("Transaction", back_populates="merchant_profile")

    def __repr__(self):
        return f"<MerchantProfile {self.merchant_name} ({self.risk_level})>"


# ============================================================================
# TRANSACTION MODEL (Extended)
# ============================================================================

class Transaction(Base):
    """
    Extended transaction model with multi-model scoring,
    explainability, and full audit trail support.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Core Transaction Data
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    account_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=True)
    merchant_id = Column(String(255), ForeignKey("merchant_profiles.merchant_id"), nullable=True)
    merchant = Column(String(255), index=True)  # Merchant name for display
    recipient_name = Column(String(255), index=True, nullable=True) # Full name or account of recipient
    
    # Transaction Details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    device_id = Column(String(255), index=True)
    ip_address = Column(String(50), index=True)
    location = Column(String(255))
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # User Baseline at Transaction Time (snapshot)
    avg_user_spend = Column(Float, default=0.0)
    std_user_spend = Column(Float, default=0.0)
    user_tx_count = Column(Integer, default=0)
    
    # Multi-Model Risk Scores (0.0 - 1.0)
    ae_score = Column(Float, default=0.0)  # Autoencoder anomaly score
    if_score = Column(Float, default=0.0)  # Isolation Forest score
    anomaly_score = Column(Float, default=0.0)  # Combined anomaly score
    gnn_score = Column(Float, default=0.0)  # Graph Neural Network score
    rule_score = Column(Float, default=0.0)  # Rule-based score
    final_risk_score = Column(Float, default=0.0)  # Fused final score
    
    # Legacy compatibility
    risk_score = Column(Float, default=0.0)  # Alias for final_risk_score
    
    # Risk Flags (JSON array of triggered rules)
    risk_flags = Column(JSON, default=list)
    
    # Decision & Status
    auto_decision = Column(String(20), default=TransactionStatus.PENDING.value)
    status = Column(String(20), default=TransactionStatus.PENDING.value, index=True)
    decision = Column(String(20), default="PENDING")  # Legacy compatibility
    
    # Explainability
    explanation = Column(Text, nullable=True)
    explanation_model = Column(String(50), nullable=True)  # llama3, gpt-4, etc.
    
    # Similarity Propagation
    similarity_triggered = Column(Boolean, default=False)
    inherited_from_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    # Review Tracking
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    investigation_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=True)
    
    # Model Metadata
    model_version = Column(String(50), nullable=True)
    scoring_latency_ms = Column(Float, nullable=True)
    intelligence = Column(JSON, nullable=True)

    # Appeal System
    is_appealed = Column(Boolean, default=False)
    appeal_reason = Column(Text, nullable=True)
    appeal_urgency = Column(String(20), nullable=True) # HIGH, MEDIUM, LOW
    appeal_timestamp = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions", foreign_keys=[user_id])
    reviewer = relationship("User", back_populates="reviewed_transactions", foreign_keys=[reviewed_by])
    account = relationship("UserAccount", back_populates="transactions")
    merchant_profile = relationship("MerchantProfile", back_populates="transactions")
    audit_trail = relationship("AuditLog", back_populates="transaction", cascade="all, delete-orphan")
    investigation_case = relationship("InvestigationCase", back_populates="transactions")
    sar_records = relationship("SARRecord", back_populates="transaction", cascade="all, delete-orphan")

    # Performance Indexes
    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_user_device", "user_id", "device_id"),
        Index("idx_user_ip", "user_id", "ip_address"),
        Index("idx_status_timestamp", "status", "timestamp"),
        Index("idx_risk_score", "final_risk_score"),
        Index("idx_amount_risk", "amount", "final_risk_score"),
    )

    def __repr__(self):
        return f"<Transaction {self.id} user={self.user_id} amount={self.amount} status={self.status}>"


# ============================================================================
# AUDIT LOG (Regulatory Compliance)
# ============================================================================

class AuditLog(Base):
    """
    Immutable audit trail for every transaction decision.
    Required for RBI/regulatory audits and dispute resolution.
    Every decision must be explainable months later.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tx_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Input Features Snapshot (for reproducibility)
    input_features = Column(JSON)  # All features used for scoring
    user_profile_snapshot = Column(JSON)  # User baseline at decision time
    
    # Model Outputs
    ae_score = Column(Float)
    if_score = Column(Float)
    gnn_score = Column(Float)
    rule_flags = Column(JSON)  # List of triggered rules
    final_risk_score = Column(Float)
    
    # Model Metadata
    model_version = Column(String(50))
    ae_model_version = Column(String(50), nullable=True)
    if_model_version = Column(String(50), nullable=True)
    gnn_model_version = Column(String(50), nullable=True)
    threshold_config = Column(JSON)  # Thresholds used for decision
    
    # Decisions
    auto_decision = Column(String(20))  # System's automatic decision
    final_decision = Column(String(20))  # Final decision (may differ if analyst overrides)
    
    # Explainability
    explanation = Column(Text)
    explanation_model = Column(String(50))
    explanation_prompt = Column(Text, nullable=True)  # LLM prompt used
    
    # Analyst Action (if reviewed)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    analyst_action = Column(String(20), nullable=True)  # APPROVED, REJECTED, ESCALATED
    analyst_notes = Column(Text, nullable=True)
    analyst_action_time = Column(DateTime, nullable=True)
    
    # Performance Metrics
    scoring_latency_ms = Column(Float, nullable=True)
    explanation_latency_ms = Column(Float, nullable=True)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="audit_trail")
    analyst = relationship("User", back_populates="audit_actions", foreign_keys=[analyst_id])

    __table_args__ = (
        Index("idx_audit_tx_timestamp", "tx_id", "timestamp"),
        Index("idx_audit_analyst", "analyst_id", "analyst_action_time"),
    )

    def __repr__(self):
        return f"<AuditLog tx={self.tx_id} decision={self.final_decision}>"


# ============================================================================
# MODEL CONFIGURATION & THRESHOLDS
# ============================================================================

class ModelConfig(Base):
    """
    Stores model configurations and risk thresholds.
    Allows admins to tune the system without code changes.
    """
    __tablename__ = "model_configs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True)  # e.g., "production", "conservative"
    is_active = Column(Boolean, default=False)
    
    # Risk Thresholds
    flag_threshold = Column(Float, default=0.5)  # Score above this → FLAGGED
    block_threshold = Column(Float, default=0.8)  # Score above this → BLOCKED
    
    # Model Weights for Score Fusion
    ae_weight = Column(Float, default=0.3)
    if_weight = Column(Float, default=0.3)
    gnn_weight = Column(Float, default=0.2)
    rule_weight = Column(Float, default=0.2)
    
    # Rule Thresholds
    amount_zscore_threshold = Column(Float, default=3.0)  # Z-score for amount anomaly
    velocity_tx_per_hour = Column(Integer, default=10)  # Max transactions per hour
    velocity_amount_per_hour = Column(Float, default=100000.0)  # Max amount per hour
    new_device_penalty = Column(Float, default=0.1)  # Added to score for new device
    new_location_penalty = Column(Float, default=0.1)  # Added to score for new location
    night_tx_penalty = Column(Float, default=0.05)  # Added for night transactions
    
    # Model Versions
    ae_model_path = Column(String(255), nullable=True)
    if_model_path = Column(String(255), nullable=True)
    gnn_model_path = Column(String(255), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    def __repr__(self):
        return f"<ModelConfig {self.name} active={self.is_active}>"


# ============================================================================
# FEEDBACK RECORDS (Model Improvement)
# ============================================================================

class FeedbackRecord(Base):
    """
    Records analyst feedback for model retraining.
    When analyst overrides a decision, this feeds back into the ML pipeline.
    """
    __tablename__ = "feedback_records"

    id = Column(Integer, primary_key=True)
    tx_id = Column(Integer, ForeignKey("transactions.id"), index=True)
    audit_id = Column(Integer, ForeignKey("audit_logs.id"), index=True)
    
    # Original vs Corrected
    original_decision = Column(String(20))
    corrected_decision = Column(String(20))
    
    # Features at Decision Time
    features = Column(JSON)
    
    # Feedback Metadata
    feedback_type = Column(String(50))  # false_positive, false_negative, edge_case
    analyst_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Retraining Status
    used_for_retraining = Column(Boolean, default=False)
    retraining_batch_id = Column(String(50), nullable=True)

    def __repr__(self):
        return f"<FeedbackRecord tx={self.tx_id} {self.feedback_type}>"



# ============================================================================
# WHITELIST / TRUSTED ENTITIES
# ============================================================================

class WhitelistEntity(Base):
    """
    Trusted entities (merchants/beneficiaries) that receive a risk discount.
    NOT a bypass. High risk scores from GNN/Models will override this.
    """
    __tablename__ = "whitelist_entities"

    id = Column(Integer, primary_key=True, index=True)
    entity_name = Column(String(255), unique=True, index=True, nullable=False)
    entity_type = Column(String(50), default="merchant") # merchant, beneficiary
    
    # Risk Config
    risk_discount = Column(Float, default=0.15) # Subtract from final risk score
    max_allowed_amount = Column(Float, nullable=True) # If set, whitelist only applies below this amount
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<WhitelistEntity {self.entity_name} discount={self.risk_discount}>"


# ============================================================================
# FORENSICS & INVESTIGATION
# ============================================================================

class InvestigationCase(Base):
    """
    Groups suspicious transactions into a single investigation.
    Supports analyst workflow from discovery to resolution.
    """
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="OPEN")  # OPEN, INVESTIGATING, RESOLVED, DISMISSED
    priority = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Assignment
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Relationships
    analyst = relationship("User", back_populates="assigned_cases")
    transactions = relationship("Transaction", back_populates="investigation_case")

    def __repr__(self):
        return f"<InvestigationCase {self.id}: {self.title} ({self.status})>"


# ============================================================================
# SAR RECORDS (Suspicious Activity Reports)
# ============================================================================

class SARRecord(Base):
    """
    Stores versioned regulatory Suspicious Activity Reports (SAR).
    Generated by LLM based on transaction facts and anomaly explanations.
    """
    __tablename__ = "sar_records"

    id = Column(Integer, primary_key=True, index=True)
    tx_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    
    # Content
    narrative = Column(Text, nullable=False)
    risk_score = Column(Float)
    triggered_models = Column(JSON)  # List of models that flagged the tx
    
    # Metadata
    version = Column(Integer, default=1)
    generated_at = Column(DateTime, default=datetime.utcnow)
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Structured context used for generation (for audit reproducibility)
    generation_context = Column(JSON, nullable=True)
    
    # Relationships
    transaction = relationship("Transaction", back_populates="sar_records")
    creator = relationship("User")

    def __repr__(self):
        return f"<SARRecord tx={self.tx_id} v={self.version}>"
