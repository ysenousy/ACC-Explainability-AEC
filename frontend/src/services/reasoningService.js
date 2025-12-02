/**
 * Reasoning Service - API integration for Reasoning Layer
 * 
 * Handles communication with backend reasoning engines:
 * - Failure analysis and explanations
 * - Impact metrics calculation
 * - Recommendation generation
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Default impact metrics configuration (used if API not available)
const DEFAULT_IMPACT_CONFIG = {
  metrics: {
    cost_multipliers: {
      // Design phase costs (not construction)
      // Based on design modifications, not physical changes
      per_element: 50,  // Design review and modification cost per element
      high_severity_adjustment: 200,  // Additional cost for critical design issues
      complex_fix_multiplier: 1.5,
      systemic_fix_multiplier: 2.0
    },
    timeline_multipliers: {
      // Design phase timeline (in days/weeks, not months)
      avg_resolution_weeks_per_failure: 0.5,  // ~2-3 days to modify design per failure
      high_severity_adjustment_days: 1,
      systemic_fix_weeks: 1  // 1 week for systemic design changes
    }
  }
};

class ReasoningService {
  constructor() {
    this.impactConfig = null;
  }

  /**
   * Load impact metrics configuration from backend or use defaults
   */
  async loadImpactConfig() {
    if (this.impactConfig) {
      return this.impactConfig;
    }

    try {
      // Try to fetch from backend
      const response = await fetch(`${API_BASE}/api/config/impact-metrics`);
      if (response.ok) {
        this.impactConfig = await response.json();
        return this.impactConfig;
      }
    } catch (err) {
      console.warn('Could not load impact config from backend, using defaults:', err);
    }

    // Use defaults
    this.impactConfig = DEFAULT_IMPACT_CONFIG;
    return this.impactConfig;
  }
  
  /**
   * Get failures from compliance check results
   */
  async getFailuresFromCompliance(complianceResults) {
    try {
      if (!complianceResults || !complianceResults.results) {
        return [];
      }

      // Filter to only failures
      const failures = complianceResults.results.filter(r => r.passed === false);
      
      // Transform to reasoning layer format
      return failures.map((failure, idx) => ({
        id: `${failure.rule_id}-${failure.element_guid}-${idx}`,
        element_id: failure.element_guid || failure.element_id,
        element_type: failure.element_type,
        element_name: failure.element_name,
        rule_id: failure.rule_id,
        rule_name: failure.rule_name,
        severity: failure.severity,
        actual_value: failure.actual_value,
        required_value: failure.required_value,
        unit: failure.unit || '',
        short_explanation: failure.explanation,
        rule_description: failure.explanation,
        element_properties: failure.properties || {},
        regulatory_reference: {
          regulation: failure.regulation || 'Unknown',
          section: failure.section || 'Unknown',
          jurisdiction: failure.jurisdiction || 'Unknown',
          source_link: failure.source_link
        }
      }));
    } catch (err) {
      console.error('Error processing failures:', err);
      throw err;
    }
  }

  /**
   * Analyze impact of failures using configuration-driven calculations
   */
  async analyzeImpact(failures, totalElements) {
    try {
      // Load configuration
      const config = await this.loadImpactConfig();
      const costMult = config.metrics.cost_multipliers;
      const timeMult = config.metrics.timeline_multipliers;

      // Calculate metrics locally
      const failuresByType = {};
      const failureBySeverity = {};
      const affectedElements = new Set();

      failures.forEach(failure => {
        // Track affected elements
        affectedElements.add(failure.element_id);

        // Group by type
        const type = failure.element_type || 'Unknown';
        failuresByType[type] = (failuresByType[type] || 0) + 1;

        // Group by severity
        const severity = failure.severity || 'WARNING';
        failureBySeverity[severity] = (failureBySeverity[severity] || 0) + 1;
      });

      const totalAffected = affectedElements.size;
      // Handle case where totalElements is 0 to avoid division by zero
      const percentage = totalElements > 0 ? (totalAffected / totalElements) * 100 : 0;

      // Estimate costs using configuration values
      const basePerElement = costMult.per_element || 500;
      const errorAdjustment = costMult.high_severity_adjustment || 1000;
      const errorCount = failureBySeverity['ERROR'] || 0;
      
      const estimatedBase = (totalAffected * basePerElement) + (errorCount * errorAdjustment);
      const costLow = Math.floor(estimatedBase * 0.8);
      const costHigh = Math.floor(estimatedBase * 1.2);

      // Timeline estimation using configuration
      const avgWeeksPerFailure = timeMult.avg_resolution_weeks_per_failure || 2.5;
      const estimatedWeeks = totalAffected / avgWeeksPerFailure;
      let timeline;
      if (estimatedWeeks < 1) timeline = '< 1 week';
      else if (estimatedWeeks < 2) timeline = '1-2 weeks';
      else if (estimatedWeeks < 4) timeline = '2-4 weeks';
      else if (estimatedWeeks < 8) timeline = '1-2 months';
      else timeline = `${Math.floor(estimatedWeeks / 4)}+ months`;

      return {
        total_affected_elements: totalAffected,
        affected_by_type: failuresByType,
        percentage_of_building: parseFloat(percentage.toFixed(2)),
        failure_distribution: failureBySeverity,
        cost_estimate_range: `$${costLow.toLocaleString()} - $${costHigh.toLocaleString()}`,
        implementation_timeline: timeline
      };
    } catch (err) {
      console.error('Error analyzing impact:', err);
      throw err;
    }
  }

  /**
   * Generate recommendations for failures
   */
  async generateRecommendations(failures) {
    try {
      // Group failures by rule
      const failuresByRule = {};
      failures.forEach(failure => {
        const ruleId = failure.rule_id || 'unknown';
        if (!failuresByRule[ruleId]) {
          failuresByRule[ruleId] = [];
        }
        failuresByRule[ruleId].push(failure);
      });

      // Generate recommendations for each rule group
      const recommendations = {
        quick_fixes: [],
        medium_fixes: [],
        comprehensive_fixes: [],
        systemic_fixes: []
      };

      for (const [ruleId, ruleFails] of Object.entries(failuresByRule)) {
        // Create generic recommendations based on failure count
        const firstFailure = ruleFails[0];
        const failureCount = ruleFails.length;

        // Quick Fix
        const quickFix = this._generateQuickFix(ruleId, firstFailure, failureCount);
        if (quickFix) recommendations.quick_fixes.push(quickFix);

        // Medium Fix
        if (failureCount > 1) {
          const mediumFix = this._generateMediumFix(ruleId, firstFailure, failureCount);
          if (mediumFix) recommendations.medium_fixes.push(mediumFix);
        }

        // Comprehensive Fix
        if (failureCount > 3) {
          const comprehensiveFix = this._generateComprehensiveFix(ruleId, firstFailure, failureCount);
          if (comprehensiveFix) recommendations.comprehensive_fixes.push(comprehensiveFix);
        }

        // Systemic Fix
        if (failureCount > 5) {
          const systemicFix = this._generateSystemicFix(ruleId, firstFailure, failureCount);
          if (systemicFix) recommendations.systemic_fixes.push(systemicFix);
        }
      }

      return recommendations;
    } catch (err) {
      console.error('Error generating recommendations:', err);
      throw err;
    }
  }

  _generateQuickFix(ruleId, failure, count) {
    return {
      title: `Modify ${failure.element_type} Properties - ${failure.rule_name}`,
      description: `Update IFC properties for ${count} ${failure.element_type}(s) to meet ${failure.rule_name} requirements`,
      ifc_modifications: [
        `Update element property: ${this._getPropertyNameFromRule(failure.rule_id)}`,
        `Current value: ${failure.actual_value}${failure.unit}`,
        `Required minimum: ${failure.required_value}${failure.unit}`,
        `Apply change to ${count} element(s)`
      ],
      affected_elements: count,
      complexity: 'LOW',
      regulatory_basis: `${failure.regulatory_reference?.regulation} - ${failure.regulatory_reference?.section}`,
      ifc_steps: [
        '1. Open IFC model in authoring tool',
        `2. Select ${count} affected ${failure.element_type}(s)`,
        `3. Modify property to meet ${failure.required_value}${failure.unit} requirement`,
        '4. Save and export IFC file',
        '5. Re-run compliance check to verify'
      ]
    };
  }

  _generateMediumFix(ruleId, failure, count) {
    return {
      title: `Redesign ${failure.element_type} Layout - ${failure.rule_name}`,
      description: `Systematic IFC redesign of ${count} element(s) with layout/placement adjustments`,
      ifc_modifications: [
        `Modify placement (location coordinates) for affected elements`,
        `Update dimensions to meet ${failure.required_value}${failure.unit} requirement`,
        `Adjust connected relationships between elements`,
        `Update relevant property sets (BaseQuantities, classification)`
      ],
      affected_elements: count,
      complexity: 'MEDIUM',
      regulatory_basis: `${failure.regulatory_reference?.regulation} - ${failure.regulatory_reference?.section}`,
      ifc_steps: [
        '1. Analyze spatial relationships in IFC model',
        `2. Identify ${count} elements needing repositioning/resizing`,
        '3. Modify element geometry and placement properties',
        '4. Update connected element relationships',
        '5. Verify no conflicts with adjacent elements',
        '6. Re-run compliance check'
      ]
    };
  }

  _generateComprehensiveFix(ruleId, failure, count) {
    return {
      title: `Redesign ${failure.element_type} System - ${failure.rule_name}`,
      description: `Complete architectural redesign affecting ${count} element(s) and related components`,
      ifc_modifications: [
        `Redefine spatial hierarchy and relationships`,
        `Modify element types or classifications if needed`,
        `Update parent-child relationships in spatial structure`,
        `Adjust all affected property sets and attributes`,
        `Update documentation and classifications`
      ],
      affected_elements: count,
      complexity: 'HIGH',
      regulatory_basis: `${failure.regulatory_reference?.regulation} - ${failure.regulatory_reference?.section}`,
      ifc_steps: [
        '1. Review complete spatial/structural organization',
        `2. Redesign layout to accommodate ${failure.required_value}${failure.unit} requirements`,
        '3. Modify IFC spatial structure and element hierarchy',
        '4. Update all affected elements and relationships',
        '5. Validate spatial hierarchy consistency',
        '6. Run comprehensive compliance audit'
      ]
    };
  }

  _generateSystemicFix(ruleId, failure, count) {
    return {
      title: `Fix Root Cause - ${failure.rule_name} (${count} elements)`,
      description: `Address underlying design pattern issue affecting ${count} element(s)`,
      ifc_modifications: [
        `Identify and fix repeating pattern causing failures`,
        `Update standardized element template/configuration`,
        `Apply fix systematically to all affected instances`,
        `Update classification scheme if needed`,
        `Document design decisions in IFC metadata`
      ],
      affected_elements: count,
      complexity: 'HIGH',
      regulatory_basis: `${failure.regulatory_reference?.regulation} - ${failure.regulatory_reference?.section}`,
      ifc_steps: [
        '1. Identify root cause pattern (e.g., similar element types failing same rule)',
        `2. Modify the source/template for this ${failure.element_type} type`,
        `3. Apply systematic changes to all ${count} instances`,
        '4. Update design standards documented in IFC',
        '5. Verify all instances now comply',
        '6. Run full compliance audit'
      ]
    };
  }

  _getPropertyNameFromRule(ruleId) {
    // Map rule IDs to IFC property names
    const propertyMap = {
      'ADA_DOOR_MIN_CLEAR_WIDTH': 'IfcDoorType.OverallWidth',
      'CORRIDOR_MIN_WIDTH': 'IfcSpace.Width',
      'EGRESS_MIN_HEIGHT': 'IfcDoor.OverallHeight',
      'MIN_FLOOR_AREA': 'IfcSpace.Area',
      'DOOR_HEIGHT_REQUIREMENT': 'IfcDoor.OverallHeight'
    };
    return propertyMap[ruleId] || 'Property';
  }

  /**
   * Get failure summary statistics
   */
  async getFailureSummary(failures) {
    try {
      const summary = {
        total_failures: failures.length,
        by_severity: {},
        by_rule: {},
        by_element_type: {}
      };

      failures.forEach(failure => {
        // By severity
        const sev = failure.severity || 'WARNING';
        summary.by_severity[sev] = (summary.by_severity[sev] || 0) + 1;

        // By rule
        const rule = failure.rule_id || 'unknown';
        summary.by_rule[rule] = (summary.by_rule[rule] || 0) + 1;

        // By element type
        const type = failure.element_type || 'unknown';
        summary.by_element_type[type] = (summary.by_element_type[type] || 0) + 1;
      });

      return summary;
    } catch (err) {
      console.error('Error generating summary:', err);
      throw err;
    }
  }

  /**
   * Get most affected elements
   */
  async getMostAffectedElements(failures, limit = 10) {
    try {
      const elementFailures = {};

      failures.forEach(failure => {
        const elementId = failure.element_id || 'unknown';
        if (!elementFailures[elementId]) {
          elementFailures[elementId] = {
            element_id: elementId,
            element_type: failure.element_type,
            element_name: failure.element_name,
            failure_count: 0
          };
        }
        elementFailures[elementId].failure_count += 1;
      });

      return Object.values(elementFailures)
        .sort((a, b) => b.failure_count - a.failure_count)
        .slice(0, limit);
    } catch (err) {
      console.error('Error getting most affected elements:', err);
      throw err;
    }
  }
}

export default new ReasoningService();
