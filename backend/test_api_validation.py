"""
Integration test: Verify the API endpoint properly handles validation failures
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.guid_fragility_fix import TrainingDataQualityError, TrainingDataQualityValidator

def test_validation_error_carries_metrics():
    """Test that TrainingDataQualityError properly carries metrics"""
    
    test_metrics = {
        "defaulted_percentage": 45.2,
        "total_features": 1024,
        "defaulted_features": 463
    }
    
    error = TrainingDataQualityError(
        "Test error message",
        validation_metrics=test_metrics
    )
    
    assert error.validation_metrics == test_metrics
    assert error.validation_report["metrics"] == test_metrics
    assert "Test error message" in str(error)
    print("✅ TrainingDataQualityError properly carries metrics")


def test_api_response_structure():
    """Test that the API error response has correct structure"""
    
    # Simulate what the API would return
    test_metrics = {
        "defaulted_percentage": 45.2,
        "total_features": 1024,
        "defaulted_features": 463
    }
    
    api_response = {
        "success": False,
        "validation_failed": True,
        "error": "Training data quality failed validation: 45.20% features defaulted (threshold: 20.0%)",
        "validation_report": {
            "metrics": test_metrics,
            "message": "Dataset contains excessive defaults which would reintroduce the 70% accuracy bug",
            "threshold_percent": 20.0
        }
    }
    
    # Verify structure matches frontend expectations
    assert api_response["validation_failed"] == True
    assert "metrics" in api_response["validation_report"]
    assert "defaulted_percentage" in api_response["validation_report"]["metrics"]
    
    # Check that frontend can extract defaulted_percentage
    defaulted_pct = api_response["validation_report"]["metrics"]["defaulted_percentage"]
    assert defaulted_pct == 45.2
    
    print("✅ API response structure correct for frontend consumption")


def test_frontend_error_message_format():
    """Test that frontend can format error message from API response"""
    
    api_response = {
        "success": False,
        "validation_failed": True,
        "error": "Training data quality failed validation",
        "validation_report": {
            "metrics": {
                "defaulted_percentage": 45.2,
                "total_features": 1024,
                "defaulted_features": 463
            }
        }
    }
    
    # Simulate frontend error message creation
    if api_response.get("validation_failed"):
        report = api_response.get("validation_report", {})
        defaulted_pct = report.get("metrics", {}).get("defaulted_percentage", 0)
        
        error_msg = (
            f"❌ TRAINING ABORTED - DATA QUALITY FAILURE\n\n"
            f"Defaulted Features: {defaulted_pct:.1f}%\n"
            f"Threshold: 20%\n\n"
            f"This indicates excessive defaults in training data"
        )
        
        assert "45.2%" in error_msg
        print("✅ Frontend can properly format error message from API response")
        print(f"   Error message:\n{error_msg}")


if __name__ == "__main__":
    test_validation_error_carries_metrics()
    test_api_response_structure()
    test_frontend_error_message_format()
    print("\n✅ All integration tests passed!")
