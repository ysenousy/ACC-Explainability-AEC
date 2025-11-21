import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, AlertTriangle, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';

function RuleCheckView({ graph }) {
  const [complianceResults, setComplianceResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('all'); // 'all', 'error', 'warning'
  const [expandedRules, setExpandedRules] = useState({});
  const [rulesLoaded, setRulesLoaded] = useState(null); // null = checking, false = not loaded, true = loaded
  const [checkingRules, setCheckingRules] = useState(true); // Start as true (checking)

  // Check if rules are loaded on component mount
  useEffect(() => {
    checkRulesStatus();
    
    // Cleanup on unmount - clear cached results so they refresh next time
    return () => {
      setComplianceResults(null);
    };
  }, []);

  // Check compliance only after rules check completes and rules are loaded
  useEffect(() => {
    console.log('Compliance check effect:', { graph: !!graph, rulesLoaded, checkingRules });
    if (!graph) {
      console.log('No graph, returning');
      return;
    }
    if (rulesLoaded === null) {
      console.log('Still checking rules, returning');
      return; // Still checking rules
    }
    if (rulesLoaded === false) {
      console.log('Rules not loaded, returning');
      return; // Rules not loaded
    }
    if (rulesLoaded === true) {
      console.log('Rules loaded, calling checkCompliance');
      checkCompliance();
    }
  }, [graph, rulesLoaded]);

  const checkRulesStatus = async () => {
    setCheckingRules(true);
    try {
      const response = await fetch('/api/rules/check-status');
      const data = await response.json();
      console.log('Rules status check result:', data);
      setRulesLoaded(data.rules_loaded || false);
      if (!data.rules_loaded) {
        setComplianceResults(null); // Clear any existing results
        setError('Regulatory rules not imported. Please import regulation rules from the Rules menu first.');
      } else {
        setError(null);
        // Rules are now loaded, proceed with compliance check
        setLoading(true);
        try {
          const response = await fetch('/api/rules/check-compliance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ graph })
          });

          const data = await response.json();
          if (data.success) {
            setComplianceResults(data.compliance);
          } else {
            setError(data.error || 'Failed to check compliance');
          }
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      }
    } catch (err) {
      console.error('Failed to check rules status:', err);
      setRulesLoaded(false);
      setComplianceResults(null); // Clear any existing results
      setError('Failed to verify regulatory rules availability.');
    } finally {
      setCheckingRules(false);
    }
  };

  const checkCompliance = async () => {
    console.log('checkCompliance called, rulesLoaded:', rulesLoaded);
    
    // Always re-check rules status before checking compliance
    // (in case rules were generated/imported after initial check)
    await checkRulesStatus();
  };

  const performComplianceCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/rules/check-compliance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph })
      });

      const data = await response.json();
      if (data.success) {
        setComplianceResults(data.compliance);
      } else {
        setError(data.error || 'Failed to check compliance');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pass':
        return '#10b981';
      case 'fail':
        return '#ef4444';
      default:
        return '#6b7280';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'error':
        return '#ef4444';
      case 'warning':
        return '#f59e0b';
      default:
        return '#3b82f6';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pass':
        return <CheckCircle size={16} style={{ color: '#10b981' }} />;
      case 'fail':
        return <AlertCircle size={16} style={{ color: '#ef4444' }} />;
      default:
        return <AlertCircle size={16} style={{ color: '#6b7280' }} />;
    }
  };

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  // Filter rules based on severity
  const filterRules = (rules) => {
    if (!rules) return [];
    return rules.filter(rule => {
      if (severityFilter !== 'all' && rule.severity?.toLowerCase() !== severityFilter.toLowerCase()) {
        return false;
      }
      return true;
    });
  };

  const filteredRules = filterRules(complianceResults?.rules || []);

  const toggleRuleExpanded = (ruleId) => {
    setExpandedRules(prev => ({
      ...prev,
      [ruleId]: !prev[ruleId]
    }));
  };

  return (
    <div className="layer-view">
      <div className="layer-header">
        <CheckCircle size={24} />
        <h2>Rules Compliance Check</h2>
        <button
          onClick={checkCompliance}
          disabled={loading || rulesLoaded !== true}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: loading || rulesLoaded !== true ? '#d1d5db' : '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: loading || rulesLoaded !== true ? 'not-allowed' : 'pointer',
            fontWeight: '600',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            marginLeft: 'auto'
          }}
          title={rulesLoaded !== true ? 'Rules must be imported first' : 'Check compliance with rules'}
        >
          <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          {loading ? 'Checking...' : 'Check Compliance'}
        </button>
      </div>

      <div className="layer-content">
        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
            Checking compliance...
          </div>
        )}

        {checkingRules || rulesLoaded === false || rulesLoaded === null ? (
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            backgroundColor: '#fef3c7',
            borderRadius: '0.5rem',
            border: '2px solid #f59e0b',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '1rem'
          }}>
            <AlertTriangle size={48} style={{ color: '#f59e0b' }} />
            <div>
              <h3 style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '1.1rem' }}>
                {checkingRules ? '⏳ Checking Regulatory Rules...' : '⚠️ Regulatory Rules Not Imported'}
              </h3>
              <p style={{ margin: '0.5rem 0', color: '#78350f', fontSize: '0.95rem' }}>
                {checkingRules 
                  ? 'Please wait while we verify regulatory rules...' 
                  : 'Please import regulatory rules first to check compliance.'}
              </p>
              {!checkingRules && (
                <p style={{ margin: '1rem 0 0 0', color: '#78350f', fontSize: '0.85rem' }}>
                  1. Go to <strong>Rules</strong> menu → <strong>Regulatory Rules</strong><br/>
                  2. Click <strong>Import Rules</strong> to load the regulation rules<br/>
                  3. Return to this view to check compliance
                </p>
              )}
            </div>
            <button
              onClick={checkRulesStatus}
              disabled={checkingRules}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: checkingRules ? '#d1d5db' : '#f59e0b',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: checkingRules ? 'not-allowed' : 'pointer',
                fontWeight: '600',
                marginTop: '1rem'
              }}
            >
              {checkingRules ? 'Checking...' : 'Check Again'}
            </button>
          </div>
        ) : (
          <>
            {error && (
              <div style={{
                padding: '1rem',
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                borderRadius: '0.375rem',
                marginBottom: '1rem'
              }}>
                Error: {error}
              </div>
            )}

            {!loading && complianceResults && (
          <>
            {/* Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{
                padding: '1rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: '600', marginBottom: '0.5rem' }}>
                  TOTAL RULES
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1f2937' }}>
                  {complianceResults.summary.total_rules}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: '600', marginBottom: '0.5rem' }}>
                  COMPONENTS CHECKED
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1f2937' }}>
                  {complianceResults.summary.components_checked}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: '600', marginBottom: '0.5rem' }}>
                  TOTAL EVALUATIONS
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1f2937' }}>
                  {complianceResults.summary.total_evaluations}
                </div>
              </div>
            </div>

            {/* Applied Rules Summary */}
            {complianceResults.rules && complianceResults.rules.length > 0 && (
              <div style={{
                padding: '1rem',
                marginBottom: '1.5rem',
                backgroundColor: '#f0f9ff',
                border: '1px solid #bfdbfe',
                borderRadius: '0.5rem'
              }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#0c4a6e', marginBottom: '0.75rem' }}>
                  ✓ Applied Rules:
                </div>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                  gap: '0.75rem'
                }}>
                  {complianceResults.rules.map((rule) => (
                    <div key={rule.rule_id} style={{
                      padding: '0.75rem',
                      backgroundColor: '#fff',
                      border: '1px solid #bfdbfe',
                      borderRadius: '0.375rem',
                      fontSize: '0.8rem'
                    }}>
                      <div style={{ fontWeight: '600', color: '#1f2937', marginBottom: '0.25rem' }}>
                        {rule.rule_name}
                      </div>
                      <div style={{ color: '#6b7280', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
                        {rule.rule_type ? rule.rule_type.charAt(0).toUpperCase() + rule.rule_type.slice(1) : 'Unknown'} • {rule.components_evaluated} components
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          backgroundColor: '#10b981',
                          color: 'white',
                          borderRadius: '0.25rem',
                          fontSize: '0.7rem',
                          fontWeight: '600'
                        }}>
                          ✓ {rule.passed}
                        </span>
                        <span style={{
                          padding: '0.25rem 0.5rem',
                          backgroundColor: '#ef4444',
                          color: 'white',
                          borderRadius: '0.25rem',
                          fontSize: '0.7rem',
                          fontWeight: '600'
                        }}>
                          ✗ {rule.failed}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Severity Filter */}
            <div style={{
              display: 'flex',
              gap: '0.5rem',
              marginBottom: '1.5rem',
              alignItems: 'center'
            }}>
              <span style={{ fontSize: '0.875rem', fontWeight: '600' }}>Severity:</span>
              {['all', 'error', 'warning'].map(sev => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: severityFilter === sev ? getSeverityColor(sev) : '#e5e7eb',
                    color: severityFilter === sev ? 'white' : '#1f2937',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '600'
                  }}
                >
                  {sev.charAt(0).toUpperCase() + sev.slice(1)}
                </button>
              ))}
            </div>

            {/* Rules List */}
            <div style={{
              maxHeight: '700px',
              overflowY: 'auto',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              backgroundColor: '#fff'
            }}>
              {filteredRules.length === 0 ? (
                <div style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: '#6b7280'
                }}>
                  No rules match the selected filters
                </div>
              ) : (
                filteredRules.map((rule) => (
                  <div
                    key={rule.rule_id}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      backgroundColor: '#fff'
                    }}
                  >
                    {/* Rule Header */}
                    <div
                      onClick={() => toggleRuleExpanded(rule.rule_id)}
                      style={{
                        padding: '1rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        backgroundColor: expandedRules[rule.rule_id] ? '#f9fafb' : '#fff',
                        transition: 'background-color 0.2s'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
                        {expandedRules[rule.rule_id] ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937', marginBottom: '0.25rem' }}>
                            {rule.rule_name}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                            {rule.rule_type ? rule.rule_type.charAt(0).toUpperCase() + rule.rule_type.slice(1) : 'Unknown'}
                          </div>
                        </div>
                      </div>

                      {/* Status Badges */}
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '0.25rem 0.75rem',
                            backgroundColor: '#ecfdf5',
                            color: '#10b981',
                            borderRadius: '0.25rem',
                            fontSize: '0.75rem',
                            fontWeight: '600'
                          }}
                        >
                          ✓ {rule.passed}
                        </span>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '0.25rem 0.75rem',
                            backgroundColor: '#fef2f2',
                            color: '#ef4444',
                            borderRadius: '0.25rem',
                            fontSize: '0.75rem',
                            fontWeight: '600'
                          }}
                        >
                          ✗ {rule.failed}
                        </span>
                        <div style={{
                          padding: '0.25rem 0.75rem',
                          backgroundColor: getSeverityColor(rule.severity) + '20',
                          color: getSeverityColor(rule.severity),
                          borderRadius: '0.25rem',
                          fontSize: '0.75rem',
                          fontWeight: '600'
                        }}>
                          {rule.severity.toUpperCase()}
                        </div>
                      </div>
                    </div>

                    {/* Rule Details */}
                    {expandedRules[rule.rule_id] && (
                      <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderTop: '1px solid #e5e7eb' }}>
                        {/* Rule Info */}
                        <div style={{ marginBottom: '1rem' }}>
                          <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                            <strong>Code Reference:</strong> {rule.code_reference}
                          </div>
                          <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                            <strong>Description:</strong> {rule.description}
                          </div>
                          <div style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                            <strong>Pass Rate:</strong>{' '}
                            <span style={{ color: rule.pass_rate >= 50 ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>
                              {rule.pass_rate.toFixed(1)}%
                            </span>
                            {' '}({rule.passed}/{rule.components_evaluated})
                          </div>

                          {/* Attributes Checked Summary */}
                          {rule.components && rule.components.length > 0 && (
                            <div style={{ fontSize: '0.85rem', marginTop: '0.75rem', padding: '0.75rem', backgroundColor: '#e0f2fe', borderRadius: '0.375rem', border: '1px solid #bfdbfe' }}>
                              <strong style={{ color: '#0c4a6e' }}>📊 Attributes Checked:</strong>
                              <div style={{ marginTop: '0.5rem', color: '#0c4a6e' }}>
                                {rule.components.length} component{rule.components.length !== 1 ? 's' : ''} evaluated
                                {rule.components.length > 0 && (
                                  <div style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                                    {rule.components.map((comp, idx) => {
                                      const attrs = comp.properties || {};
                                      const attrCount = Object.keys(attrs).length;
                                      return (
                                        <div key={idx} style={{ marginBottom: '0.25rem', paddingLeft: '0.5rem' }}>
                                          • <strong>{comp.name}</strong>: {attrCount} attribute{attrCount !== 1 ? 's' : ''} ({Object.keys(attrs).join(', ') || 'none'})
                                        </div>
                                      );
                                    }).slice(0, 5)}
                                    {rule.components.length > 5 && (
                                      <div style={{ marginTop: '0.25rem', paddingLeft: '0.5rem', color: '#6b7280', fontStyle: 'italic' }}>
                                        ... and {rule.components.length - 5} more components
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Components List */}
                        {rule.components && rule.components.length > 0 && (
                          <div style={{ marginTop: '1rem' }}>
                            <div style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '0.5rem', color: '#6b7280' }}>
                              EVALUATED COMPONENTS ({rule.components.length}):
                            </div>
                            <div style={{
                              maxHeight: '300px',
                              overflowY: 'auto',
                              border: '1px solid #e5e7eb',
                              borderRadius: '0.375rem',
                              backgroundColor: '#fff'
                            }}>
                              {rule.components.map((comp, idx) => (
                                <div
                                  key={idx}
                                  style={{
                                    padding: '0.75rem',
                                    borderBottom: idx < rule.components.length - 1 ? '1px solid #e5e7eb' : 'none',
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '0.5rem',
                                    backgroundColor: comp.status === 'pass' ? '#f0fdf4' : '#fef2f2'
                                  }}
                                >
                                  <div style={{ marginTop: '2px' }}>
                                    {getStatusIcon(comp.status)}
                                  </div>
                                  <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{
                                      fontSize: '0.8rem',
                                      fontWeight: '600',
                                      color: comp.status === 'pass' ? '#10b981' : '#ef4444',
                                      marginBottom: '0.25rem'
                                    }}>
                                      {comp.name}
                                    </div>
                                    <div style={{
                                      fontSize: '0.75rem',
                                      color: '#6b7280',
                                      wordBreak: 'break-word',
                                      marginBottom: '0.25rem'
                                    }}>
                                      {comp.message}
                                    </div>
                                    {comp.properties && Object.keys(comp.properties).length > 0 && (
                                      <div style={{
                                        fontSize: '0.7rem',
                                        color: '#9ca3af',
                                        marginTop: '0.25rem',
                                        fontStyle: 'italic',
                                        backgroundColor: '#f3f4f6',
                                        padding: '0.25rem 0.5rem',
                                        borderRadius: '0.25rem'
                                      }}>
                                        <strong>Attributes checked:</strong> {Object.entries(comp.properties)
                                          .map(([k, v]) => `${k}: ${v}`)
                                          .join(' | ')}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </>
        )}
          </>
        )}
      </div>
    </div>
  );
}

export default RuleCheckView;

const styles = `
  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
`;

// Add styles to document
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = styles;
  document.head.appendChild(styleSheet);
}
