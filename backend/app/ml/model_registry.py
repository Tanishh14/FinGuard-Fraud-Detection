"""Model registry for version tracking and traceability."""

# Current model version - update when models are retrained
MODEL_VERSION = "v1.0.0"

import os

# Base directory of the backend application (3 levels up from app/ml/model_registry.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Model file paths - using absolute paths to be safe regardless of CWD
MODEL_PATHS = {
    "autoencoder": os.path.join(BASE_DIR, "ml_models", "autoencoder.pt"),
    "isolation_forest": os.path.join(BASE_DIR, "ml_models", "isolation_forest.pkl"),
    "gnn": os.path.join(BASE_DIR, "ml_models", "gnn_model.pt"),
    "scaler": os.path.join(BASE_DIR, "ml_models", "scaler.pkl")
}

# Risk thresholds (configurable by admin)
RISK_THRESHOLDS = {
    "approved_max": 0.3,      # Below this = APPROVED
    "flagged_max": 0.7,       # Between approved_max and this = FLAGGED
    # Above flagged_max = BLOCKED
}

# Weighted fusion coefficients
FUSION_WEIGHTS = {
    "autoencoder": 0.3,
    "isolation_forest": 0.3,
    "gnn": 0.4
}

# Rule-based thresholds
RULE_THRESHOLDS = {
    "amount_z_score_max": 5.0,      # Z-score above this triggers flag
    "amount_ratio_max": 10.0,       # Ratio to avg above this triggers flag
    "night_tx_suspicious": 0.9,     # Night tx when user rarely does = suspicious
    "min_amount_for_ratio_check": 500.0 # Minimum amount to trigger ratio heuristic
}
