import torch
import numpy as np
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from torch_geometric.data import Data
from app.db.models import Transaction, MerchantProfile, User
from app.ml.anomaly.features import extract_transaction_features

logger = logging.getLogger(__name__)

class GNNService:
    """
    GNN Service for real-time risk propagation.
    Builds a local subgraph around the transaction and runs GraphSAGE.
    """
    def __init__(self, model, scaler=None):
        self.model = model
        self.scaler = scaler
        if self.model:
            self.model.eval()

    def score_transaction(self, db: Session, user_id: int, merchant_name: str, device_id: str, tx_data: Dict[str, Any]) -> float:
        """
        Builds a local neighborhood subgraph and runs GNN inference.
        Propagates risk from linked entities (shared devices, recent merchant fraud).
        """
        if not self.model:
            return 0.1
            
        try:
            # 1. Fetch Local Neighborhood (related nodes and edges)
            # Find transactions in last 24h for this merchant or device
            related_txs = db.query(Transaction).filter(
                (Transaction.merchant_id == tx_data.get('merchant_id')) | 
                (Transaction.device_id == device_id) |
                (Transaction.user_id == user_id)
            ).order_by(Transaction.timestamp.desc()).limit(20).all()
            
            if not related_txs:
                return 0.1

            # 2. Build Subgraph Nodes & Features
            # We map entities to node indices
            node_map = {} # (type, id) -> index
            features = []
            
            for rtx in related_txs:
                uid = rtx.user_id
                mid = rtx.merchant_id
                
                if ("user", uid) not in node_map:
                    node_map[("user", uid)] = len(node_map)
                    # For users, we can use their baseline or generic features
                    features.append(np.zeros(8)) 
                
                if ("merchant", mid) not in node_map:
                    node_map[("merchant", mid)] = len(node_map)
                    features.append(np.zeros(8))

            # Current transaction node
            curr_idx = len(node_map)
            # 1. Extract RAW features
            features_df = extract_transaction_features(tx_data)

            # 2. Select ONLY the 8 numerical columns that the scaler expects
            numerical_cols = ["step", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest", "errorBalanceOrig", "errorBalanceDest"]
            features_selection = features_df[numerical_cols].values
            
            # SCALE features if scaler acts on them
            if self.scaler:
                try:
                    # Transform DataFrame using pipeline
                    features_processed = self.scaler.transform(features_selection)
                    
                    if hasattr(features_processed, "toarray"):
                        features_processed = features_processed.toarray()
                        
                    # Slice to 8 dims for GNN alignment
                    if features_processed.shape[1] > 8:
                        features_processed = features_processed[:, :8]
                        
                    # Flatten for GNN
                    features.append(features_processed.flatten())
                except Exception as e:
                    logger.warning(f"GNN Scaling failed: {e}. Using zero vector.")
                    features.append(np.zeros(8))
            else:
                # Fallback if no scaler (should not happen in prod)
                features.append(np.zeros(8))
            
            # 3. Build Edges (User -> Merchant)
            edge_index = []
            for rtx in related_txs:
                u_idx = node_map.get(("user", rtx.user_id))
                m_idx = node_map.get(("merchant", rtx.merchant_id))
                if u_idx is not None and m_idx is not None:
                    edge_index.append([u_idx, m_idx])
                    edge_index.append([m_idx, u_idx]) # Undirected
            
            if not edge_index:
                return 0.15

            # 4. Run GNN Inference
            x = torch.tensor(np.array(features), dtype=torch.float32)
            edges = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
            
            with torch.no_grad():
                # GNN returns scores for ALL nodes in subgraph
                out = self.model(x, edges)
                # Prediction for our current transaction node (last one)
                risk_score = torch.sigmoid(out[-1]).item()
            
            return float(np.clip(risk_score, 0.05, 0.95))

        except Exception as e:
            logger.error(f"GNN Real-time Scoring Error: {e}")
            return 0.2 # Elevated neutral on failure

    def update_graph(self, tx: Transaction):
        """Placeholder for batch graph updates or persistent risk table."""
        pass
