import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.profiles.service import ProfileService
from app.db.models import UserBehaviorProfile, Transaction
from app.ml.scoring_pipeline import FraudScoringPipeline

class TestCriticalLogic:
    
    @pytest.fixture
    def mock_db_session(self):
        return MagicMock()
        
    def test_profile_outlier_protection(self, mock_db_session):
        """Verify that massive outliers do not corrupt the user profile."""
        service = ProfileService(mock_db_session)
        
        # Setup existing profile
        profile = UserBehaviorProfile(
            user_id=1,
            avg_amount=100.0,
            std_amount=10.0,
            total_tx_count=10,
            _m2=900.0 # Variance=100 -> std=10
        )
        
        # Mock DB to return this profile
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = profile
        
        # 1. Normal transaction
        tx_normal = Transaction(amount=110.0, timestamp=datetime.utcnow())
        service.update_profile(1, tx_normal)
        assert profile.avg_amount < 200, "Normal update failed"
        
        # 2. Massive Outlier (10,000x average)
        # Without protection, this would skew the mean to ~90,000
        tx_outlier = Transaction(amount=1_000_000.0, timestamp=datetime.utcnow())
        service.update_profile(1, tx_outlier)
        
        # Expectation: The outlier is capped at 100x mean (100 * 100 = 10,000)
        # So effective amount is 10,000. New mean should be roughly (100*11 + 10000)/12 ~= 900
        # Definitely NOT 90,000
        assert profile.avg_amount < 5000.0, f"Outlier protection failed. Mean skewed to {profile.avg_amount}"
        assert profile.std_amount < 1_000_000_000.0, "Std deviation exploded"
        
    def test_scoring_boost_explanation(self, mock_db_session):
        """Verify that extreme risk scores trigger the specific explanation."""
        pipeline = FraudScoringPipeline()
        
        # Mock services
        pipeline.anomaly_service = MagicMock()
        pipeline.gnn_service = MagicMock()
        
        # Setup: Extreme anomaly score
        pipeline.anomaly_service.score_transaction.return_value = {
            "ae_score": 0.99, # > 0.95 Threshold
            "if_score": 0.5
        }
        pipeline.gnn_service.score_transaction.return_value = 0.5
        
        # Mock DB features
        with patch('app.ml.scoring_pipeline.ProfileService'), \
             patch('app.ml.anomaly.features.extract_transaction_features', return_value=[0]*14):
            
            result = pipeline.score_transaction(
                mock_db_session,
                {"amount": 100, "user_id": 1},
                user_profile={"avg_amount": 100}
            )
            
            print(f"Decision Reason: {result['decision_reason']}")
            
            # Verify Boost happened
            assert result['final_risk'] >= 0.85, "Risk boost failed to raise score"
            
            # Verify Logic is explained
            assert "CRITICAL: Extreme anomaly signal" in result['decision_reason'], \
                "Decision reason did not mention the risk boost override"
