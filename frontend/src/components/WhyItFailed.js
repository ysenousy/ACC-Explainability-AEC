import React, { useState } from 'react';
import { ChevronDown, ChevronUp, AlertCircle, BookOpen, ExternalLink, CheckCircle } from 'lucide-react';
import '../styles/ReasoningTabs.css';

/**
 * WhyItFailed Tab
 * 
 * Displays detailed explanations for why compliance rules failed.
 * Shows rule details, regulatory context, and specific failure reasons.
 */
function WhyItFailed({ failures }) {
  const [expandedFailures, setExpandedFailures] = useState({});

  if (!failures || failures.length === 0) {
    return (
      <div className="reasoning-empty-state">
        <CheckCircle size={32} />
        <h3>No Failures</h3>
        <p>All evaluated elements are compliant with selected rules.</p>
      </div>
    );
  }

  const toggleFailure = (failureId) => {
    setExpandedFailures(prev => ({
      ...prev,
      [failureId]: !prev[failureId]
    }));
  };

  return (
    <div className="why-it-failed-container">
      <div className="tab-info">
        <AlertCircle size={20} />
        <p>Understanding why elements failed compliance checks</p>
      </div>

      <div className="failures-list">
        {failures.map((failure, idx) => (
          <div key={`${failure.element_id}-${failure.rule_id}-${idx}`} className="failure-card">
            {/* Header */}
            <div 
              className="failure-header"
              onClick={() => toggleFailure(idx)}
              role="button"
              tabIndex={0}
            >
              <div className="failure-title">
                <span className={`severity-badge severity-${(failure.severity || 'WARNING').toLowerCase()}`}>
                  {failure.severity || 'WARNING'}
                </span>
                <div className="title-text">
                  <h4>{failure.rule_name}</h4>
                  <p className="element-ref">{failure.element_name} ({failure.element_type})</p>
                </div>
              </div>
              {expandedFailures[idx] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </div>

            {/* Expanded Content */}
            {expandedFailures[idx] && (
              <div className="failure-details">
                {/* Short Explanation */}
                <div className="detail-section">
                  <h5>What Failed</h5>
                  <p className="explanation-text">
                    {failure.short_explanation || `${failure.element_name} did not meet rule requirements.`}
                  </p>
                </div>

                {/* Actual vs Required */}
                {failure.actual_value !== undefined && failure.required_value !== undefined && (
                  <div className="detail-section comparison">
                    <h5>Measurements</h5>
                    <div className="value-comparison">
                      <div className="value-item actual">
                        <span className="label">Current</span>
                        <span className="value">{failure.actual_value}{failure.unit || ''}</span>
                      </div>
                      <div className="comparison-arrow">→</div>
                      <div className="value-item required">
                        <span className="label">Required</span>
                        <span className="value">{failure.required_value}{failure.unit || ''}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Rule Description */}
                <div className="detail-section">
                  <h5>Rule Description</h5>
                  <p className="rule-description">
                    {failure.rule_description || 'No description available.'}
                  </p>
                </div>

                {/* Regulatory Reference */}
                {failure.regulatory_reference && (
                  <div className="detail-section regulatory">
                    <h5>Regulatory Reference</h5>
                    <div className="regulatory-info">
                      <p><strong>Regulation:</strong> {failure.regulatory_reference.regulation}</p>
                      <p><strong>Section:</strong> {failure.regulatory_reference.section}</p>
                      <p><strong>Jurisdiction:</strong> {failure.regulatory_reference.jurisdiction}</p>
                      {failure.regulatory_reference.source_link && (
                        <a 
                          href={failure.regulatory_reference.source_link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="reference-link"
                        >
                          <ExternalLink size={14} />
                          View Source
                        </a>
                      )}
                    </div>
                  </div>
                )}

                {/* Element Details */}
                {failure.element_properties && Object.keys(failure.element_properties).length > 0 && (
                  <div className="detail-section">
                    <h5>Element Properties</h5>
                    <div className="properties-grid">
                      {Object.entries(failure.element_properties).slice(0, 6).map(([key, value]) => (
                        <div key={key} className="property-item">
                          <span className="property-key">{key}</span>
                          <span className="property-value">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default WhyItFailed;
