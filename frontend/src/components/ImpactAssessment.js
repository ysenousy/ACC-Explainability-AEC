import React, { useState } from 'react';
import { BarChart3, TrendingUp, AlertTriangle, Info, ChevronDown, ChevronUp } from 'lucide-react';
import '../styles/ReasoningTabs.css';

/**
 * ImpactAssessment Tab
 * 
 * Displays metrics about the scope and severity of failures.
 * Shows affected elements, distribution, cost/timeline estimates.
 */
function ImpactAssessment({ failures, impactMetrics, totalElements }) {
  const [expandedSections, setExpandedSections] = useState({
    overview: true,
    distribution: true,
    mostAffected: false,
    timeline: false
  });

  console.log('[ImpactAssessment] Props received:', {
    totalElements,
    impactMetrics_total_affected: impactMetrics?.total_affected_elements,
    impactMetrics_percentage: impactMetrics?.percentage_of_building,
    failures_count: failures?.length
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  if (!failures || failures.length === 0) {
    return (
      <div className="reasoning-empty-state">
        <TrendingUp size={32} />
        <h3>No Failures to Assess</h3>
        <p>No compliance failures detected in this model.</p>
      </div>
    );
  }

  const totalAffected = impactMetrics?.total_affected_elements || (failures ? new Set(failures.map(f => f.element_id)).size : 0);
  const totalFailures = failures?.length || 0;
  
  // Use totalElements from backend (now includes total_elements from compliance results)
  // Use nullish coalescing (??) instead of || to handle 0 correctly
  const effectiveTotalElements = totalElements ?? 1; // Fallback to 1 to avoid division by zero
  
  console.log('[ImpactAssessment] Calculation values:', {
    effectiveTotalElements,
    totalAffected,
    totalFailures,
    received_totalElements: totalElements
  });
  
  // Impact rate: affected elements as percentage of total elements
  const percentage = impactMetrics?.percentage_of_building || (effectiveTotalElements > 0 ? (totalAffected / effectiveTotalElements * 100) : 0);
  
  // Compliance rate: non-affected elements as percentage of total elements
  // Only calculate if we have a meaningful total elements value (> totalAffected)
  let complianceRate = 0;
  if (effectiveTotalElements > 0 && effectiveTotalElements > totalAffected) {
    complianceRate = ((effectiveTotalElements - totalAffected) / effectiveTotalElements * 100).toFixed(1);
  } else if (effectiveTotalElements > 0 && effectiveTotalElements === totalAffected) {
    // All elements have failures
    complianceRate = 0;
  } else {
    // effectiveTotalElements is 1 (fallback), can't calculate meaningful rate
    complianceRate = 0;
  }
  
  console.log('[ImpactAssessment] Final rates:', {
    complianceRate: complianceRate,
    percentage: percentage
  });

  return (
    <div className="impact-assessment-container">
      <div className="tab-info">
        <BarChart3 size={20} />
        <p>Understanding the scope and severity of compliance failures</p>
      </div>

      {/* Compliance Overview */}
      <section className="impact-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('overview')}
          role="button"
          tabIndex={0}
        >
          <h3>Compliance Overview</h3>
          {expandedSections.overview ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>

        {expandedSections.overview && (
          <div className="section-content overview-metrics">
            <div className="metric-card">
              <div className="metric-label">Compliance Rate</div>
              <div className="metric-value">{complianceRate}%</div>
              <div className="metric-progress">
                <div 
                  className="progress-bar"
                  style={{width: `${complianceRate}%`}}
                ></div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Total Rule Violations</div>
              <div className="metric-value" style={{color: '#dc2626'}}>{totalFailures}</div>
              <div className="metric-subtitle">across {totalAffected} unique element(s)</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Affected Elements</div>
              <div className="metric-value" style={{color: '#f97316'}}>{totalAffected}</div>
              <div className="metric-subtitle">out of {effectiveTotalElements} total</div>
            </div>

            <div className="metric-card">
              <div className="metric-label">Impact Rate</div>
              <div className="metric-value" style={{color: '#dc2626'}}>{percentage.toFixed(1)}%</div>
              <div className="metric-subtitle">of building affected</div>
            </div>
          </div>
        )}

        {/* Explanation Card - Outside section-content for full width */}
        {expandedSections.overview && (
          <div style={{
            marginTop: '1.5rem',
            marginBottom: '2.5rem',
            padding: '1rem',
            backgroundColor: '#f0f9ff',
            border: '1px solid #0284c7',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            lineHeight: '1.5',
            color: '#0c4a6e',
            width: '100%',
            boxSizing: 'border-box'
          }}>
            <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>🎯 Understanding Impact Assessment:</div>
            <ul style={{ margin: '0.5rem 0', paddingLeft: '1.25rem' }}>
              <li><strong>Compliance Rate %</strong>: Percentage of building elements that are <strong>compliant</strong> (not affected)</li>
              <li><strong>Impact Rate %</strong>: Percentage of building elements that are <strong>affected</strong> by non-compliance</li>
              <li><strong>Affected Elements</strong>: Individual building components failing one or more rules</li>
              <li><strong>Total Elements</strong>: All building components in the model</li>
            </ul>
            <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', fontStyle: 'italic', opacity: 0.9 }}>
              Impact Assessment counts unique elements, so one element failing multiple rules counts as 1 affected element
            </div>
          </div>
        )}
      </section>

      {/* Failure Distribution */}
      <section className="impact-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('distribution')}
          role="button"
          tabIndex={0}
        >
          <h3>Failure Distribution</h3>
          {expandedSections.distribution ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>

        {expandedSections.distribution && (
          <div className="section-content">
            {/* By Element Type */}
            <div className="distribution-subsection">
              <h4>By Element Type</h4>
              <div className="distribution-list">
                {impactMetrics?.affected_by_type && Object.entries(impactMetrics.affected_by_type).map(([type, count]) => (
                  <div key={type} className="distribution-item">
                    <span className="element-type">{type}</span>
                    <div className="distribution-bar">
                      <div 
                        className="distribution-fill"
                        style={{width: `${(count / totalFailures) * 100}%`}}
                      ></div>
                    </div>
                    <span className="distribution-count">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* By Severity */}
            <div className="distribution-subsection">
              <h4>By Severity Level</h4>
              <div className="severity-grid">
                {impactMetrics?.failure_distribution && Object.entries(impactMetrics.failure_distribution).map(([severity, count]) => (
                  <div key={severity} className={`severity-card severity-${severity.toLowerCase()}`}>
                    <div className="severity-label">{severity}</div>
                    <div className="severity-count">{count}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Cost & Timeline Estimates */}
      <section className="impact-section">
        <div 
          className="section-header"
          onClick={() => toggleSection('timeline')}
          role="button"
          tabIndex={0}
        >
          <h3>Implementation Estimates</h3>
          {expandedSections.timeline ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>

        {expandedSections.timeline && (
          <div className="section-content estimates">
            {impactMetrics?.cost_estimate_range && (
              <div className="estimate-card">
                <h4>Design Modification Cost</h4>
                <div className="estimate-value">{impactMetrics.cost_estimate_range}</div>
                <p className="estimate-note">Design review and modification effort (not construction)</p>
              </div>
            )}

            {impactMetrics?.implementation_timeline && (
              <div className="estimate-card">
                <h4>Design Phase Timeline</h4>
                <div className="estimate-value">{impactMetrics.implementation_timeline}</div>
                <p className="estimate-note">Estimated duration for design modifications</p>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Key Insights */}
      <section className="impact-section insights">
        <div className="insights-header">
          <Info size={20} />
          <h3>Key Insights</h3>
        </div>
        <div className="insights-list">
          {percentage > 50 && (
            <div className="insight-item warning">
              <AlertTriangle size={16} />
              <span>More than half of elements have failures. Consider systemic solutions.</span>
            </div>
          )}
          {impactMetrics?.failure_distribution?.ERROR > 0 && (
            <div className="insight-item error">
              <AlertTriangle size={16} />
              <span>{impactMetrics.failure_distribution.ERROR} critical errors require immediate attention.</span>
            </div>
          )}
          {totalAffected < 5 && (
            <div className="insight-item success">
              <span>✓ Relatively few failures. Quick fixes may resolve most issues.</span>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default ImpactAssessment;
