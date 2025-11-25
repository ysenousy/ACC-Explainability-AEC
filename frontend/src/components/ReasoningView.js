import React, { useState, useEffect } from 'react';
import { Zap, ChevronDown, ChevronUp, AlertCircle, CheckCircle, Lightbulb, Wrench, Book, AlertTriangle } from 'lucide-react';
import reasoningService from '../services/reasoningService';

function ReasoningView({ graph }) {
  const [activeTab, setActiveTab] = useState('rules');
  const [allRulesFromCatalogue, setAllRulesFromCatalogue] = useState([]);
  const [failureExplanations, setFailureExplanations] = useState([]);
  const [passExplanations, setPassExplanations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});
  const [rulesLoaded, setRulesLoaded] = useState(null);
  const [standards, setStandards] = useState({});
  // eslint-disable-next-line no-unused-vars
  const [complianceStats, setComplianceStats] = useState(null);

  useEffect(() => {
    if (!graph) return;
    validateReasoningLayer();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  const validateReasoningLayer = async () => {
    try {
      console.log('[ReasoningView] Validating reasoning layer...');
      const data = await reasoningService.validateReasoningLayer();
      console.log('[ReasoningView] Validation response:', data);
      
      if (data.success) {
        const rulesAreLoaded = data.validation.rules_loaded;
        console.log('[ReasoningView] Rules loaded status:', rulesAreLoaded);
        
        setRulesLoaded(rulesAreLoaded);
        setStandards(data.validation.standards || {});
        
        if (rulesAreLoaded) {
          console.log('[ReasoningView] Loading all rules from catalogue...');
          await loadAllRulesFromCatalogue();
          await loadReasoningData();
        } else {
          console.log('[ReasoningView] No rules loaded in reasoning engine yet');
        }
      } else {
        console.error('[ReasoningView] Validation failed:', data);
        setError('Validation failed: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      console.error('[ReasoningView] Validation error:', err);
      setError('Failed to validate reasoning layer: ' + err.message);
    }
  };

  const loadAllRulesFromCatalogue = async () => {
    try {
      console.log('Loading all rules from catalogue...');
      const response = await fetch('/api/reasoning/all-rules');
      if (!response.ok) {
        throw new Error('Failed to load rules catalogue');
      }
      
      const data = await response.json();
      console.log('Rules catalogue loaded:', data);
      
      if (data.success && data.rules) {
        setAllRulesFromCatalogue(data.rules);
        console.log(`Loaded ${data.rules.length} rules from catalogue (${data.regulatory_rules} regulatory, ${data.custom_rules} custom)`);
      }
    } catch (err) {
      console.error('Error loading rules catalogue:', err);
      setError('Failed to load rules catalogue: ' + err.message);
    }
  };

  const loadReasoningData = async () => {
    if (!graph) return;
    
    setLoading(true);
    setError(null);

    try {
      const complianceData = await reasoningService.checkComplianceWithReasoning(graph);
      if (!complianceData.results) {
        setError('Failed to perform compliance check');
        setLoading(false);
        return;
      }

      setComplianceStats({
        total_checks: complianceData.total_checks,
        passed: complianceData.passed,
        failed: complianceData.failed,
        unable: complianceData.unable
      });

      const failuresByElement = reasoningService.groupFailuresByElement(complianceData);
      const passesByElement = reasoningService.groupPassesByElement(complianceData);

      const explanations = [];
      for (const [, elementData] of Object.entries(failuresByElement)) {
        try {
          const failureData = await reasoningService.analyzeFailure(elementData);
          if (failureData.success && failureData.reasoning) {
            explanations.push(failureData.reasoning);
          }
        } catch (err) {
          console.error('Failed to get failure explanation:', err);
        }
      }
      setFailureExplanations(explanations);

      for (const [, elementData] of Object.entries(passesByElement)) {
        try {
          const passData = await reasoningService.analyzePass(elementData);
          if (passData.success && passData.reasoning) {
            setPassExplanations(prev => [...prev, passData.reasoning]);
          }
        } catch (err) {
          console.error('Failed to get pass explanation:', err);
        }
      }

    } catch (err) {
      setError(err.message);
      console.error('Error loading reasoning data:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleExpanded = (id) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  return (
    <div className="layer-view">
      <div className="layer-header">
        <Zap size={24} />
        <h2>Reasoning Layer</h2>
      </div>

      <div className="layer-content">
        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #ddd', marginBottom: '1.5rem', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex' }}>
            <button
              onClick={() => setActiveTab('overview')}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: activeTab === 'overview' ? '#f0f7ff' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'overview' ? '2px solid #0066cc' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: activeTab === 'overview' ? 'bold' : 'normal'
            }}
          >
            <Book size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('rules')}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: activeTab === 'rules' ? '#f0f7ff' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'rules' ? '2px solid #0066cc' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: activeTab === 'rules' ? 'bold' : 'normal'
            }}
          >
            <Lightbulb size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Why Rules Exist ({allRulesFromCatalogue.length})
          </button>
          <button
            onClick={() => setActiveTab('failures')}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: activeTab === 'failures' ? '#f0f7ff' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'failures' ? '2px solid #0066cc' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: activeTab === 'failures' ? 'bold' : 'normal'
            }}
          >
            <Wrench size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Failures & Fixes
          </button>
          <button
            onClick={() => setActiveTab('passes')}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: activeTab === 'passes' ? '#f0f7ff' : 'transparent',
              border: 'none',
              borderBottom: activeTab === 'passes' ? '2px solid #0066cc' : '2px solid transparent',
              cursor: 'pointer',
              fontWeight: activeTab === 'passes' ? 'bold' : 'normal'
            }}
          >
            <CheckCircle size={16} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            Passes & Benefits
          </button>
          </div>
          <button
            onClick={validateReasoningLayer}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: '#f0f7ff',
              border: '1px solid #0066cc',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              marginLeft: 'auto',
              marginTop: '-2px'
            }}
            title="Refresh to check if rules have been imported"
          >
            Refresh Rules Status
          </button>
        </div>

        {/* Show warning if rules not loaded */}
        {rulesLoaded === false && (
          <div style={{
            padding: '1rem',
            textAlign: 'center',
            backgroundColor: '#fef3c7',
            borderRadius: '0.5rem',
            border: '2px solid #f59e0b',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem',
            marginBottom: '1rem'
          }}>
            <AlertTriangle size={48} style={{ color: '#f59e0b' }} />
            <div>
              <h3 style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '1.1rem' }}>
                Rules Import Required
              </h3>
              <p style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '0.95rem' }}>
                You must import regulatory rules before accessing the reasoning layer.
              </p>
              <p style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '0.85rem' }}>
                Go to the Rule Management Panel and import rules to continue.
              </p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <p>Loading reasoning explanations...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div style={{
            padding: '1rem',
            backgroundColor: '#fee',
            border: '1px solid #f88',
            borderRadius: '4px',
            marginBottom: '1rem'
          }}>
            <AlertCircle size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
            {error}
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === 'overview' && rulesLoaded && (
          <div className="info-section">
            <h3>Reasoning Layer Overview</h3>
            <p style={{ color: '#666', marginBottom: '1rem' }}>
              The Reasoning Layer provides explainability by answering three core questions:
            </p>
            
            <div style={{ 
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{
                padding: '1rem',
                backgroundColor: '#f0f7ff',
                borderLeft: '4px solid #0066cc',
                borderRadius: '4px'
              }}>
                <h4 style={{ marginTop: 0 }}>Why Rules Exist?</h4>
                <p style={{ fontSize: '0.9rem', color: '#333' }}>
                  Understand the regulatory intent and safety concerns behind each rule.
                </p>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#f0fff0',
                borderLeft: '4px solid #00aa00',
                borderRadius: '4px'
              }}>
                <h4 style={{ marginTop: 0 }}>Why Elements Failed?</h4>
                <p style={{ fontSize: '0.9rem', color: '#333' }}>
                  Analyze failures and understand why specific elements don't meet requirements.
                </p>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#fff7f0',
                borderLeft: '4px solid #dd7700',
                borderRadius: '4px'
              }}>
                <h4 style={{ marginTop: 0 }}>How to Fix It?</h4>
                <p style={{ fontSize: '0.9rem', color: '#333' }}>
                  Get step-by-step solutions and implementation guidance.
                </p>
              </div>
            </div>

            <h4>Regulatory Standards Coverage</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
              {Object.entries(standards).map(([standard, count]) => (
                <div key={standard} style={{ fontSize: '0.9rem', padding: '0.5rem' }}>
                  <strong>{standard}:</strong> {count} rules
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rules Explanations Tab - Now shows ALL rules from catalogue */}
        {activeTab === 'rules' && rulesLoaded && (
          <div>
            {allRulesFromCatalogue.length === 0 ? (
              <p style={{ color: '#999' }}>No rules available in catalogue</p>
            ) : (
              <div>
                <div style={{ 
                  marginBottom: '1rem', 
                  padding: '1rem', 
                  backgroundColor: '#f0f7ff', 
                  borderRadius: '4px',
                  borderLeft: '4px solid #0066cc'
                }}>
                  <p style={{ margin: 0, fontSize: '0.9rem' }}>
                    <strong>Rules Catalogue:</strong> {allRulesFromCatalogue.length} total rules
                    ({allRulesFromCatalogue.filter(r => r.source === 'regulatory').length} regulatory, 
                    {allRulesFromCatalogue.filter(r => r.source === 'custom').length} custom)
                  </p>
                </div>
                
                {allRulesFromCatalogue.map((rule, idx) => {
                  const itemId = `rule-${idx}`;
                  const isExpanded = expandedItems[itemId];
                  const isRegulatory = rule.source === 'regulatory';
                  
                  return (
                    <div
                      key={itemId}
                      style={{
                        marginBottom: '1rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        borderLeft: `4px solid ${isRegulatory ? '#0066cc' : '#5cb85c'}`
                      }}
                    >
                      <button
                        onClick={() => toggleExpanded(itemId)}
                        style={{
                          width: '100%',
                          padding: '1rem',
                          backgroundColor: isRegulatory ? '#f0f7ff' : '#f0fff0',
                          border: 'none',
                          textAlign: 'left',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <span style={{ fontWeight: 'bold' }}>
                            {rule.name}
                          </span>
                          <span style={{ 
                            fontSize: '0.75rem', 
                            marginLeft: '1rem', 
                            padding: '0.25rem 0.5rem',
                            backgroundColor: isRegulatory ? '#0066cc' : '#5cb85c',
                            color: 'white',
                            borderRadius: '3px'
                          }}>
                            {rule.source}
                          </span>
                          {rule.jurisdiction && (
                            <span style={{ 
                              fontSize: '0.85rem', 
                              color: '#666', 
                              marginLeft: '0.5rem' 
                            }}>
                              ({rule.jurisdiction})
                            </span>
                          )}
                        </div>
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </button>

                      {isExpanded && (
                        <div style={{ padding: '1rem', borderTop: '1px solid #eee' }}>
                          <div style={{ marginBottom: '1rem' }}>
                            <h5 style={{ marginTop: 0 }}>Description</h5>
                            <p style={{ fontSize: '0.9rem', color: '#333', margin: 0 }}>
                              {rule.description}
                            </p>
                          </div>

                          {rule.target_ifc_class && (
                            <div style={{ marginBottom: '1rem' }}>
                              <h5 style={{ marginTop: 0 }}>Applies To</h5>
                              <p style={{ fontSize: '0.9rem', color: '#333', margin: 0 }}>
                                {rule.target_ifc_class}
                              </p>
                            </div>
                          )}

                          <div style={{ marginBottom: '1rem' }}>
                            <h5 style={{ marginTop: 0 }}>Severity</h5>
                            <p style={{ 
                              fontSize: '0.9rem', 
                              margin: 0,
                              display: 'inline-block',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: rule.severity === 'ERROR' ? '#fee' : '#ffeaa7',
                              borderRadius: '3px',
                              color: rule.severity === 'ERROR' ? '#d9534f' : '#f0ad4e'
                            }}>
                              {rule.severity || 'WARNING'}
                            </p>
                          </div>

                          {rule.regulation && (
                            <div style={{ marginBottom: '1rem' }}>
                              <h5 style={{ marginTop: 0 }}>Regulatory Reference</h5>
                              <p style={{ fontSize: '0.9rem', color: '#666', margin: 0 }}>
                                <strong>{rule.regulation}</strong>
                                {rule.section && ` - Section ${rule.section}`}
                                {rule.jurisdiction && ` (${rule.jurisdiction})`}
                              </p>
                            </div>
                          )}

                          {rule.short_explanation && (
                            <div style={{ marginBottom: '1rem' }}>
                              <h5 style={{ marginTop: 0 }}>Explanation</h5>
                              <p style={{ fontSize: '0.9rem', color: '#333', margin: 0 }}>
                                {rule.short_explanation}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Failures & Solutions Tab */}
        {activeTab === 'failures' && rulesLoaded && (
          <div>
            {complianceStats?.failed === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <CheckCircle size={32} style={{ color: '#5cb85c', marginBottom: '1rem' }} />
                <p style={{ color: '#666', marginBottom: '1rem' }}>
                  <strong>No element failures found!</strong>
                </p>
                <p style={{ color: '#999', fontSize: '0.95rem' }}>
                  All elements comply with regulatory standards.
                </p>
              </div>
            ) : (
              <div>
                <div style={{
                  marginBottom: '1rem',
                  padding: '1rem',
                  backgroundColor: '#fee',
                  borderRadius: '4px',
                  borderLeft: '4px solid #d9534f'
                }}>
                  <p style={{ margin: 0, fontSize: '0.9rem' }}>
                    <strong>Compliance Summary:</strong> {complianceStats?.failed || 0} attribute(s) failed compliance checks
                  </p>
                </div>
                {failureExplanations.map((explanation, idx) => {
                  const itemId = `failure-${idx}`;
                  const isExpanded = expandedItems[itemId];
                  const elementExp = explanation.element_explanations?.[0];
                  
                  if (!elementExp) return null;

                  return (
                    <div
                      key={itemId}
                      style={{
                        marginBottom: '1rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        borderLeft: '4px solid #d9534f'
                      }}
                    >
                      <button
                        onClick={() => toggleExpanded(itemId)}
                        style={{
                          width: '100%',
                          padding: '1rem',
                          backgroundColor: '#fee',
                          border: 'none',
                          textAlign: 'left',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <span>
                          <strong>{elementExp.element_type}</strong> {elementExp.element_name}
                          <span style={{ fontSize: '0.85rem', color: '#d9534f', marginLeft: '1rem', fontWeight: 'bold' }}>
                            {elementExp.total_failures} failed attribute(s)
                          </span>
                        </span>
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </button>

                      {isExpanded && (
                        <div style={{ padding: '1rem', borderTop: '1px solid #ddd' }}>
                          {elementExp.analyses?.map((analysis, aIdx) => (
                            <div key={aIdx} style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #eee' }}>
                              <h5 style={{ marginTop: 0, color: '#d9534f' }}>{analysis.rule_name}</h5>
                              <div style={{ backgroundColor: '#fff9f9', padding: '0.75rem', borderRadius: '3px', marginBottom: '0.5rem' }}>
                                <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                  <strong>Status:</strong> Failed ✗
                                </p>
                                <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                  <strong>Reason:</strong> {analysis.failure_reason}
                                </p>
                                {analysis.actual_value !== undefined && (
                                  <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                    <strong>Actual Value:</strong> {String(analysis.actual_value)} {analysis.unit || ''}
                                  </p>
                                )}
                                {analysis.required_value !== undefined && (
                                  <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                    <strong>Required Value:</strong> {String(analysis.required_value)} {analysis.unit || ''}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Passes & Benefits Tab */}
        {activeTab === 'passes' && rulesLoaded && (
          <div>
            {complianceStats?.passed === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem' }}>
                <p style={{ color: '#999' }}>No passing attributes to display</p>
              </div>
            ) : (
              <div>
                <div style={{
                  marginBottom: '1rem',
                  padding: '1rem',
                  backgroundColor: '#d4edda',
                  borderRadius: '4px',
                  borderLeft: '4px solid #28a745'
                }}>
                  <p style={{ margin: 0, fontSize: '0.9rem' }}>
                    <strong>Compliance Summary:</strong> {complianceStats?.passed || 0} attribute(s) passed compliance checks
                  </p>
                </div>
                {passExplanations.map((explanation, idx) => {
                  const itemId = `pass-${idx}`;
                  const isExpanded = expandedItems[itemId];
                  const elementExp = explanation.element_explanations?.[0];

                  if (!elementExp) return null;

                  return (
                    <div
                      key={itemId}
                      style={{
                        marginBottom: '1rem',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        overflow: 'hidden',
                        borderLeft: '4px solid #28a745'
                      }}
                    >
                      <button
                        onClick={() => toggleExpanded(itemId)}
                        style={{
                          width: '100%',
                          padding: '1rem',
                          backgroundColor: '#d4edda',
                          border: 'none',
                          textAlign: 'left',
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center'
                        }}
                      >
                        <span>
                          <CheckCircle size={16} style={{ display: 'inline', marginRight: '0.5rem', color: '#28a745' }} />
                          <strong>{elementExp.element_type}</strong> {elementExp.element_name}
                          <span style={{ fontSize: '0.85rem', color: '#28a745', marginLeft: '1rem', fontWeight: 'bold' }}>
                            {elementExp.total_passes || 1} passed attribute(s)
                          </span>
                        </span>
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                      </button>

                      {isExpanded && (
                        <div style={{ padding: '1rem', borderTop: '1px solid #ddd' }}>
                          {elementExp.analyses?.map((analysis, aIdx) => (
                            <div key={aIdx} style={{ marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #eee' }}>
                              <h5 style={{ marginTop: 0, color: '#28a745' }}>{analysis.rule_name}</h5>
                              <div style={{ backgroundColor: '#f0fdf4', padding: '0.75rem', borderRadius: '3px', marginBottom: '0.5rem' }}>
                                <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                  <strong>Status:</strong> Passed ✓
                                </p>
                                <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                  <strong>Reason:</strong> {analysis.pass_reason || 'Element meets regulatory requirements'}
                                </p>
                                {analysis.actual_value !== undefined && (
                                  <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                    <strong>Actual Value:</strong> {String(analysis.actual_value)} {analysis.unit || ''}
                                  </p>
                                )}
                                {analysis.required_value !== undefined && (
                                  <p style={{ fontSize: '0.9rem', margin: '0.25rem 0' }}>
                                    <strong>Required Value:</strong> {String(analysis.required_value)} {analysis.unit || ''}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ReasoningView;
