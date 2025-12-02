"""
Configuration and utilities for the Reasoning Layer.

Handles loading configuration files and providing utility functions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ReasoningConfig:
    """Configuration manager for Reasoning Layer."""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent
        self.templates_file = self.config_dir / "recommendation_templates.json"
        self.impact_metrics_file = self.config_dir / "impact_metrics.json"
        self.root_cause_rules_file = self.config_dir / "root_cause_rules.json"
        
        self.templates = self._load_templates()
        self.impact_config = self._load_impact_config()
        self.root_cause_rules = self._load_root_cause_rules()
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load recommendation templates from JSON file."""
        if not self.templates_file.exists():
            logger.warning(f"Templates file not found: {self.templates_file}")
            return {}
        
        try:
            with open(self.templates_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            return {}
    
    def _load_impact_config(self) -> Dict[str, Any]:
        """Load impact metrics configuration."""
        if not self.impact_metrics_file.exists():
            logger.warning(f"Impact metrics file not found: {self.impact_metrics_file}")
            return {}
        
        try:
            with open(self.impact_metrics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading impact config: {e}")
            return {}
    
    def _load_root_cause_rules(self) -> Dict[str, Any]:
        """Load root cause analysis rules."""
        if not self.root_cause_rules_file.exists():
            logger.warning(f"Root cause rules file not found: {self.root_cause_rules_file}")
            return {}
        
        try:
            with open(self.root_cause_rules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading root cause rules: {e}")
            return {}
    
    def get_templates_for_rule(self, rule_id: str) -> Dict[str, Any]:
        """Get recommendation templates for a specific rule."""
        templates = self.templates.get('rules', {})
        return templates.get(rule_id, self.templates.get('default', {}))
    
    def reload(self):
        """Reload configuration from files."""
        self.templates = self._load_templates()
        self.impact_config = self._load_impact_config()
        self.root_cause_rules = self._load_root_cause_rules()
        logger.info("Reasoning Layer configuration reloaded")


class BaseReasoningEngine:
    """Base class for reasoning engines."""
    
    def __init__(self):
        self.config = ReasoningConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """Format a template string with context values."""
        try:
            # Support both {key} and $key placeholder styles
            formatted = template.format(**context)
            return formatted
        except KeyError as e:
            self.logger.warning(f"Missing template variable: {e}")
            return template
    
    def _extract_context(self, failure: Dict[str, Any]) -> Dict[str, Any]:
        """Extract useful context from a failure for template formatting."""
        return {
            'element_id': failure.get('element_id', ''),
            'element_type': failure.get('element_type', ''),
            'element_name': failure.get('element_name', ''),
            'actual_value': failure.get('actual_value'),
            'required_value': failure.get('required_value'),
            'unit': failure.get('unit', ''),
            'rule_id': failure.get('rule_id', ''),
            'rule_name': failure.get('rule_name', ''),
            'severity': failure.get('severity', 'WARNING'),
            'difference': self._calculate_difference(
                failure.get('actual_value'),
                failure.get('required_value')
            ),
        }
    
    @staticmethod
    def _calculate_difference(actual, required) -> Optional[float]:
        """Calculate numerical difference between actual and required."""
        try:
            if isinstance(actual, (int, float)) and isinstance(required, (int, float)):
                return required - actual
            return None
        except:
            return None
