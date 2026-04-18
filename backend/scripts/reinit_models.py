import os
import torch
import joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
import sys

# Add parent directory to path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.ml.anomaly.autoencoder import TransactionAutoencoder
from app.ml.gnn.model import FraudGNN
from app.ml.model_registry import MODEL_PATHS

def reinit_models():
    print("Starting ML Model Re-initialization (14-dim Architecture)...")
    
    # Ensure directory exists
    model_dir = os.path.dirname(MODEL_PATHS["autoencoder"])
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        print(f"Created directory: {model_dir}")

    # 1. Initialize & Save Autoencoder
    print("Initializing Autoencoder (input_dim=14)...")
    ae = TransactionAutoencoder(input_dim=14)
    torch.save(ae.state_dict(), MODEL_PATHS["autoencoder"])
    print(f"✓ Saved Autoencoder to {MODEL_PATHS['autoencoder']}")

    # 2. Initialize & Save GNN
    print("Initializing GNN (in_dim=14)...")
    gnn = FraudGNN(in_dim=14)
    torch.save(gnn.state_dict(), MODEL_PATHS["gnn"])
    print(f"✓ Saved GNN to {MODEL_PATHS['gnn']}")

    # 3. Initialize & Save Scaler (14 features)
    print("Initializing StandardScaler (14 features)...")
    scaler = StandardScaler()
    # Fit on dummy data to set n_features_in_
    dummy_data = np.zeros((1, 14))
    scaler.fit(dummy_data)
    
    scaler_payload = {
        'scaler': scaler,
        'error_mean': 0.05,
        'error_std': 0.02
    }
    joblib.dump(scaler_payload, MODEL_PATHS["scaler"])
    print(f"✓ Saved Scaler to {MODEL_PATHS['scaler']}")

    # 4. Initialize & Save Isolation Forest (Optional but recommended)
    print("Initializing Isolation Forest...")
    from sklearn.ensemble import IsolationForest
    iforest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
    iforest.fit(dummy_data)
    joblib.dump(iforest, MODEL_PATHS["isolation_forest"])
    print(f"✓ Saved Isolation Forest to {MODEL_PATHS['isolation_forest']}")

    print("\nML Model Re-initialization Complete. System check ready.")

if __name__ == "__main__":
    reinit_models()
