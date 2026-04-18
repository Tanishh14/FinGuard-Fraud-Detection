import numpy as np
import joblib
from sklearn.ensemble import IsolationForest

class TransactionIsolationForest:
    def __init__(self, n_estimators=200, contamination=0.01, random_state=42):
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1
        )

    def fit(self, X: np.ndarray):
        self.model.fit(X)

    def score(self, X: np.ndarray) -> np.ndarray:
        """
        Convert sklearn output to anomaly score [0,1].
        Higher score = more anomalous.
        """
        # score_samples returns the opposite of the anomaly score (lower is more abnormal)
        scores = -self.model.score_samples(X)
        if scores.max() == scores.min():
            return np.zeros_like(scores)
        return (scores - scores.min()) / (scores.max() - scores.min() + 1e-6)
