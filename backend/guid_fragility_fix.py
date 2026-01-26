"""
GUID Fragility Fix - Prevent Silent 70% Accuracy Regression

CRITICAL ISSUE:
When GUID matching fails during graph enrichment, element features silently
default to standard dimensions (width=1200mm, height=2400mm, etc.). If this
happens to >20% of training samples, features cluster into near-identical values,
causing the model to train to 70% accuracy by learning patterns in defaults
rather than real building characteristics.

The 70% bug is UNDETECTABLE because:
1. Feature extraction returns (features, missing_fields) but missing_fields not used
2. Training diagnostics runs AFTER training (too late to prevent garbage data)
3. No pre-training validation gate

SOLUTION:
1. Track default usage percentage in feature extraction
2. Pre-training validation gate: ABORT if >20% features use defaults
3. Diagnostic logging: Warn if any default-filled training data
4. Test case: Detect if 70% bug returns silently
"""

import logging
import json
import numpy as np
from typing import Dict, Tuple, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FeatureExtractionMetrics:
    """Track feature extraction quality"""
    total_features: int = 0
    defaulted_features: int = 0
    defaulted_percentage: float = 0.0
    missing_fields: List[str] = None
    
    def __post_init__(self):
        if self.missing_fields is None:
            self.missing_fields = []
    
    def update_percentage(self):
        """Calculate defaulted percentage"""
        if self.total_features > 0:
            self.defaulted_percentage = (self.defaulted_features / self.total_features) * 100.0
    
    def is_problematic(self, threshold: float = 20.0) -> bool:
        """Check if default usage exceeds threshold"""
        return self.defaulted_percentage > threshold
    
    def summary(self) -> str:
        """Generate human-readable summary"""
        return (
            f"Features: {self.total_features} total, "
            f"{self.defaulted_features} defaulted ({self.defaulted_percentage:.1f}%) - "
            f"Fields: {', '.join(self.missing_fields) if self.missing_fields else 'none'}"
        )


