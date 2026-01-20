"""
Training Diagnostics - Analyze and improve TRM training

Identifies issues with small dataset, data imbalance, and unrealistic accuracy.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import Counter
import numpy as np

logger = logging.getLogger(__name__)


class TrainingDataDiagnostics:
    """Diagnose training data issues"""
    
    @staticmethod
    def analyze_training_data(data_path: str) -> Dict[str, Any]:
        """
        Analyze training data and identify issues
        
        Args:
            data_path: Path to trm_training_data.json
            
        Returns:
            Comprehensive diagnostic report
        """
        if not Path(data_path).exists():
            return {"error": f"Training data not found at {data_path}"}
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        samples = data.get("training_samples", [])
        
        report = {
            "total_samples": len(samples),
            "issues": [],
            "warnings": [],
            "data_distribution": {},
            "feature_quality": {},
            "recommendations": []
        }
        
        if len(samples) == 0:
            report["issues"].append("❌ No training samples found")
            return report
        
        # 1. Check dataset size
        if len(samples) < 100:
            report["issues"].append(
                f"❌ CRITICAL: Only {len(samples)} samples (need minimum 300-500 for reliable training)"
            )
            report["recommendations"].append(
                "→ Run compliance checks on MORE IFC FILES to generate more samples"
            )
        elif len(samples) < 300:
            report["warnings"].append(
                f"⚠️  Only {len(samples)} samples (200-300 is borderline, 500+ is ideal)"
            )
        
        # 2. Check class balance
        labels = [s.get("trm_target_label", 0) for s in samples]
        label_counts = Counter(labels)
        total = len(labels)
        
        report["data_distribution"]["label_counts"] = dict(label_counts)
        report["data_distribution"]["label_percentages"] = {
            label: round(count / total * 100, 1) 
            for label, count in label_counts.items()
        }
        
        if len(label_counts) == 1:
            report["issues"].append(
                f"❌ CRITICAL: All samples are class {list(label_counts.keys())[0]} (no variation!)"
            )
            report["recommendations"].append(
                "→ Training data has no class imbalance - model will achieve 100% by always predicting the majority class"
            )
        elif min(label_counts.values()) / total < 0.1:
            report["warnings"].append(
                f"⚠️  Severe class imbalance: {label_counts[0]}% vs {label_counts[1]}%"
            )
            report["recommendations"].append(
                "→ Use weighted loss or data augmentation to handle imbalance"
            )
        
        # 3. Check feature quality
        if samples:
            sample = samples[0]
            
            # Check element features
            elem_features = sample.get("element_features", [])
            if isinstance(elem_features, (list, tuple)):
                elem_features = np.array(elem_features)
            else:
                elem_features = np.array([])
            
            if len(elem_features) == 0:
                report["issues"].append("❌ Element features are missing")
            else:
                report["feature_quality"]["element_features"] = {
                    "count": len(elem_features),
                    "mean": float(np.mean(elem_features)),
                    "std": float(np.std(elem_features)),
                    "min": float(np.min(elem_features)),
                    "max": float(np.max(elem_features)),
                }
            
            # Check rule features
            rule_features = sample.get("rule_features", [])
            if isinstance(rule_features, (list, tuple)):
                rule_features = np.array(rule_features)
            
            if len(rule_features) == 0:
                report["issues"].append("❌ Rule features are missing")
            else:
                report["feature_quality"]["rule_features"] = {
                    "count": len(rule_features),
                    "mean": float(np.mean(rule_features)),
                    "std": float(np.std(rule_features)),
                    "unique_values": len(np.unique(rule_features)),
                }
            
            # Check for zero/constant features
            all_features = []
            if isinstance(elem_features, np.ndarray):
                all_features.extend(elem_features)
            if isinstance(rule_features, np.ndarray):
                all_features.extend(rule_features)
            
            if all_features:
                all_features = np.array(all_features)
                unique_values = len(np.unique(all_features))
                if unique_values < 10:
                    report["warnings"].append(
                        f"⚠️  Features are mostly constant/placeholder ({unique_values} unique values across {len(all_features)} features)"
                    )
        
        # 4. Final diagnosis
        if not report["issues"]:
            report["status"] = "✅ Training data looks reasonable"
        else:
            report["status"] = f"❌ {len(report['issues'])} critical issues found"
        
        return report
    
    @staticmethod
    def analyze_training_metrics(metrics_path: str) -> Dict[str, Any]:
        """
        Analyze training metrics to detect overfitting
        
        Args:
            metrics_path: Path to training metrics JSON
            
        Returns:
            Analysis of training curves
        """
        if not Path(metrics_path).exists():
            return {"error": f"Metrics not found at {metrics_path}"}
        
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        if not metrics:
            return {"error": "No metrics found"}
        
        analysis = {
            "total_epochs": len(metrics),
            "overfitting_detected": False,
            "issues": [],
            "observations": []
        }
        
        # Extract accuracy values
        train_acc = [m.get("accuracy", 0) for m in metrics]
        val_acc = [m.get("val_accuracy", 0) for m in metrics if m.get("val_accuracy")]
        
        if val_acc:
            final_train_acc = train_acc[-1]
            final_val_acc = val_acc[-1]
            gap = final_train_acc - final_val_acc
            
            analysis["final_train_accuracy"] = round(final_train_acc, 4)
            analysis["final_val_accuracy"] = round(final_val_acc, 4)
            analysis["train_val_gap"] = round(gap, 4)
            
            if final_val_acc == 1.0:
                analysis["issues"].append(
                    "❌ Validation accuracy is 100% - likely data leakage or trivial task"
                )
            
            if gap > 0.15:
                analysis["overfitting_detected"] = True
                analysis["observations"].append(
                    f"⚠️  Overfitting detected: train={final_train_acc:.1%} vs val={final_val_acc:.1%}"
                )
            
            # Check if validation loss plateaued
            if len(metrics) > 5:
                val_losses = [m.get("val_loss", 0) for m in metrics[-5:] if m.get("val_loss")]
                if val_losses and max(val_losses) - min(val_losses) < 0.01:
                    analysis["observations"].append(
                        "ℹ️  Validation loss has plateaued (early stopping likely triggered)"
                    )
        
        return analysis


def print_diagnostic_report(data_path: str):
    """Print formatted diagnostic report"""
    
    print("\n" + "="*70)
    print("📊 TRM TRAINING DATA DIAGNOSTICS")
    print("="*70 + "\n")
    
    report = TrainingDataDiagnostics.analyze_training_data(data_path)
    
    # Print main status
    print(report.get("status", "Unknown"))
    print()
    
    # Print issues
    if report.get("issues"):
        print("🔴 CRITICAL ISSUES:")
        for issue in report["issues"]:
            print(f"  {issue}")
        print()
    
    # Print warnings
    if report.get("warnings"):
        print("🟡 WARNINGS:")
        for warning in report["warnings"]:
            print(f"  {warning}")
        print()
    
    # Print data distribution
    if report.get("data_distribution"):
        print("📈 DATA DISTRIBUTION:")
        dist = report["data_distribution"]
        if "label_percentages" in dist:
            for label, pct in dist["label_percentages"].items():
                print(f"  Class {label}: {pct}%")
        print()
    
    # Print feature quality
    if report.get("feature_quality"):
        print("🔍 FEATURE QUALITY:")
        for feature_type, stats in report["feature_quality"].items():
            print(f"  {feature_type}:")
            print(f"    - Dimensionality: {stats.get('count', 0)}")
            print(f"    - Mean: {stats.get('mean', 0):.4f}")
            print(f"    - Std: {stats.get('std', 0):.4f}")
        print()
    
    # Print recommendations
    if report.get("recommendations"):
        print("💡 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"  {rec}")
        print()
    
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    data_path = "data/trm_training_data.json"
    report = print_diagnostic_report(data_path)
