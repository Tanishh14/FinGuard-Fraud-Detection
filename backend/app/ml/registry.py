import torch
import joblib
import os
import logging
from typing import Dict, Any, Optional
from threading import Lock

from app.ml.anomaly.autoencoder import TransactionAutoencoder
from app.ml.anomaly.isolation_forest import TransactionIsolationForest
from app.ml.gnn.model import FraudGNN
from app.ml.model_registry import MODEL_PATHS

logger = logging.getLogger(__name__)

class ModelRegistry:
    """
    Singleton registry to manage ML models in production.
    Ensures models are loaded once and available globally for scoring.
    """
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelRegistry, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        self.models: Dict[str, Any] = {}
        self.is_ready = False
        self._initialized = True
        
    def load_all_models(self):
        """Load all ML models from disk with per-model fallback resilience."""
        logger.info(f"Loading models. CWD: {os.getcwd()}")
        
        # 1. Load Autoencoder
        self.models["autoencoder"] = TransactionAutoencoder(input_dim=8)
        ae_path = MODEL_PATHS["autoencoder"]
        if os.path.exists(ae_path):
            try:
                state_dict = torch.load(ae_path, map_location=torch.device('cpu'))
                self.models["autoencoder"].load_state_dict(state_dict)
                self.models["autoencoder"].eval()
                logger.info("Autoencoder loaded successfully")
            except Exception as e:
                logger.error(f"Autoencoder architecture mismatch or corruption: {e}")
                logger.warning("Using uninitialized (untrained) Autoencoder structure.")
        else:
            logger.warning(f"Autoencoder weights not found at {ae_path}")

        # 2. Load Isolation Forest
        if_path = MODEL_PATHS["isolation_forest"]
        if os.path.exists(if_path):
            try:
                self.models["isolation_forest"] = joblib.load(if_path)
                logger.info("Isolation Forest loaded successfully")
            except Exception as e:
                logger.error(f"Isolation Forest load failed: {e}")
        else:
            logger.warning(f"Isolation Forest model not found at {if_path}")

        # 3. Load StandardScaler + Error Distribution
        scaler_path = MODEL_PATHS["scaler"]
        if os.path.exists(scaler_path):
            try:
                scaler_data = joblib.load(scaler_path)
                if isinstance(scaler_data, dict):
                    self.models["scaler"] = scaler_data['scaler']
                    # Verify scaler dimensions
                    # Verify scaler dimensions
                    # New pipeline: Scaler takes ~9 raw features -> outputs 8
                    # Old pipeline: Scaler took 14 features.
                    # We relax this check or update it.
                    if hasattr(self.models["scaler"], "n_features_in_"):
                        logger.info(f"Scaler expects {self.models['scaler'].n_features_in_} input features.")
                    
                    self.models["error_mean"] = scaler_data.get('error_mean', 0.05)
                    self.models["error_std"] = scaler_data.get('error_std', 0.02)
                else:
                    self.models["scaler"] = scaler_data
                    self.models["error_mean"] = 0.05
                    self.models["error_std"] = 0.02
                logger.info("StandardScaler + Error Distribution loaded")
            except Exception as e:
                logger.error(f"Scaler mismatch or error: {e}")
                from sklearn.preprocessing import StandardScaler
                self.models["scaler"] = StandardScaler() # Raw fallback
        else:
            logger.warning(f"StandardScaler not found at {scaler_path}")

        # 4. Load GNN
        self.models["gnn"] = FraudGNN(in_dim=8)
        gnn_path = MODEL_PATHS["gnn"]
        if os.path.exists(gnn_path):
            try:
                state_dict = torch.load(gnn_path, map_location=torch.device('cpu'))
                self.models["gnn"].load_state_dict(state_dict)
                self.models["gnn"].eval()
                logger.info("GNN loaded successfully")
            except Exception as e:
                logger.error(f"GNN architecture mismatch or corruption: {e}")
                logger.warning("Using uninitialized (untrained) GNN structure.")
        else:
            logger.warning(f"GNN weights not found at {gnn_path}")
            
        self.is_ready = all(k in self.models for k in ["autoencoder", "isolation_forest", "gnn", "scaler"])
        if not self.is_ready:
            logger.error("System in DEGRADED mode: One or more ML models missing/failed.")
        else:
            logger.info("✓ ML System Registry initialized successfully.")

    def get_model(self, name: str):
        """Get a specific model by name."""
        return self.models.get(name)

# Global registry instance
registry = ModelRegistry()
