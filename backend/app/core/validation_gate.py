import logging
import math
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ValidationGate:
    """
    FinGuard AI 2.0 — Hybrid Orchestration Gate.
    ML scores determine RISK. This gate determines CONSEQUENCE.
    """

    def validate_transaction(
        self, tx_data: Dict[str, Any], scores: Dict[str, float]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Returns (gate_passed, decision_string, metadata).
        decision_string: "APPROVED" | "REVIEW" | "BLOCKED"
        gate_passed: True unless BLOCKED (REVIEW still passes money through)
        """
        amount = float(tx_data.get("amount", 0.0))
        frs    = float(scores.get("final_score", 0.0))   # 0.0 – 1.0
        track  = tx_data.get("track", "PROBATIONARY")

        # ── TRACK A: PROBATIONARY HARD CEILING ──────────────────────────────────
        # New users (< 10 tx) cannot spend > ₹5,000 per transaction.
        if track == "PROBATIONARY" and amount > 5000:
            return (
                False,   # Hard-block enforcement
                "BLOCKED",
                {
                    "tier": "PROBATIONARY_LIMIT",
                    "reason": (
                        f"[BLOCKED] Provisional maximum exceeded: New user account limit is "
                        f"₹5,000 per transaction (Attempted: ₹{amount:,.2f})."
                    ),
                },
            )

        # ── TIER 3: HARD BLOCK ───────────────────────────────────────────────────
        # FRS > 90%  OR  Amount > ₹45,000  OR  FRS > 95% (extreme certainty)
        if frs > 0.90 or amount > 45000:
            return (
                False,
                "BLOCKED",
                {
                    "tier": "TIER_3",
                    "reason": (
                        f"[BLOCKED] High-confidence fraud signal "
                        f"(FRS: {frs*100:.1f}%, Amount: ₹{amount:,.2f}). "
                        f"Transaction rejected and flagged for SAR drafting."
                    ),
                },
            )

        # ── TIER 2: REVIEW / FLAG ────────────────────────────────────────────────
        # FRS 65–90%  OR  Amount ₹15,000–₹45,000 (high-value oversight)
        # Money flows through but is held for investigative audit.
        if (0.65 <= frs <= 0.90) or (15000 <= amount <= 45000):
            return (
                True,   # Allowed — not blocked
                "REVIEW",
                {
                    "tier": "TIER_2",
                    "reason": (
                        f"[FLAGGED] Suspicious pattern detected "
                        f"(FRS: {frs*100:.1f}%, Amount: ₹{amount:,.2f}). "
                        f"Transaction permitted but queued for investigative audit."
                    ),
                    "velocity_monitoring": frs > 0.80,
                },
            )

        # ── TIER 1: AUTO-APPROVED ────────────────────────────────────────────────
        # FRS < 55%  AND  Amount < ₹15,000 — clean, low-risk transaction
        return (
            True,
            "APPROVED",
            {
                "tier": "TIER_1",
                "reason": (
                    "Transaction cleared by AI ensemble. "
                    "Risk score and amount within safe thresholds."
                ),
            },
        )


def get_calibrated_score(logit: float) -> float:
    """
    Platt Scaling sigmoid — converts raw logit to calibrated probability.
    Formula: P = 1 / (1 + exp(-logit))
    """
    # Guard against overflow for very large/small logits
    logit = max(-20.0, min(20.0, logit))
    return 1.0 / (1.0 + math.exp(-logit))
