import pytest
from unittest.mock import MagicMock, patch
from app.ml.similarity.service import SimilarityEngine
from app.db.models import Transaction

@pytest.fixture
def mock_db():
    return MagicMock()

@pytest.fixture
def mock_cache():
    with patch("app.ml.similarity.service.cache_manager") as mock:
        yield mock

def test_similarity_hit_blocked(mock_db, mock_cache):
    # Setup
    mock_cache.get_json.return_value = {
        "tx_id": 123,
        "amount": 100.0,
        "decision": "BLOCKED",
        "final_risk_score": 0.95,
        "rule_score": 1.0
    }
    engine = SimilarityEngine(mock_db)
    
    # Test
    result = engine.check_similarity({
        "user_id": 1,
        "merchant": "Test Merchant",
        "amount": 95.0 # within 90%
    })
    
    # Assert
    assert result is not None
    assert result["similarity_triggered"] is True
    assert result["inherited_from_transaction_id"] == 123
    assert result["decision"] == "BLOCKED"
    assert result["final_risk"] == 0.95

def test_similarity_hit_approved(mock_db, mock_cache):
    # Setup
    mock_cache.get_json.return_value = {
        "tx_id": 124,
        "amount": 50.0,
        "decision": "APPROVED",
        "final_risk_score": 0.10,
        "rule_score": 0.0
    }
    engine = SimilarityEngine(mock_db)
    
    # Test
    result = engine.check_similarity({
        "user_id": 1,
        "merchant": "Safe Merchant",
        "amount": 52.0 # within 90%
    })
    
    # Assert
    assert result is not None
    assert result["similarity_triggered"] is True
    assert result["inherited_from_transaction_id"] == 124
    assert result["decision"] == "APPROVED"
    assert result["final_risk"] == 0.10
    
def test_no_similarity_normal_path(mock_db, mock_cache):
    # Setup Cache Miss
    mock_cache.get_json.return_value = None
    
    # DB fallback miss
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    
    engine = SimilarityEngine(mock_db)
    
    # Test
    result = engine.check_similarity({
        "user_id": 1,
        "merchant": "New Merchant",
        "amount": 50.0
    })
    
    # Assert
    assert result is None # indicates normal ML path should run

def test_similarity_engine_failure_fallback(mock_db, mock_cache):
    # Simulate Redis Exception
    mock_cache.get_json.side_effect = Exception("Redis connection refused")
    
    # DB fallback miss
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    
    engine = SimilarityEngine(mock_db)
    
    # Should safely catch exception and return None to continue ML path
    result = engine.check_similarity({
        "user_id": 1,
        "merchant": "Safe Merchant",
        "amount": 50.0
    })
    
    assert result is None

def test_db_fallback_hit(mock_db, mock_cache):
    # Cache miss
    mock_cache.get_json.return_value = None
    
    # DB fallback hit
    mock_tx = MagicMock(spec=Transaction)
    mock_tx.id = 555
    mock_tx.amount = 100.0
    mock_tx.status = "BLOCKED"
    mock_tx.final_risk_score = 0.99
    mock_tx.rule_score = 1.0
    
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_tx
    
    engine = SimilarityEngine(mock_db)
    
    # Test
    result = engine.check_similarity({
        "user_id": 1,
        "merchant": "Merchant X",
        "amount": 99.0
    })
    
    # Assert
    assert result is not None
    assert result["similarity_triggered"] is True
    assert result["inherited_from_transaction_id"] == 555
    assert result["decision"] == "BLOCKED"
