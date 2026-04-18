import sys
import os

# Robust Path Fix
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

import torch
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from app.ml.anomaly.autoencoder import TransactionAutoencoder
from app.ml.gnn.model import FraudGNN

def init_models():
    print("Initializing Models...")
    os.makedirs(os.path.join(backend_dir, "ml_models"), exist_ok=True)
    models_dir = os.path.join(backend_dir, "ml_models")
    
    # 1. Train Autoencoder (Calibrated)
    print("Training Autoencoder with calibrated data...")
    
    
    # 1. Train Autoencoder (Calibrated with REALISTIC SYNTHETIC DATA)
    print("Training Autoencoder with realistic synthetic data...")
    
    n_normal = 5000
    n_anomaly = 500
    
    # Generate realistic features matching extract_transaction_features order:
    # 0: amount (LogNormal) - Median ~50, Range 1-1000+
    # 1: hour (Uniform 0-24)
    # 2: weekday (Uniform 0-7)
    # 3: tx_count_1h (Poisson lambda=1)
    # 4: tx_count_24h (Poisson lambda=5)
    # 5: avg_amount_7d (LogNormal matching amount)
    # 6: merchant_risk (Beta - mostly low)
    # 7: device_changed (Bernoulli p=0.1)
    
    def generate_synthetic_data(n, is_anomaly=False):
        # 0. Amount
        if is_anomaly:
            amounts = np.random.lognormal(mean=7.0, sigma=1.5, size=n) # Very High amounts
        else:
            amounts = np.random.lognormal(mean=4.5, sigma=1.5, size=n) # Higher variance for normal
            
        # 1. Hour (0-24)
        hours = np.random.uniform(0, 24, n)
        if is_anomaly: # Night items
            hours = np.concatenate([np.random.uniform(0, 5, n//2), np.random.uniform(22, 24, n-n//2)])
            
        # 2. Weekday
        days = np.random.randint(0, 7, n)
        
        # 3. Velocity 1h
        v1h = np.random.poisson(lam=10 if is_anomaly else 1, size=n)
        
        # 4. Velocity 24h
        v24h = np.random.poisson(lam=50 if is_anomaly else 5, size=n)
        
        # 5. Avg Amount
        avg_amt = np.random.lognormal(mean=4.0, sigma=1.0, size=n)
        
        # 6. Merchant Risk
        merch_risk = np.random.beta(a=5, b=1, size=n) if is_anomaly else np.random.beta(a=1, b=10, size=n)
        
        # 7. Device Changed
        dev_chg = np.random.choice([0, 1], size=n, p=[0.5, 0.5] if is_anomaly else [0.9, 0.1])
        
        return np.column_stack([amounts, hours, days, v1h, v24h, avg_amt, merch_risk, dev_chg])

    X_normal = generate_synthetic_data(n_normal, is_anomaly=False)
    X_anomaly = generate_synthetic_data(n_anomaly, is_anomaly=True)
    
    X_train_raw = np.vstack([X_normal, X_anomaly])
    np.random.shuffle(X_train_raw)

    # Scale Data
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    
    ae = TransactionAutoencoder(input_dim=8)
    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(ae.parameters(), lr=0.001) # Lower LR
    
    inputs = torch.FloatTensor(X_train)
    for epoch in range(100): # More epochs
        optimizer.zero_grad()
        outputs = ae(inputs)
        loss = criterion(outputs, inputs)
        loss.backward()
        optimizer.step()
    
    # Calculate reconstruction error distribution (μ, σ) on NORMAL data only
    # (We want to score anomalies relative to normal behavior)
    ae.eval()
    with torch.no_grad():
        # Scale normal data separately for stats
        X_norm_scaled = scaler.transform(X_normal)
        inputs_norm = torch.FloatTensor(X_norm_scaled)
        recon = ae(inputs_norm)
        reconstruction_errors = torch.mean((inputs_norm - recon) ** 2, dim=1).numpy()
    
    error_mean = float(np.mean(reconstruction_errors))
    error_std = float(np.std(reconstruction_errors))
    print(f"OK Reconstruction Error Distribution: mean={error_mean:.6f}, std={error_std:.6f}")
        
    torch.save(ae.state_dict(), os.path.join(models_dir, "autoencoder.pt"))
    print(f"OK Saved Autoencoder to {os.path.join(models_dir, 'autoencoder.pt')}")
    
    # Save scaler with error distribution
    scaler_data = {
        'scaler': scaler,
        'error_mean': error_mean,
        'error_std': error_std
    }
    joblib.dump(scaler_data, os.path.join(models_dir, "scaler.pkl"))
    print(f"OK Saved Scaler + Error Distribution")

    # 2. Train Isolation Forest
    print("Training Isolation Forest...")
    clf = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
    clf.fit(X_train)
    joblib.dump(clf, os.path.join(models_dir, "isolation_forest.pkl"))
    print(f"OK Saved Isolation Forest to {os.path.join(models_dir, 'isolation_forest.pkl')}")

    # 3. GNN Weights
    print("Initializing GNN weights...")
    gnn = FraudGNN(in_dim=8)
    torch.save(gnn.state_dict(), os.path.join(models_dir, "gnn_model.pt"))
    print(f"OK Saved GNN to {os.path.join(models_dir, 'gnn_model.pt')}")

    print("Model initialization complete.")

if __name__ == "__main__":
    init_models()
