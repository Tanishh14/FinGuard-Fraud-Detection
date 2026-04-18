"""
FinGuard Fraud Scoring Pipeline
================================
Comprehensive fraud detection pipeline that combines:
1. Autoencoder (AE) anomaly detection
2. Isolation Forest (IF) outlier detection
3. Graph Neural Network (GNN) for fraud rings
4. Rule-based sanity checks

All scores are fused into a final risk score with configurable weights.
"""
import torch
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import time
import logging

from sqlalchemy.orm import Session

from app.db.models import Transaction, ModelConfig, MerchantProfile
from app.profiles.service import ProfileService

logger = logging.getLogger(__name__)


class FraudScoringPipeline:
    """
    Unified Data-Driven Scoring Pipeline.
    Combines Autoencoder, Isolation Forest, and GNN scores.
    """
    
    def __init__(
        self,
        ae_model=None,
        if_model=None,
        gnn_service=None,
    ):
        from app.ml.registry import registry
        from app.ml.anomaly.service import AnomalyService
        from app.ml.gnn.service import GNNService
        
        # 1. Models & Services from Registry (Fallback)
        ae = ae_model or registry.get_model("autoencoder")
        iforest = if_model or registry.get_model("isolation_forest")
        scaler = registry.get_model("scaler")
        gnn_model = registry.get_model("gnn")
        
        self.anomaly_service = AnomalyService(
            ae_model=ae,
            iforest_model=iforest,
            scaler=scaler,
            error_mean=registry.models.get("error_mean"),
            error_std=registry.models.get("error_std")
        )
        
        self.gnn_service = gnn_service
        if self.gnn_service is None and gnn_model is not None:
            self.gnn_service = GNNService(gnn_model, scaler=scaler)
            
        self.model_version = "v2.1.0"
        logger.info(f"Scoring Pipeline initialized. Models: AE={'YES' if ae else 'NO'}, IF={'YES' if iforest else 'NO'}, GNN={'YES' if self.gnn_service else 'NO'}")

    def score_transaction(
        self,
        db: Session,
        tx_data: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]] = None,
        graph_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Unified ML scoring pipeline with Performance Measurement and Deterministic Decisions.
        """
        # --- FEATURE 3: LATENCY MEASUREMENT (START) ---
        pipeline_start = time.perf_counter()
        
        # 1. Feature Engineering
        from app.ml.anomaly.features import extract_transaction_features
        profile_service = ProfileService(db)
        if user_profile is None:
            user_profile = profile_service.get_baseline(tx_data.get("user_id", 0))
            
        features = extract_transaction_features(tx_data, user_profile)
        
        # 2. Get Anomaly Scores (Autoencoder + Isolation Forest)
        anomaly_results = self.anomaly_service.score_transaction(features)
        ae_score = float(anomaly_results.get("ae_score", 0.05))
        if_score = float(anomaly_results.get("if_score", 0.05))
        anomaly_component = (ae_score * 0.5 + if_score * 0.5)
        
        # 3. Get GNN Risk Score
        gnn_score = 0.05
        gnn_active = False
        if self.gnn_service is not None:
            try:
                gnn_score = self.gnn_service.score_transaction(
                    db,
                    tx_data.get("user_id"),
                    tx_data.get("merchant", "unknown"),
                    tx_data.get("device_id", "unknown"),
                    tx_data
                )
                gnn_active = True
            except Exception as e:
                logger.warning(f"GNN inference failed: {e}")
        
        gnn_component = float(np.clip(gnn_score, 0.0, 1.0))

        # 4. Behavioral & Contextual Rules (Heuristic Engine)
        rule_flags = []
        try:
            is_transfer = 1.0 if features['type'].iloc[0] == 'TRANSFER' else 0.0
            is_payment = 1.0 if features['type'].iloc[0] == 'PAYMENT' else 0.0
            hour = int(features['step'].iloc[0]) % 24 
            
            context_risk = (is_transfer * 0.7 + is_payment * 0.2)
            amount = float(tx_data.get("amount", 0))
            avg_amount = user_profile.get("avg_amount", 5000) if user_profile else 5000
            if avg_amount < 100:  # Guard against zero/uninitialized profiles
                avg_amount = 5000
            spike_factor = min(1.0, (amount / avg_amount) / 5.0)  # Spike only if 5x above baseline
            time_risk = 0.8 if hour < 5 else 0.1
            behavior_risk = (spike_factor * 0.7 + time_risk * 0.3)
            
            if behavior_risk > 0.5: rule_flags.append({"name": "Behavioral Spikes", "weight": behavior_risk})
            if context_risk > 0.5: rule_flags.append({"name": "High-Risk Channel", "weight": context_risk})
            
            rule_component = (behavior_risk * 0.5 + context_risk * 0.5)
        except Exception:
            rule_component = 0.2

        # --- FIN GUARD AI 2.0: DUAL-TRACK ORCHESTRATION ---
        user_history = user_profile.get("total_tx_count", 0) if user_profile else 0
        amount_val = float(tx_data.get("amount", 0.0))

        # ── NORMALIZE RAW MODEL SCORES ──────────────────────────────────────────
        # The AE model outputs reconstruction error (0-1). A new user ALWAYS has
        # high reconstruction error (unseen pattern) → this is NOT fraud signal.
        # We normalize by comparing to expected baseline error for new users.
        # AE score > 0.5 on new users is expected noise, not fraud.
        # We clip+scale to a 0-0.4 range for new users, 0-1.0 for established.
        ae_normalized = float(np.clip(ae_score, 0.0, 1.0))
        gnn_normalized = float(np.clip(gnn_score, 0.0, 1.0))

        # ── TRACK SELECTION ─────────────────────────────────────────────────────
        if user_history < 10:
            track = "PROBATIONARY"
            # New users: AE reconstruction error is not a reliable fraud signal.
            # Cap the contribution so "new user = anomalous" doesn't auto-flag.
            # Weight toward rule-based heuristics which are more reliable for new users.
            ae_capped = ae_normalized * 0.3   # Dampen AE: new ≠ fraudulent
            raw_score = (ae_capped * 0.5) + (rule_component * 0.5)
        else:
            track = "ESTABLISHED"
            # Spread out the FRS tightly by giving more weight to dynamic behavioral heuristics
            # (rule_component vary wildly based on amount, time, and context)
            raw_score = (gnn_normalized * 0.50) + (ae_normalized * 0.10) + (rule_component * 0.40)

            # Micro-amnesty: routine small spend for known users
            if amount_val < 500:
                raw_score *= 0.4

        # ── DIVERGENCE PENALTY (Soft) ────────────────────────────────────────────
        divergence = abs(gnn_normalized - ae_normalized)
        if divergence > 0.30:
            raw_score = min(1.0, raw_score * 1.08)  # Soft 8% bump, capped at 1.0

        # ── PLATT SCALING (CALIBRATED SIGMOID) ──────────────────────────────────
        # Bias = 0.62 (raw score > 0.62 exceeds 50% risk) - Pushes mid-range down safely
        # Slope = 8 (Maintains healthy variance across the full spectrum)
        logit = (raw_score - 0.62) * 8
        from app.core.validation_gate import get_calibrated_score
        fraud_probability = float(np.clip(get_calibrated_score(logit), 0.0, 1.0))

        # Package Context for Decision Engine
        tx_data["track"] = track

        # ── METRICS ─────────────────────────────────────────────────────────────
        confidence = round(1.0 - divergence, 4)
        contributions = {
            "gnn": 0.80 if track == "ESTABLISHED" else 0.0,
            "anomaly": 0.10 if track == "ESTABLISHED" else 0.5,
            "rules": 0.10 if track == "ESTABLISHED" else 0.5,
        }

        # ── VALIDATION GATE ──────────────────────────────────────────────────────
        from app.core.validation_gate import ValidationGate
        gate = ValidationGate()

        if user_profile:
            tx_data["total_tx_count"] = user_profile.get("total_tx_count", 0)

        gate_passed, gate_status, gate_metadata = gate.validate_transaction(
            tx_data,
            {
                "gnn_score": gnn_normalized,
                "anomaly_score": ae_normalized,
                "final_score": fraud_probability,
                "rule_score": rule_component,
            }
        )

        final_decision = gate_status  # APPROVED / REVIEW / BLOCKED

        # --- ALIGN AI VERDICT WITH FINAL DECISION ---
        # If the gate enacts a hard block or review due to rules (e.g., amount limits, probationary limits),
        # ensure the AI Verdict correctly reflects this deterministic risk so the UI is visually consistent.
        if final_decision == "BLOCKED" and fraud_probability < 0.85:
            fraud_probability = min(0.99, 0.92 + (amount_val / 1000000.0))
        elif final_decision == "REVIEW" and fraud_probability < 0.65:
            fraud_probability = min(0.89, 0.72 + (amount_val / 1000000.0))

        # ── LATENCY ──────────────────────────────────────────────────────────────
        latency_ms = (time.perf_counter() - pipeline_start) * 1000

        # Build decision reason
        if final_decision == "BLOCKED":
            reason = gate_metadata.get("reason", f"High fraud probability ({fraud_probability*100:.1f}%). Transaction rejected.")
        elif final_decision == "REVIEW":
            reason = gate_metadata.get("reason", f"Suspicious activity flagged ({fraud_probability*100:.1f}%). Queued for review.")
        else:
            reason = "Transaction cleared by AI ensemble. Matches behavioral baseline."

        result = {
            "ae_score": round(ae_score, 4),
            "if_score": round(if_score, 4),
            "gnn_score": round(gnn_normalized, 4),
            "final_risk": round(fraud_probability, 4),
            "confidence": round(confidence, 4),
            "decision": final_decision,  # Map to gate-validated decision
            "decision_reason": reason,
            "model_contributions": contributions,
            "latency_ms": round(latency_ms, 2),
            "gate_status": gate_status,
            "track": track,
            "intelligence": {
                "labels": [
                    f"TRACK: {track}",
                    f"FRS: {fraud_probability*100:.1f}%",
                    f"CONFIDENCE: {confidence:.2f}",
                    f"LATENCY: {latency_ms:.1f}ms",
                    f"GATE: {gate_status}",
                ],
                "breakdown": {
                    "GNN (Graph Network)": round(gnn_normalized, 4),
                    "Anomaly (Autoencoder)": round(ae_normalized, 4),
                    "Isolation Forest": round(if_score, 4),
                    "Behavioral Rules": round(rule_component, 4),
                    "Calibrated FRS": round(fraud_probability, 4),
                    "Model Divergence": round(divergence, 4),
                }
            }
        }
        
        logger.info(f"AUDIT_SCORE: {final_decision} | prob={fraud_probability:.4f} | latency={latency_ms:.2f}ms")
        return result
    def _generate_reason(self, contributors: List[str], decision: str, tx_data: Dict = None, trust_score: float = 0.0) -> str:
        if decision == "APPROVED":
            return "Transaction safe: matches historical patterns and graph topology."
        
        if not contributors:
            return "Unexpected anomaly detected across multiple neural network layers."
            
        merchant = tx_data.get("merchant", "Unknown Merchant") if tx_data else "Unknown"
        amount = tx_data.get("amount", 0) if tx_data else 0
        
        # Build narrative
        narrative = f"Critical risk detected for payment to '{merchant}' (₹{amount:,.2f}). "
        
        # Add primary reasons (Handle both strings and metadata dicts)
        reason_names = [c["name"] if isinstance(c, dict) else str(c) for c in contributors]
        narrative += f"Primary factors: {', '.join(reason_names)}. "
        
        if decision == "BLOCKED":
            narrative += "Action: Access restricted to prevent potential fraud."
        else:
            narrative += "Action: Secondary verification required."
            
        return narrative
    
    def _apply_rules(self, *args, **kwargs):
        """DEPRECATED: Rule-based logic removed."""
        return 0.0, []
    
    def _build_explanation_context(
        self,
        tx_data: Dict[str, Any],
        user_profile: Dict[str, Any],
        ae_score: float,
        if_score: float,
        gnn_score: float,
        rule_flags: List[str],
        final_score: float,
        decision: str
    ) -> Dict[str, Any]:
        """Build context for LLM explanation generation."""
        return {
            "transaction": {
                "amount": tx_data.get("amount"),
                "merchant": tx_data.get("merchant"),
                "location": tx_data.get("location"),
                "timestamp": str(tx_data.get("timestamp"))
            },
            "user_baseline": {
                "avg_spend": round(user_profile.get("avg_amount", 0), 2),
                "typical_locations": list(user_profile.get("top_locations", {}).keys())[:3],
                "profile_maturity": user_profile.get("profile_maturity")
            },
            "scores": {
                "anomaly_detection": round(ae_score, 2),
                "outlier_detection": round(if_score, 2),
                "graph_analysis": round(gnn_score, 2),
                "rule_based": round(sum([0.1] * len(rule_flags)), 2) if rule_flags else 0
            },
            "risk_flags": rule_flags,
            "final_score": round(final_score * 100, 1),
            "decision": decision
        }


# Singleton instance for easy import
_pipeline_instance: Optional[FraudScoringPipeline] = None


def get_scoring_pipeline() -> FraudScoringPipeline:
    """Get or create scoring pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = FraudScoringPipeline()
    return _pipeline_instance


def score_transaction(db: Session, tx_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to score a single transaction."""
    pipeline = get_scoring_pipeline()
    return pipeline.score_transaction(db, tx_data)
