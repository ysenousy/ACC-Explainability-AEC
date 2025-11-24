/**
 * Reasoning Layer API Service
 * 
 * Provides functions to interact with the backend Reasoning Layer endpoints.
 */

const API_BASE = process.env.REACT_APP_API_URL || '/api';

/**
 * Validate the reasoning layer is ready
 */
export const validateReasoningLayer = async () => {
  const response = await fetch(`${API_BASE}/reasoning/validate`);
  return response.json();
};

/**
 * Get all rules from the rules catalogue
 */
export const getAllRulesFromCatalogue = async () => {
  const response = await fetch(`${API_BASE}/reasoning/all-rules`);
  if (!response.ok) {
    throw new Error('Failed to fetch rules catalogue');
  }
  return response.json();
};

/**
 * Get explanation for why a rule exists
 */
export const explainRule = async (ruleId, options = {}) => {
  const response = await fetch(`${API_BASE}/reasoning/explain-rule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      rule_id: ruleId,
      applicable_elements: options.applicableElements || [],
      elements_checked: options.elementsChecked || 0,
      elements_passing: options.elementsPassing || 0,
      elements_failing: options.elementsFailing || 0
    })
  });
  return response.json();
};

/**
 * Get explanation for why elements failed and how to fix them
 */
export const analyzeFailure = async (elementData) => {
  const response = await fetch(`${API_BASE}/reasoning/analyze-failure`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(elementData)
  });
  return response.json();
};

/**
 * Get explanation for why elements PASSED compliance checks
 */
export const analyzePass = async (elementData) => {
  const response = await fetch(`${API_BASE}/reasoning/analyze-pass`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(elementData)
  });
  return response.json();
};

/**
 * Enrich compliance results with reasoning explanations
 */
export const enrichComplianceWithReasoning = async (complianceResults) => {
  const response = await fetch(`${API_BASE}/reasoning/enrich-compliance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ compliance_results: complianceResults })
  });
  return response.json();
};

/**
 * Check compliance and include reasoning
 */
export const checkComplianceWithReasoning = async (graph) => {
  const response = await fetch(`${API_BASE}/compliance/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ graph })
  });
  
  if (!response.ok) {
    throw new Error('Compliance check failed');
  }

  const complianceData = await response.json();
  
  if (!complianceData.success) {
    throw new Error(complianceData.error || 'Compliance check failed');
  }

  // Optionally enrich with reasoning
  try {
    const enriched = await enrichComplianceWithReasoning(complianceData);
    if (enriched.success) {
      return enriched.enriched_results;
    }
  } catch (err) {
    console.warn('Could not enrich with reasoning:', err);
  }

  return complianceData;
};

/**
 * Group failures by element
 */
export const groupFailuresByElement = (complianceResults) => {
  const failures = {};

  complianceResults.results?.forEach(result => {
    // Only include actual failures (passed === false), exclude unable-to-evaluate (passed === null)
    if (result.passed === false) {
      const elementGuid = result.element_guid;
      if (!failures[elementGuid]) {
        failures[elementGuid] = {
          element_id: elementGuid,
          element_type: result.element_type,
          element_name: result.element_name,
          failed_rules: []
        };
      }
      failures[elementGuid].failed_rules.push({
        rule_id: result.rule_id,
        rule_name: result.rule_name,
        actual_value: result.actual_value,
        required_value: result.required_value,
        unit: result.unit || ''
      });
    }
  });

  return failures;
};

/**
 * Group passes by element
 */
export const groupPassesByElement = (complianceResults) => {
  const passes = {};

  complianceResults.results?.forEach(result => {
    // Only include actual passes (passed === true), exclude unable-to-evaluate (passed === null)
    if (result.passed === true) {
      const elementGuid = result.element_guid;
      if (!passes[elementGuid]) {
        passes[elementGuid] = {
          element_id: elementGuid,
          element_type: result.element_type,
          element_name: result.element_name,
          passed_rules: []
        };
      }
      passes[elementGuid].passed_rules.push({
        rule_id: result.rule_id,
        rule_name: result.rule_name,
        actual_value: result.actual_value,
        required_value: result.required_value,
        unit: result.unit || ''
      });
    }
  });

  return passes;
};

/**
 * Format severity for display
 */
export const formatSeverity = (severity) => {
  const severityMap = {
    'critical': 'CRITICAL',
    'high': 'HIGH',
    'medium': 'MEDIUM',
    'low': 'LOW',
    'info': 'INFO'
  };
  return severityMap[severity?.toLowerCase()] || severity;
};

/**
 * Get severity color for display
 */
export const getSeverityColor = (severity) => {
  const colorMap = {
    'critical': '#d9534f',
    'high': '#f0ad4e',
    'medium': '#5bc0de',
    'low': '#5cb85c',
    'info': '#5cb85c'
  };
  return colorMap[severity?.toLowerCase()] || '#999';
};

/**
 * Get severity background color
 */
export const getSeverityBackgroundColor = (severity) => {
  const bgMap = {
    'critical': '#fee',
    'high': '#ffeaa7',
    'medium': '#d1ecf1',
    'low': '#d4edda',
    'info': '#d4edda'
  };
  return bgMap[severity?.toLowerCase()] || '#f9f9f9';
};

export default {
  validateReasoningLayer,
  getAllRulesFromCatalogue,
  explainRule,
  analyzeFailure,
  analyzePass,
  enrichComplianceWithReasoning,
  checkComplianceWithReasoning,
  groupFailuresByElement,
  groupPassesByElement,
  formatSeverity,
  getSeverityColor,
  getSeverityBackgroundColor
};
