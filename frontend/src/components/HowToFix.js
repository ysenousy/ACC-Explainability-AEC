import React, { useState } from 'react';
import { Wrench, Lightbulb, ChevronDown, ChevronUp, CheckCircle2, AlertCircle, Zap, Code, Settings, Target } from 'lucide-react';
import '../styles/ReasoningTabs.css';

/**
 * HowToFix Tab
 * 
 * Displays tiered recommendations for fixing compliance failures.
 * Shows quick fixes, medium, comprehensive, and systemic solutions.
 */
function HowToFix({ recommendations, failures }) {
  const [expandedRecs, setExpandedRecs] = useState({});
  const [selectedTier, setSelectedTier] = useState('quick');

  if (!recommendations || !failures || failures.length === 0) {
    return (
      <div className="reasoning-empty-state">
        <Wrench size={32} />
        <h3>No Recommendations</h3>
        <p>No failures to recommend fixes for.</p>
      </div>
    );
  }

  const toggleRec = (recId) => {
    setExpandedRecs(prev => ({
      ...prev,
      [recId]: !prev[recId]
    }));
  };

  const getRecommendations = () => {
    switch(selectedTier) {
      case 'quick':
        return recommendations.quick_fixes || [];
      case 'medium':
        return recommendations.medium_fixes || [];
      case 'comprehensive':
        return recommendations.comprehensive_fixes || [];
      case 'systemic':
        return recommendations.systemic_fixes || [];
      default:
        return [];
    }
  };

  const getTierInfo = () => {
    const tiers = {
      quick: {
        icon: Zap,
        label: 'Quick Fixes',
        desc: 'Fast, targeted solutions for individual failures',
        color: 'green',
        longDesc: 'Minimal changes to individual elements. Best for isolated compliance issues.'
      },
      medium: {
        icon: Wrench,
        label: 'Standard Solutions',
        desc: 'Coordinated fixes requiring moderate effort',
        color: 'yellow',
        longDesc: 'Coordinated changes affecting related elements. Requires planning but limited scope.'
      },
      comprehensive: {
        icon: AlertCircle,
        label: 'Comprehensive',
        desc: 'Complete solutions for major issues',
        color: 'orange',
        longDesc: 'Complete architectural redesign for major non-compliance areas.'
      },
      systemic: {
        icon: CheckCircle2,
        label: 'Systemic Fixes',
        desc: 'Root cause solutions affecting multiple elements',
        color: 'red',
        longDesc: 'Fundamental design changes addressing root causes across the building.'
      }
    };
    return tiers[selectedTier];
  };

  const currentRecs = getRecommendations();
  const tierInfo = getTierInfo();
  const TierIcon = tierInfo.icon;

  return (
    <div className="how-to-fix-container">
      <div className="how-to-fix-header">
        <div className="header-content">
          <Lightbulb size={24} className="header-icon" />
          <div className="header-text">
            <h2>How To Fix Compliance Issues</h2>
            <p>Actionable, tiered recommendations to resolve failures</p>
          </div>
        </div>
      </div>

      {/* Tier Selection */}
      <div className="tier-selector">
        {['quick', 'medium', 'comprehensive', 'systemic'].map(tier => (
          <button
            key={tier}
            className={`tier-button tier-${tier} ${selectedTier === tier ? 'active' : ''}`}
            onClick={() => setSelectedTier(tier)}
          >
            <span className="tier-name">
              {tier === 'quick' && 'Quick'}
              {tier === 'medium' && 'Medium'}
              {tier === 'comprehensive' && 'Comprehensive'}
              {tier === 'systemic' && 'Systemic'}
            </span>
            <span className="tier-count">
              {tier === 'quick' && (recommendations.quick_fixes?.length || 0)}
              {tier === 'medium' && (recommendations.medium_fixes?.length || 0)}
              {tier === 'comprehensive' && (recommendations.comprehensive_fixes?.length || 0)}
              {tier === 'systemic' && (recommendations.systemic_fixes?.length || 0)}
            </span>
          </button>
        ))}
      </div>

      {/* Tier Info */}
      <div className={`tier-info-card tier-${selectedTier}`}>
        <div className="tier-info-icon-wrapper">
          <TierIcon size={28} />
        </div>
        <div className="tier-info-text">
          <h3>{tierInfo.label}</h3>
          <p className="tier-short-desc">{tierInfo.desc}</p>
          <p className="tier-long-desc">{tierInfo.longDesc}</p>
        </div>
      </div>

      {/* Recommendations List */}
      {currentRecs.length === 0 ? (
        <div className="no-recommendations">
          <p>No {tierInfo.label.toLowerCase()} available for current failures.</p>
        </div>
      ) : (
        <div className="recommendations-list">
          {currentRecs.map((rec, idx) => (
            <div key={idx} className="recommendation-card">
              {/* Header */}
              <div 
                className="recommendation-header"
                onClick={() => toggleRec(idx)}
                role="button"
                tabIndex={0}
              >
                <div className="rec-title-section">
                  <h4>{rec.title}</h4>
                  <div className="rec-meta">
                    <span className={`effort-badge effort-${(rec.estimated_effort || 'MEDIUM').toLowerCase()}`}>
                      {rec.estimated_effort || 'MEDIUM'} Effort
                    </span>
                    {rec.affected_elements && (
                      <span className="affected-count">
                        {rec.affected_elements} element{rec.affected_elements !== 1 ? 's' : ''}
                      </span>
                    )}
                  </div>
                </div>
                {expandedRecs[idx] ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </div>

              {/* Expanded Content */}
              {expandedRecs[idx] && (
                <div className="recommendation-details">
                  {/* Description */}
                  <div className="rec-section">
                    <h5>What To Do</h5>
                    <p>{rec.description}</p>
                  </div>

                  {/* IFC Modifications Required */}
                  {rec.ifc_modifications && (
                    <div className="rec-section ifc-modifications-section">
                      <div className="section-header-with-icon">
                        <Code size={16} />
                        <h5>IFC Modifications Required</h5>
                      </div>
                      <ul className="modifications-list">
                        {rec.ifc_modifications.map((mod, modIdx) => (
                          <li key={modIdx}>
                            <span className="mod-icon">📝</span>
                            <span className="mod-text">{mod}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* IFC Implementation Steps */}
                  {rec.ifc_steps ? (
                    <div className="rec-section steps-section">
                      <div className="section-header-with-icon">
                        <Settings size={16} />
                        <h5>How to Modify IFC File</h5>
                      </div>
                      <ol className="steps-list enhanced-steps">
                        {rec.ifc_steps.map((step, stepIdx) => (
                          <li key={stepIdx}>
                            <span className="step-number">{stepIdx + 1}</span>
                            <span className="step-text">{step}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : (
                    rec.implementation_steps && (
                      <div className="rec-section steps-section">
                        <div className="section-header-with-icon">
                          <Settings size={16} />
                          <h5>Implementation Steps</h5>
                        </div>
                        <ol className="steps-list enhanced-steps">
                          {rec.implementation_steps.map((step, stepIdx) => (
                            <li key={stepIdx}>
                              <span className="step-number">{stepIdx + 1}</span>
                              <span className="step-text">{step}</span>
                            </li>
                          ))}
                        </ol>
                      </div>
                    )
                  )}

                  {/* Effort & Complexity */}
                  <div className="rec-estimates">
                    {rec.complexity && (
                      <div className={`complexity-badge complexity-${rec.complexity.toLowerCase()}`}>
                        <span className="complexity-label">Complexity</span>
                        <span className="complexity-level">{rec.complexity}</span>
                      </div>
                    )}
                    {rec.estimated_effort && (
                      <div className={`effort-badge-large effort-${(rec.estimated_effort || '').toLowerCase()}`}>
                        <span className="effort-label">Effort Level</span>
                        <span className="effort-text">{rec.estimated_effort}</span>
                      </div>
                    )}
                  </div>

                  {/* Regulatory Basis */}
                  {rec.regulatory_basis && (
                    <div className="rec-section regulatory-basis-section">
                      <div className="section-header-with-icon">
                        <Target size={16} />
                        <h5>Regulatory Basis</h5>
                      </div>
                      <div className="regulatory-content">
                        <p>{rec.regulatory_basis}</p>
                      </div>
                    </div>
                  )}
                  {rec.regulatory_pathway && (
                    <div className="rec-section regulatory-basis-section">
                      <div className="section-header-with-icon">
                        <Target size={16} />
                        <h5>Regulatory Compliance</h5>
                      </div>
                      <div className="regulatory-content">
                        <p>{rec.regulatory_pathway}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Quick Reference */}
      <div className="recommendation-guide">
        <h4>Recommendation Tiers Guide</h4>
        <div className="guide-items">
          <div className="guide-item quick">
            <span className="guide-label">Quick Fixes</span>
            <span className="guide-desc">Individual modifications, minimal coordination</span>
          </div>
          <div className="guide-item medium">
            <span className="guide-label">Standard</span>
            <span className="guide-desc">Coordinated changes, requires planning</span>
          </div>
          <div className="guide-item comprehensive">
            <span className="guide-label">Comprehensive</span>
            <span className="guide-desc">Major design changes, full architectural work</span>
          </div>
          <div className="guide-item systemic">
            <span className="guide-label">Systemic</span>
            <span className="guide-desc">Root cause fixes, affects multiple areas</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default HowToFix;
