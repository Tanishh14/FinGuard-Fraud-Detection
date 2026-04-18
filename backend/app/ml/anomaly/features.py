import numpy as np
import pandas as pd
from datetime import datetime

# Expanded Feature Columns for Modernized Pipeline (14 dims)
# Matches training script output: 8 numerical + 5 categorical + 1 padding
FEATURE_COLUMNS = [
    "step", 
    "amount", 
    "oldbalanceOrg", 
    "newbalanceOrig", 
    "oldbalanceDest", 
    "newbalanceDest", 
    "errorBalanceOrig", 
    "errorBalanceDest",
    "type_CASH_IN", 
    "type_CASH_OUT", 
    "type_DEBIT", 
    "type_PAYMENT", 
    "type_TRANSFER",
    "padding"
]

def extract_transaction_features(tx: dict, profile: dict = None) -> np.ndarray:
    """
    Extracts 14 core features compatible with the PaySim-trained model.
    Encodes Step, Amount, Balances, and Transaction Type.
    
    Args:
        tx: Transaction data dictionary
        profile: User behavioral profile (optional, used for balance proxy if needed)
        
    Returns:
        pd.DataFrame: Single-row DataFrame with raw features matching training schema
    """
    try:
        amount = float(tx.get("amount", 0.0))
        
        # 1. Step (Time) - Approximate
        ts_raw = tx.get("timestamp") or datetime.utcnow()
        ts = datetime.fromisoformat(str(ts_raw)) if isinstance(ts_raw, str) else ts_raw
        step = int(ts.hour) # Simple mapping
        
        # 2. Balances & Errors
        oldbalanceOrg = float(tx.get("oldbalanceOrg", amount))
        newbalanceOrig = float(tx.get("newbalanceOrig", 0.0))
        oldbalanceDest = float(tx.get("oldbalanceDest", 0.0))
        newbalanceDest = float(tx.get("newbalanceDest", amount))
        
        errorBalanceOrig = newbalanceOrig + amount - oldbalanceOrg
        errorBalanceDest = oldbalanceDest + amount - newbalanceDest
        
        # 3. Type Inference
        merchant_id = tx.get("merchant_id")
        tx_type = "TRANSFER"
        if merchant_id and str(merchant_id).strip():
            tx_type = "PAYMENT"
            
        # 4. Construct DataFrame (Raw values for ColumnTransformer)
        # Schema must match training data for Transformer to work
        features_df = pd.DataFrame([{
            "step": step,
            "type": tx_type,
            "amount": amount,
            "oldbalanceOrg": oldbalanceOrg,
            "newbalanceOrig": newbalanceOrig,
            "oldbalanceDest": oldbalanceDest,
            "newbalanceDest": newbalanceDest,
            "errorBalanceOrig": errorBalanceOrig,
            "errorBalanceDest": errorBalanceDest
        }])
        
        return features_df
        
    except Exception as e:
        print(f"Feature Extraction Error: {e}")
        # Return empty DF with correct columns (will likely fail downstream but better than crash)
        return pd.DataFrame(columns=[
            "step", "type", "amount", "oldbalanceOrg", "newbalanceOrig", 
            "oldbalanceDest", "newbalanceDest", "errorBalanceOrig", "errorBalanceDest"
        ])
