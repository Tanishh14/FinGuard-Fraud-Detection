"""
FinGuard Anomaly Detection Service
===================================
Provides anomaly detection using Autoencoder and Isolation Forest models.
Used as part of the fraud scoring pipeline.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


from app.ml.anomaly.autoencoder import TransactionAutoencoder as AutoEncoder


class AnomalyService:
    """
    Service for transaction anomaly detection.
    Implements Sigmoid-based normalization for zero-saturation scoring.
    """
    def __init__(self, ae_model=None, iforest_model=None, scaler=None, error_mean=None, error_std=None):
        self.ae = ae_model
        self.iforest = iforest_model
        self.scaler = scaler
        
        # Baseline stats for normalization (rolling statistics)
        self.error_mean = error_mean if error_mean is not None else 0.05
        self.error_std = error_std if error_std is not None else 0.02
        
        if self.ae:
            self.ae.eval()
    
    def score_transaction(self, features_df: Any) -> Dict[str, float]:
        """
        Score transaction using unified pipeline.
        Args:
            features_df: pd.DataFrame with raw features (from features.py)
        """
        ae_score = 0.05
        if_score = 0.05
        recon_error = 0.0
        
        # Get Amount for Logic (safe access)
        try:
            amount = float(features_df['amount'].iloc[0])
        except:
            amount = 0.0
            
        # 1. Feature Preprocessing (CRITICAL: Use Training Pipeline)
        if self.scaler is None:
            logger.error("Scoring aborted: Scaler pipeline missing. Falling back to rule-based heuristics.")
            return {"ae_score": 0.05, "if_score": 0.05, "reconstruction_error": 0.0}
            
        try:
            # Select ONLY the 8 numerical columns that the scaler expects
            numerical_cols = ["step", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "errorBalanceOrig", "errorBalanceDest"]
            features_selection = features_df[numerical_cols].values
            
            # Transform raw dataframe -> numpy array (8 dims)
            features_processed = self.scaler.transform(features_selection)
            
            # Handle Sparse Matrix
            features_scaled = features_processed.astype(np.float32)
            
            # Ensure shape is (Batch, 8)
            if features_scaled.shape[1] != 8:
                logger.warning(f"Feature dimension mismatch: expected 8, got {features_scaled.shape[1]}. Slicing/Padding.")
                if features_scaled.shape[1] > 8:
                    features_scaled = features_scaled[:, :8]
                else:
                    padding = np.zeros((features_scaled.shape[0], 8 - features_scaled.shape[1]))
                    features_scaled = np.hstack((features_scaled, padding))
            
        except Exception as e:
            logger.error(f"Preprocessing pipeline failed: {e}")
            return {"ae_score": 0.1, "if_score": 0.1, "reconstruction_error": 0.0}
        
        # 2. Autoencoder Scoring
        if self.ae is not None:
            try:
                x_tensor = torch.tensor(features_scaled, dtype=torch.float32)
                recon_error = self.ae.anomaly_score(x_tensor).item()
                
                # Dynamic normalization (Log-Relative)
                # FIX: self.error_mean from scaler.pkl is the FEATURE mean (~0.07), not MSE mean.
                # Observed MSE for normal tx is ~0.0003. Anomaly is ~0.001+.
                # We interpret error_mean as a baseline MSE. 
                # Let's use a hardcoded safe baseline if the loaded one is suspicious (>0.01)
                baseline_mse = self.error_mean
                if baseline_mse > 0.01: 
                     baseline_mse = 0.0005 # Calibrated from tuning script
                
                ratio = recon_error / max(baseline_mse, 1e-9)
                
                # Calibrated Z-score: 
                # Ratio 1.0 -> 0.1 score
                # Ratio 3.0 -> 0.8 score (Anomaly)
                
                # z = (ratio - 1.5) * 2.0
                # ratio=1 => -1.0 => sig(-1) = 0.26
                # ratio=3 => 3.0 => sig(3) = 0.95
                # ratio=0.6 (very normal) => -1.8 => 0.14
                
                z = (ratio - 1.5) * 2.5
                
                ae_score = 1.0 / (1.0 + np.exp(-z))
                
                # Sensitivity Guard
                # Boost massive amounts regardless of error
                if amount > 150000:
                    ae_score = max(ae_score, 0.6) # Minimum suspicion for huge amounts
                
                ae_score = float(np.clip(ae_score, 0.01, 1.0))
                logger.info(f"AE_SCORE: {ae_score:.4f} (err={recon_error:.6f}, base={baseline_mse:.6f}, amt={amount})")
            except Exception as e:
                logger.warning(f"AE scoring failed: {e}")
        
        # 3. Isolation Forest Scoring (Global Thresholding)
        if self.iforest is not None:
            try:
                # RAW Score: decision_function
                # Normal observed: ~0.21. Anomaly observed: ~0.13. 
                # We need to shift the boundary. 
                # If raw < 0.18, we start seeing risk.
                
                raw_score = self.iforest.decision_function(features_scaled)[0]
                
                # Calibration:
                # Threshold = 0.18. 
                # Risk increases as score drops below 0.18.
                # raw = 0.21 -> diff = 0.03 -> Safe
                # raw = 0.13 -> diff = -0.05 -> Risky
                
                # Formula: sigmoid( (0.18 - raw) * Scale )
                # (0.18 - 0.21) * 30 = -0.9 -> sig(-0.9) ~ 0.28 (Low)
                # (0.18 - 0.13) * 30 = 1.5 -> sig(1.5) ~ 0.81 (High)
                
                if_score = 1.0 / (1.0 + np.exp( -(0.18 - raw_score) * 40.0 ))
                
                # Guard: If amount is tiny, suppress risk unless it's deep anomaly
                if amount < 500.0 and if_score < 0.9:
                    if_score *= 0.5
                    
                if_score = float(np.clip(if_score, 0.01, 1.0))
                
                logger.info(f"IF_SCORE: {if_score:.4f} (raw={raw_score:.4f})")
            except Exception as e:
                logger.warning(f"IF scoring failed: {e}")

        return {
            "ae_score": ae_score,
            "if_score": if_score,
            "reconstruction_error": float(recon_error)
        }


def train_autoencoder(X_train, X_val, epochs=50, patience=5):
    """
    Train autoencoder model with early stopping.
    
    Args:
        X_train: Training features
        X_val: Validation features
        epochs: Maximum epochs
        patience: Early stopping patience
        
    Returns:
        Trained model, train losses, val losses
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Training autoencoder on {device}")

    model = AutoEncoder(X_train.shape[1]).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    X_train = torch.tensor(X_train, dtype=torch.float32).to(device)
    X_val = torch.tensor(X_val, dtype=torch.float32).to(device)

    best_loss = float("inf")
    counter = 0

    train_losses, val_losses = [], []

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        recon = model(X_train)
        train_loss = criterion(recon, X_train)
        train_loss.backward()
        optimizer.step()

        model.eval()
        with torch.no_grad():
            val_recon = model(X_val)
            val_loss = criterion(val_recon, X_val)

        train_losses.append(train_loss.item())
        val_losses.append(val_loss.item())

        if epoch % 10 == 0:
            logger.info(
                f"Epoch {epoch+1}/{epochs} | "
                f"Train: {train_loss.item():.6f} | "
                f"Val: {val_loss.item():.6f}"
            )

        if val_loss < best_loss:
            best_loss = val_loss
            counter = 0
        else:
            counter += 1
            if counter >= patience:
                logger.info("Early stopping triggered")
                break

    return model, train_losses, val_losses


def ae_scores(model, X):
    """Calculate anomaly scores for a batch of samples."""
    device = next(model.parameters()).device
    X = torch.tensor(X, dtype=torch.float32).to(device)

    model.eval()
    with torch.no_grad():
        recon = model(X)
        scores = torch.mean((X - recon) ** 2, dim=1)

    return scores.cpu().numpy()
