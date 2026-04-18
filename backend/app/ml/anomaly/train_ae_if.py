import os
import joblib
import torch
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import MinMaxScaler

from app.ml.anomaly.features import load_and_prepare_data
from app.ml.anomaly.isolation_forest import (
    train_isolation_forest,
    anomaly_score,
)
from app.ml.anomaly.service import train_autoencoder, ae_scores


# ==============================
# Config
# ==============================
DATA_PATH = "data/ieee_cis/creditcard.csv"

MODEL_DIR = "ml_models"
EPOCHS = 50
PATIENCE = 5
AE_WEIGHT = 0.6
IF_WEIGHT = 0.4

os.makedirs(MODEL_DIR, exist_ok=True)

# ==============================
# Load data
# ==============================
X, y, scaler = load_and_prepare_data(DATA_PATH)

# Train only on normal data
X_normal = X[y == 0]

# Train/validation split (NORMAL ONLY)
X_train, X_val = train_test_split(
    X_normal, test_size=0.2, random_state=42
)

print(f"Training samples: {X_train.shape[0]}")
print(f"Validation samples: {X_val.shape[0]}")

# ==============================
# Autoencoder Training
# ==============================
ae, train_losses, val_losses = train_autoencoder(
    X_train,
    X_val,
    epochs=EPOCHS,
    patience=PATIENCE
)


# AE anomaly scores
ae_score_all = ae_scores(ae, X)

# ==============================
# Isolation Forest
# ==============================
if_model = train_isolation_forest(
    X_train,
    n_estimators=300,
    contamination=0.002,
    max_samples=0.8
)

if_score_all = anomaly_score(if_model, X)

# ==============================
# Normalize scores
# ==============================
ae_scaler = MinMaxScaler()
if_scaler = MinMaxScaler()

ae_norm = ae_scaler.fit_transform(
    ae_score_all.reshape(-1, 1)
).ravel()

if_norm = if_scaler.fit_transform(
    if_score_all.reshape(-1, 1)
).ravel()

# ==============================
# Ensemble score
# ==============================
final_score = AE_WEIGHT * ae_norm + IF_WEIGHT * if_norm

auc = roc_auc_score(y, final_score)
print(f"\n🔥 AE + IF ROC-AUC: {auc:.4f}")

# ==============================
# Threshold (99.9% normal)
# ==============================
threshold = np.percentile(final_score[y == 0], 99.9)
print(f"🚨 Alert threshold: {threshold:.4f}")

# ==============================
# Save models
# ==============================
torch.save(ae.state_dict(), f"{MODEL_DIR}/autoencoder.pt")
joblib.dump(if_model, f"{MODEL_DIR}/isolation_forest.pkl")
joblib.dump(scaler, f"{MODEL_DIR}/scaler.pkl")
joblib.dump(ae_scaler, f"{MODEL_DIR}/ae_score_scaler.pkl")
joblib.dump(if_scaler, f"{MODEL_DIR}/if_score_scaler.pkl")
joblib.dump(threshold, f"{MODEL_DIR}/alert_threshold.pkl")

print("\n✅ Models saved successfully")