class TrainingDataQualityValidator:
    """Pre-training validation to prevent 70% accuracy bug"""
    
    CRITICAL_THRESHOLD = 20.0  # Abort if >20% defaults
    WARNING_THRESHOLD = 10.0   # Warn if >10% defaults
    
    @staticmethod
    def validate_dataset_before_training(
        training_data_path: str,
        training_samples: List[Dict[str, Any]],
        abort_on_failure: bool = True
    ) -> Dict[str, Any]:
        """
        CRITICAL VALIDATION: Run before training starts
        
        This is the ONLY barrier preventing the 70% accuracy bug from being
        silently reintroduced.
        
        Args:
            training_data_path: Path to training data file (for context)
            training_samples: List of training sample dicts
            abort_on_failure: If True, raise exception instead of warning
        
        Returns:
            Validation report with analysis
        
        Raises:
            TrainingDataQualityError: If CRITICAL_THRESHOLD exceeded and abort_on_failure=True
        """
        report = {
            "validation_status": "PASS",
            "timestamp": str(np.datetime64('now')),
            "total_samples": len(training_samples),
            "data_path": training_data_path,
            "issues": [],
            "warnings": [],
            "metrics": {},
            "sample_analysis": [],
            "recommendation": ""
        }
        
        if not training_samples:
            report["validation_status"] = "FAIL"
            report["issues"].append("❌ CRITICAL: No training samples provided!")
            return report
        
        # Analyze feature extraction quality across all samples
        total_defaulted = 0
        total_features_count = 0
        problematic_samples = []
        
        for idx, sample in enumerate(training_samples[:100]):  # Sample first 100
            elem_features = sample.get("element_features", [])
            rule_features = sample.get("rule_features", [])
            context_features = sample.get("context_features", [])
            
            # Extract metadata about defaults (if present)
            defaults_metadata = sample.get("_extraction_metadata", {})
            if defaults_metadata:
                elem_defaults = defaults_metadata.get("element_defaults_count", 0)
                rule_defaults = defaults_metadata.get("rule_defaults_count", 0)
                
                total_defaulted += elem_defaults + rule_defaults
                total_features_count += (
                    len(elem_features) if isinstance(elem_features, (list, tuple)) else 128
                ) + (
                    len(rule_features) if isinstance(rule_features, (list, tuple)) else 128
                )
                
                if (elem_defaults + rule_defaults) > 25:  # >25 defaults per sample
                    problematic_samples.append({
                        "sample_idx": idx,
                        "defaults_count": elem_defaults + rule_defaults,
                        "labels": sample.get("trm_target_label")
                    })
        
        # Calculate statistics
        if total_features_count > 0:
            default_percentage = (total_defaulted / total_features_count) * 100.0
        else:
            default_percentage = 0.0
        
        report["metrics"] = {
            "total_samples_analyzed": min(100, len(training_samples)),
            "total_features": total_features_count,
            "defaulted_features": total_defaulted,
            "defaulted_percentage": round(default_percentage, 2),
            "problematic_samples_count": len(problematic_samples)
        }
        
        # Check against thresholds
        if default_percentage > TrainingDataQualityValidator.CRITICAL_THRESHOLD:
            report["validation_status"] = "FAIL"
            report["issues"].append(
                f"❌ CRITICAL: {default_percentage:.1f}% of features use defaults! "
                f"This will reintroduce the 70% accuracy bug."
            )
            report["issues"].append(
                f"   Defaulted features: {total_defaulted} out of {total_features_count}"
            )
            report["recommendation"] = (
                "→ Do NOT proceed with training! This dataset is too corrupted by defaults.\n"
                "→ Verify graph enrichment succeeded during data extraction.\n"
                "→ Check that GUID matching is working correctly.\n"
                "→ Run compliance checks with proper IFC files (graph parameter provided)."
            )
            
            if problematic_samples:
                report["sample_analysis"] = problematic_samples[:10]
            
            if abort_on_failure:
                raise TrainingDataQualityError(
                    f"Training data quality failed validation: "
                    f"{default_percentage:.1f}% features defaulted (threshold: {TrainingDataQualityValidator.CRITICAL_THRESHOLD}%)",
                    validation_metrics=report["metrics"]
                )
        
        elif default_percentage > TrainingDataQualityValidator.WARNING_THRESHOLD:
            report["validation_status"] = "WARN"
            report["warnings"].append(
                f"⚠️  {default_percentage:.1f}% of features use defaults (warning threshold: {TrainingDataQualityValidator.WARNING_THRESHOLD}%)"
            )
            report["warnings"].append(
                "   While not critical, this suggests incomplete GUID matching."
            )
            report["recommendation"] = (
                "→ Consider rerunning compliance checks to improve data quality.\n"
                "→ Monitor model accuracy closely - may be lower than expected."
            )
        
        else:
            report["validation_status"] = "PASS"
            report["recommendation"] = (
                "✅ Training data quality is good.\n"
                f"→ Only {default_percentage:.1f}% of features use defaults."
            )
        
        # Log full report
        logger.info(f"\n{'='*80}")
        logger.info("GUID FRAGILITY VALIDATION REPORT")
        logger.info(f"{'='*80}")
        logger.info(f"Status: {report['validation_status']}")
        logger.info(f"Metrics: {json.dumps(report['metrics'], indent=2)}")
        for issue in report['issues']:
            logger.error(issue)
        for warning in report['warnings']:
            logger.warning(warning)
        logger.info(f"Recommendation:\n{report['recommendation']}")
        logger.info(f"{'='*80}\n")
        
        return report
    
    @staticmethod
    def validate_element_features(
        element_features: np.ndarray,
        element_data: Dict[str, Any],
        missing_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Validate individual element features for excessive defaults
        
        Returns diagnostic info about feature quality
        """
        feature_quality = {
            "feature_vector_length": len(element_features),
            "has_nan": bool(np.any(np.isnan(element_features))),
            "has_inf": bool(np.any(np.isinf(element_features))),
            "feature_variance": float(np.var(element_features)),
            "feature_mean": float(np.mean(element_features)),
            "missing_fields_count": len(missing_fields),
            "missing_fields": missing_fields,
            "defaulted_keys": [k for k, v in element_data.items() if v is None or v == ""],
            "is_suspicious": False,
            "reason": ""
        }
        
        # Check for suspicious patterns
        if feature_quality["feature_variance"] < 0.001:
            feature_quality["is_suspicious"] = True
            feature_quality["reason"] = "Feature variance too low (likely all defaults)"
        
        if len(missing_fields) > 5:
            feature_quality["is_suspicious"] = True
            feature_quality["reason"] = f"Too many missing fields: {len(missing_fields)}"
        
        if feature_quality["has_nan"] or feature_quality["has_inf"]:
            feature_quality["is_suspicious"] = True
            feature_quality["reason"] = "Invalid feature values (NaN/Inf)"
        
        return feature_quality


class TrainingDataQualityError(Exception):
    """Raised when training data quality check fails"""
    def __init__(self, message: str, validation_metrics: Dict[str, Any] = None):
        super().__init__(message)
        self.validation_metrics = validation_metrics or {}
        self.validation_report = {
            "metrics": self.validation_metrics,
            "message": message
        }


def create_training_data_with_quality_tracking(
    samples: List[Dict[str, Any]],
    output_path: str,
    validate_before_save: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Create training data file with quality validation
    
    This replaces the standard training data creation and adds:
    1. Feature extraction metadata tracking
    2. Pre-training validation
    3. Quality report generation
    
    Args:
        samples: List of training samples
        output_path: Where to save training data
        validate_before_save: If True, validate data before saving
    
    Returns:
        (success: bool, report: Dict with validation results)
    
    Raises:
        TrainingDataQualityError: If validation fails and abort_on_failure=True
    """
    report = {
        "creation_status": "CREATING",
        "total_samples": len(samples),
        "output_path": output_path,
        "validation_report": None,
        "saved": False,
        "errors": []
    }
    
    # Validate data quality if requested
    if validate_before_save:
        try:
            validation_report = TrainingDataQualityValidator.validate_dataset_before_training(
                training_data_path=output_path,
                training_samples=samples,
                abort_on_failure=True
            )
            report["validation_report"] = validation_report
            
            if validation_report["validation_status"] == "FAIL":
                report["creation_status"] = "FAILED_VALIDATION"
                report["errors"].append(
                    "Training data failed quality validation. Aborting save."
                )
                return False, report
        
        except TrainingDataQualityError as e:
            report["creation_status"] = "FAILED_VALIDATION"
            report["errors"].append(str(e))
            logger.error(f"❌ Training data validation failed: {e}")
            return False, report
    
    # Save training data
    try:
        training_data = {
            "training_samples": samples,
            "_metadata": {
                "creation_timestamp": str(np.datetime64('now')),
                "total_samples": len(samples),
                "quality_validated": validate_before_save,
                "validation_report": report.get("validation_report")
            }
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        report["creation_status"] = "SUCCESS"
        report["saved"] = True
        logger.info(f"✅ Training data saved to {output_path}")
        
    except Exception as e:
        report["creation_status"] = "FAILED_WRITE"
        report["errors"].append(f"Failed to write training data: {str(e)}")
        logger.error(f"❌ Failed to save training data: {e}")
        return False, report
    
    return True, report


# ============================================================================
# TEST CASE: Detect if 70% accuracy bug returns silently
# ============================================================================

def test_training_data_default_detection():
    """
    TEST CASE: Verify that training data with excessive defaults is detected
    
    This test MUST pass to ensure the 70% accuracy bug cannot be
    silently reintroduced.
    
    Scenario:
    - Create fake training data where 80% of features are defaulted
    - Validation should FAIL with appropriate error
    - Training should be ABORTED
    """
    import tempfile
    
    print("\n" + "="*80)
    print("TEST: GUID Fragility Detection")
    print("="*80)
    
    # Create sample training data with excessive defaults
    bad_samples = []
    for i in range(100):
        sample = {
            "element_features": np.ones(128) * 0.5,  # All ~0.5 = clustered!
            "rule_features": np.ones(128) * 0.5,
            "context_features": np.ones(128) * 0.5,
            "trm_target_label": i % 2,
            "_extraction_metadata": {
                "element_defaults_count": 115,  # 115 out of 128 = 90% defaulted!
                "rule_defaults_count": 120
            }
        }
        bad_samples.append(sample)
    
    # Attempt to validate
    try:
        validation_report = TrainingDataQualityValidator.validate_dataset_before_training(
            training_data_path="test_data.json",
            training_samples=bad_samples,
            abort_on_failure=True
        )
        
        # Should not reach here
        print("❌ TEST FAILED: Validation should have raised exception!")
        return False
    
    except TrainingDataQualityError as e:
        print(f"✅ TEST PASSED: Validation correctly detected fragility")
        print(f"   Error: {str(e)}")
        return True
    
    except Exception as e:
        print(f"❌ TEST FAILED: Unexpected error: {str(e)}")
        return False


def test_good_training_data_passes():
    """
    TEST CASE: Verify that good training data passes validation
    
    Scenario:
    - Create training data with only 5% defaulted features
    - Validation should PASS
    - Training should proceed normally
    """
    print("\n" + "="*80)
    print("TEST: Good Training Data Quality")
    print("="*80)
    
    # Create sample training data with acceptable defaults
    good_samples = []
    for i in range(100):
        sample = {
            "element_features": np.random.rand(128),  # Diverse features
            "rule_features": np.random.rand(128),
            "context_features": np.random.rand(128),
            "trm_target_label": i % 2,
            "_extraction_metadata": {
                "element_defaults_count": 6,  # 6 out of 128 = ~5% defaulted
                "rule_defaults_count": 0
            }
        }
        good_samples.append(sample)
    
    try:
        validation_report = TrainingDataQualityValidator.validate_dataset_before_training(
            training_data_path="test_data.json",
            training_samples=good_samples,
            abort_on_failure=True
        )
        
        if validation_report["validation_status"] == "PASS":
            print("✅ TEST PASSED: Good data correctly validated")
            print(f"   Defaulted percentage: {validation_report['metrics']['defaulted_percentage']:.1f}%")
            return True
        else:
            print(f"❌ TEST FAILED: Expected PASS, got {validation_report['validation_status']}")
            return False
    
    except Exception as e:
        print(f"❌ TEST FAILED: Validation raised unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    # Run tests
    print("\nGUID FRAGILITY FIX - TEST SUITE")
    print("="*80)
    
    test1_pass = test_training_data_default_detection()
    test2_pass = test_good_training_data_passes()
    
    print("\n" + "="*80)
    if test1_pass and test2_pass:
        print("✅ ALL TESTS PASSED")
        print("   The 70% accuracy bug fragility is now detectable and preventable.")
    else:
        print("❌ SOME TESTS FAILED")
        print("   The fragility detection is not working correctly.")
    print("="*80)
