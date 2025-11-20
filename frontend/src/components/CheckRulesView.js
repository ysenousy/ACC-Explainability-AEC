import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, AlertTriangle, Info, Play, Download, Eye, Filter } from 'lucide-react';

function CheckRulesView({ graph }) {
  const [checkMode, setCheckMode] = useState(null); // 'regulatory' or 'generated'
  const [availableRules, setAvailableRules] = useState([]);
  const [selectedRules, setSelectedRules] = useState(new Set());
  const [isChecking, setIsChecking] = useState(false);
  const [checkResults, setCheckResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('all'); // 'all', 'error', 'warning', 'info'
  const [resultFilter, setResultFilter] = useState('all'); // 'all', 'pass', 'fail'

  // Load available rules based on mode
  useEffect(() => {
    if (!checkMode) return;

    const loadRules = async () => {
      setLoading(true);
      setError(null);
      try {
        if (checkMode === 'regulatory') {
          // Fetch confirmed regulatory rules
          const response = await fetch('/api/rules/catalogue');
          const data = await response.json();
          if (data.success) {
            setAvailableRules(data.rules || []);
          } else {
            setError(data.error || 'Failed to load regulatory rules');
          }
        } else if (checkMode === 'generated') {
          // Analyze and extract generated rules
          const response = await fetch('/api/rules/analyze-strategies', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ graph })
          });
          const data = await response.json();
          if (data.success) {
            // Generate rules from the strategies
            const genResponse = await fetch('/api/rules/generate', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ graph, strategies: ['pset', 'statistical', 'metadata'] })
            });
            const genData = await genResponse.json();
            if (genData.success) {
              setAvailableRules(genData.rules || []);
            } else {
              setError(genData.error || 'Failed to generate rules');
            }
          } else {
            setError(data.error || 'Failed to analyze strategies');
          }
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadRules();
  }, [checkMode, graph]);

  const handleToggleRule = (ruleId) => {
    setSelectedRules(prev => {
      const newSet = new Set(prev);
      if (newSet.has(ruleId)) {
        newSet.delete(ruleId);
      } else {
        newSet.add(ruleId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedRules.size === availableRules.length) {
      setSelectedRules(new Set());
    } else {
      setSelectedRules(new Set(availableRules.map(r => r.id)));
    }
  };

  const handleCheckRules = async () => {
    if (selectedRules.size === 0) {
      setError('Please select at least one rule to check');
      return;
    }

    setIsChecking(true);
    setError(null);
    try {
      const rulesToCheck = availableRules.filter(r => selectedRules.has(r.id));
      
      const response = await fetch('/api/rules/check-against-ifc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph,
          rules: rulesToCheck,
          mode: checkMode
        })
      });

      const data = await response.json();
      if (data.success) {
        setCheckResults(data.results);
      } else {
        setError(data.error || 'Failed to check rules');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsChecking(false);
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'error': return <AlertCircle size={16} />;
      case 'warning': return <AlertTriangle size={16} />;
      default: return <Info size={16} />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'error': return '#ef4444';
      case 'warning': return '#f59e0b';
      default: return '#3b82f6';
    }
  };

  const getResultColor = (result) => {
    return result === 'PASS' ? '#10b981' : '#ef4444';
  };

  const getResultIcon = (result) => {
    return result === 'PASS' ? '✓' : '✗';
  };

  // Filter results
  const filteredResults = checkResults?.details?.filter(item => {
    if (severityFilter !== 'all' && item.rule.severity?.toLowerCase() !== severityFilter) {
      return false;
    }
    if (resultFilter !== 'all' && item.result !== resultFilter.toUpperCase()) {
      return false;
    }
    return true;
  }) || [];

  const passCount = checkResults?.details?.filter(d => d.result === 'PASS').length || 0;
  const failCount = checkResults?.details?.filter(d => d.result === 'FAIL').length || 0;

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  // Step 1: Select Check Mode
  if (!checkMode) {
    return (
      <div className="layer-view">
        <div className="layer-header">
          <CheckCircle size={24} />
          <h2>Check Rules</h2>
        </div>

        <div className="layer-content">
          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1rem', fontWeight: '600' }}>
              Select Check Mode
            </h3>
            <p style={{ color: '#666', marginBottom: '1.5rem', fontSize: '0.95rem' }}>
              Choose how you want to validate your IFC model against rules.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
            {/* Regulatory Rules Option */}
            <div
              onClick={() => setCheckMode('regulatory')}
              style={{
                padding: '1.5rem',
                border: '2px solid #3b82f6',
                borderRadius: '0.75rem',
                backgroundColor: '#eff6ff',
                cursor: 'pointer',
                transition: 'all 0.3s',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ fontSize: '1.5rem' }}>📋</div>
                <h3 style={{ margin: 0, color: '#3b82f6', fontSize: '1.1rem', fontWeight: '600' }}>
                  Regulatory Rules
                </h3>
              </div>
              <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
                Check your IFC model against <strong>external compliance standards</strong> (ADA, Building Codes, Fire Code, etc.)
              </p>
              <div style={{
                marginTop: '1rem',
                padding: '0.75rem',
                backgroundColor: '#dbeafe',
                borderRadius: '0.375rem',
                fontSize: '0.8rem',
                color: '#1e40af'
              }}>
                ✓ Verify code compliance
                <br />
                ✓ Audit against regulations
                <br />
                ✓ Generate compliance reports
              </div>
            </div>

            {/* Generated Rules Option */}
            <div
              onClick={() => setCheckMode('generated')}
              style={{
                padding: '1.5rem',
                border: '2px solid #10b981',
                borderRadius: '0.75rem',
                backgroundColor: '#f0fdf4',
                cursor: 'pointer',
                transition: 'all 0.3s',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.boxShadow = '0 10px 25px rgba(0, 0, 0, 0.15)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ fontSize: '1.5rem' }}>⚡</div>
                <h3 style={{ margin: 0, color: '#10b981', fontSize: '1.1rem', fontWeight: '600' }}>
                  Generated Rules
                </h3>
              </div>
              <p style={{ margin: '0.5rem 0', fontSize: '0.875rem', color: '#666', lineHeight: '1.5' }}>
                Check your IFC model against <strong>building-specific baseline rules</strong> extracted from the data.
              </p>
              <div style={{
                marginTop: '1rem',
                padding: '0.75rem',
                backgroundColor: '#dcfce7',
                borderRadius: '0.375rem',
                fontSize: '0.8rem',
                color: '#166534'
              }}>
                ✓ Find design inconsistencies
                <br />
                ✓ Detect anomalies
                <br />
                ✓ Ensure data completeness
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Select Rules and Check
  return (
    <div className="layer-view">
      <div className="layer-header">
        <CheckCircle size={24} />
        <h2>Check Rules</h2>
      </div>

      <div className="layer-content">
        {/* Back Button and Mode Info */}
        <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            onClick={() => {
              setCheckMode(null);
              setSelectedRules(new Set());
              setCheckResults(null);
            }}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '500'
            }}
          >
            ← Back
          </button>
          <div style={{ fontSize: '0.95rem', fontWeight: '600', color: '#1f2937' }}>
            {checkMode === 'regulatory' ? '📋 Regulatory Rules' : '⚡ Generated Rules'}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div style={{
            padding: '1rem',
            marginBottom: '1rem',
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            borderRadius: '0.375rem',
            border: '1px solid #fca5a5',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
          }}>
            <AlertCircle size={18} />
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
            <div style={{ animation: 'spin 1s linear infinite', fontSize: '2rem', marginBottom: '1rem' }}>⟳</div>
            <p>Loading rules...</p>
          </div>
        )}

        {/* Rules Selection */}
        {!loading && availableRules.length > 0 && !checkResults && (
          <>
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '1rem'
              }}>
                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>
                  Available Rules ({availableRules.length})
                </h3>
                <button
                  onClick={handleSelectAll}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#e0e7ff',
                    color: '#4f46e5',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    fontWeight: '500'
                  }}
                >
                  {selectedRules.size === availableRules.length ? 'Deselect All' : 'Select All'}
                </button>
              </div>

              <div style={{
                maxHeight: '400px',
                overflowY: 'auto',
                border: '1px solid #e5e7eb',
                borderRadius: '0.375rem',
                backgroundColor: '#f9fafb'
              }}>
                {availableRules.map((rule, idx) => (
                  <div
                    key={rule.id}
                    style={{
                      padding: '1rem',
                      borderBottom: idx < availableRules.length - 1 ? '1px solid #e5e7eb' : 'none',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '1rem',
                      backgroundColor: idx % 2 === 0 ? '#f9fafb' : '#ffffff',
                      cursor: 'pointer',
                      transition: 'background-color 0.2s'
                    }}
                    onClick={() => handleToggleRule(rule.id)}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = idx % 2 === 0 ? '#f9fafb' : '#ffffff'}
                  >
                    <input
                      type="checkbox"
                      checked={selectedRules.has(rule.id)}
                      onChange={() => {}}
                      style={{ marginTop: '0.25rem', cursor: 'pointer' }}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '600', fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                        {rule.name || rule.id}
                      </div>
                      {rule.description && (
                        <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.5rem' }}>
                          {rule.description}
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#999' }}>
                        {rule.target_type && <span>Target: {rule.target_type}</span>}
                        {rule.severity && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: getSeverityColor(rule.severity) }}>
                            {getSeverityIcon(rule.severity)}
                            {rule.severity.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Check Button */}
            <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
              <button
                onClick={handleCheckRules}
                disabled={isChecking || selectedRules.size === 0}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.5rem',
                  backgroundColor: selectedRules.size === 0 ? '#d1d5db' : '#06b6d4',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: selectedRules.size === 0 ? 'not-allowed' : 'pointer',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  transition: 'background-color 0.2s',
                  opacity: isChecking ? 0.7 : 1
                }}
                onMouseEnter={(e) => selectedRules.size > 0 && !isChecking && (e.target.style.backgroundColor = '#0891b2')}
                onMouseLeave={(e) => selectedRules.size > 0 && !isChecking && (e.target.style.backgroundColor = '#06b6d4')}
                title={selectedRules.size === 0 ? 'Select at least one rule' : 'Check rules against IFC'}
              >
                {isChecking ? (
                  <>
                    <div style={{ animation: 'spin 1s linear infinite' }}>⟳</div>
                    Checking...
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    Check {selectedRules.size} {selectedRules.size === 1 ? 'Rule' : 'Rules'}
                  </>
                )}
              </button>
            </div>
          </>
        )}

        {/* No Rules Message */}
        {!loading && availableRules.length === 0 && !checkResults && (
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            backgroundColor: '#fef3c7',
            color: '#92400e',
            borderRadius: '0.375rem',
            border: '1px solid #fcd34d'
          }}>
            <AlertCircle size={24} style={{ marginBottom: '0.5rem' }} />
            <p>No {checkMode === 'regulatory' ? 'regulatory' : 'generated'} rules available.</p>
            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              {checkMode === 'regulatory' 
                ? 'Please confirm rules from the catalogue first.'
                : 'Generate rules from the IFC first.'}
            </p>
          </div>
        )}

        {/* Results Display */}
        {checkResults && (
          <>
            {/* Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '1rem',
              marginBottom: '2rem'
            }}>
              <div style={{
                padding: '1.5rem',
                backgroundColor: '#dcfce7',
                border: '2px solid #86efac',
                borderRadius: '0.5rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#10b981' }}>
                  {passCount}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#166534', fontWeight: '500' }}>
                  Passed
                </div>
              </div>
              <div style={{
                padding: '1.5rem',
                backgroundColor: '#fee2e2',
                border: '2px solid #fca5a5',
                borderRadius: '0.5rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ef4444' }}>
                  {failCount}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#991b1b', fontWeight: '500' }}>
                  Failed
                </div>
              </div>
              <div style={{
                padding: '1.5rem',
                backgroundColor: '#dbeafe',
                border: '2px solid #93c5fd',
                borderRadius: '0.5rem',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
                  {checkResults.details?.length || 0}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#1e40af', fontWeight: '500' }}>
                  Total
                </div>
              </div>
            </div>

            {/* Filters */}
            <div style={{
              display: 'flex',
              gap: '1rem',
              marginBottom: '1.5rem',
              flexWrap: 'wrap'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Filter size={16} />
                <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>Filter:</span>
              </div>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                style={{
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="all">All Severities</option>
                <option value="error">Error</option>
                <option value="warning">Warning</option>
                <option value="info">Info</option>
              </select>
              <select
                value={resultFilter}
                onChange={(e) => setResultFilter(e.target.value)}
                style={{
                  padding: '0.5rem 0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  fontSize: '0.875rem'
                }}
              >
                <option value="all">All Results</option>
                <option value="pass">Passed</option>
                <option value="fail">Failed</option>
              </select>
            </div>

            {/* Results List */}
            <div style={{
              maxHeight: '600px',
              overflowY: 'auto',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              backgroundColor: '#f9fafb',
              marginBottom: '1.5rem'
            }}>
              {filteredResults.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#999' }}>
                  No results match the filters
                </div>
              ) : (
                filteredResults.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '1rem',
                      borderBottom: idx < filteredResults.length - 1 ? '1px solid #e5e7eb' : 'none',
                      backgroundColor: idx % 2 === 0 ? '#f9fafb' : '#ffffff'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.5rem' }}>
                      <div style={{
                        fontSize: '1.5rem',
                        fontWeight: 'bold',
                        color: getResultColor(item.result),
                        minWidth: '2rem',
                        textAlign: 'center'
                      }}>
                        {getResultIcon(item.result)}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.75rem',
                          marginBottom: '0.25rem'
                        }}>
                          <strong style={{ fontSize: '0.95rem' }}>
                            {item.rule.name || item.rule.id}
                          </strong>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.25rem 0.5rem',
                            backgroundColor: getResultColor(item.result),
                            color: 'white',
                            borderRadius: '0.25rem',
                            fontSize: '0.7rem',
                            fontWeight: 'bold'
                          }}>
                            {item.result}
                          </span>
                          {item.rule.severity && (
                            <span style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                              padding: '0.25rem 0.5rem',
                              backgroundColor: getSeverityColor(item.rule.severity),
                              color: 'white',
                              borderRadius: '0.25rem',
                              fontSize: '0.7rem',
                              fontWeight: 'bold'
                            }}>
                              {getSeverityIcon(item.rule.severity)}
                              {item.rule.severity.toUpperCase()}
                            </span>
                          )}
                        </div>
                        {item.message && (
                          <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem' }}>
                            {item.message}
                          </div>
                        )}
                        {item.details && (
                          <div style={{ fontSize: '0.8rem', color: '#999', padding: '0.5rem', backgroundColor: '#f0f0f0', borderRadius: '0.25rem', marginTop: '0.5rem' }}>
                            {typeof item.details === 'object' ? JSON.stringify(item.details) : item.details}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                onClick={() => setCheckResults(null)}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#f3f4f6',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.9rem'
                }}
              >
                Back to Rules
              </button>
              <button
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#8b5cf6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.9rem'
                }}
              >
                <Download size={18} />
                Export Results
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default CheckRulesView;
