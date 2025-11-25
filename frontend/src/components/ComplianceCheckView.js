import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Download, BarChart3 } from 'lucide-react';

function ComplianceCheckView({ graph }) {
  const [loading, setLoading] = useState(false);
  const [checkResults, setCheckResults] = useState(null);
  const [selectedRuleFilter, setSelectedRuleFilter] = useState(null);
  const [severityFilter, setSeverityFilter] = useState(null);
  const [statusFilter, setStatusFilter] = useState(null); // 'passed', 'failed', 'unable'
  const [dataStatusFilter, setDataStatusFilter] = useState(null); // 'complete', 'partial', 'missing'
  const [showSummary, setShowSummary] = useState(true);
  const [error, setError] = useState(null);

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'ERROR': return '#ef4444';
      case 'WARNING': return '#f59e0b';
      case 'INFO': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  const getDataStatusColor = (status) => {
    switch (status) {
      case 'complete': return '#10b981'; // green
      case 'partial': return '#f59e0b';  // amber
      case 'missing': return '#ef4444';  // red
      default: return '#6b7280';         // gray
    }
  };

  const getDataStatusLabel = (status) => {
    switch (status) {
      case 'complete': return '✓ Complete';
      case 'partial': return '◐ Partial';
      case 'missing': return '✗ Missing';
      default: return '? Unknown';
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'ERROR': return <AlertCircle size={16} />;
      case 'WARNING': return <AlertTriangle size={16} />;
      case 'INFO': return <CheckCircle2 size={16} />;
      default: return null;
    }
  };

  const runComplianceCheck = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/compliance/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph })
      });

      const data = await response.json();
      if (data.success) {
        setCheckResults(data);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = async () => {
    if (!checkResults) return;

    try {
      const response = await fetch('/api/compliance/export-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ check_results: checkResults })
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `compliance-report-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
      } else {
        setError('Failed to export report');
      }
    } catch (err) {
      setError(err.message);
    }
  };

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  // Filter results
  let filteredResults = checkResults?.results || [];
  if (selectedRuleFilter) {
    filteredResults = filteredResults.filter(r => r.rule_id === selectedRuleFilter);
  }
  if (severityFilter) {
    filteredResults = filteredResults.filter(r => r.severity === severityFilter);
  }
  if (statusFilter) {
    filteredResults = filteredResults.filter(r => {
      if (statusFilter === 'passed') return r.passed === true;
      if (statusFilter === 'failed') return r.passed === false;
      if (statusFilter === 'unable') return r.passed === null;
      return true;
    });
  }
  if (dataStatusFilter) {
    filteredResults = filteredResults.filter(r => r.data_status === dataStatusFilter);
  }

  return (
    <div style={{ padding: '1.5rem' }}>
      <div className="layer-view">
        <div className="layer-header">
          <BarChart3 size={24} />
          <h2>Compliance Checking</h2>
        </div>

        <div className="layer-content">
          {/* Control Panel */}
          <div style={{
            display: 'flex',
            gap: '1rem',
            marginBottom: '2rem',
            padding: '1rem',
            backgroundColor: '#f3f4f6',
            borderRadius: '0.5rem'
          }}>
            <button
              onClick={runComplianceCheck}
              disabled={loading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.625rem 1.25rem',
                backgroundColor: '#10b981',
                color: '#fff',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: '500',
                fontSize: '0.875rem',
                opacity: loading ? 0.5 : 1
              }}
              onMouseEnter={(e) => !loading && (e.target.style.backgroundColor = '#059669')}
              onMouseLeave={(e) => !loading && (e.target.style.backgroundColor = '#10b981')}
            >
              {loading ? 'Checking...' : 'Run Compliance Check'}
            </button>

            {checkResults && (
              <button
                onClick={exportReport}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.625rem 1.25rem',
                  backgroundColor: '#3b82f6',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '500',
                  fontSize: '0.875rem'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
                onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
              >
                <Download size={16} />
                Export Report
              </button>
            )}
          </div>

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

          {checkResults && (
            <>
              {/* Summary Statistics */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
              }}>
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#ecfdf5',
                  borderRadius: '0.5rem',
                  border: '1px solid #a7f3d0'
                }}>
                  <div style={{ fontSize: '0.875rem', color: '#059669', fontWeight: '500' }}>Passed</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#10b981' }}>
                    {checkResults.passed}
                  </div>
                </div>

                <div style={{
                  padding: '1rem',
                  backgroundColor: '#fef2f2',
                  borderRadius: '0.5rem',
                  border: '1px solid #fecaca'
                }}>
                  <div style={{ fontSize: '0.875rem', color: '#991b1b', fontWeight: '500' }}>Failed</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#ef4444' }}>
                    {checkResults.failed}
                  </div>
                </div>

                <div style={{
                  padding: '1rem',
                  backgroundColor: '#eff6ff',
                  borderRadius: '0.5rem',
                  border: '1px solid #bfdbfe'
                }}>
                  <div style={{ fontSize: '0.875rem', color: '#1e40af', fontWeight: '500' }}>Unable</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#3b82f6' }}>
                    {checkResults.unable}
                  </div>
                </div>

                <div style={{
                  padding: '1rem',
                  backgroundColor: '#f5f3ff',
                  borderRadius: '0.5rem',
                  border: '1px solid #ddd6fe'
                }}>
                  <div style={{ fontSize: '0.875rem', color: '#6b21a8', fontWeight: '500' }}>Pass Rate</div>
                  <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#8b5cf6' }}>
                    {checkResults.pass_rate.toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Filter Controls */}
              <div style={{
                display: 'flex',
                gap: '1rem',
                marginBottom: '1.5rem',
                flexWrap: 'wrap'
              }}>
                <select
                  value={statusFilter || ''}
                  onChange={(e) => setStatusFilter(e.target.value || null)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}
                >
                  <option value="">All Status</option>
                  <option value="passed">Passed ✓</option>
                  <option value="failed">Failed ✗</option>
                  <option value="unable">Unable ?</option>
                </select>

                <select
                  value={severityFilter || ''}
                  onChange={(e) => setSeverityFilter(e.target.value || null)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}
                >
                  <option value="">All Severity</option>
                  <option value="ERROR">Error</option>
                  <option value="WARNING">Warning</option>
                  <option value="INFO">Info</option>
                </select>

                <select
                  value={dataStatusFilter || ''}
                  onChange={(e) => setDataStatusFilter(e.target.value || null)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    cursor: 'pointer'
                  }}
                >
                  <option value="">All Data Status</option>
                  <option value="complete">✓ Complete Data</option>
                  <option value="partial">◐ Partial Data</option>
                  <option value="missing">✗ Missing Data</option>
                </select>
              </div>

              {/* Results Table */}
              <div style={{
                overflowX: 'auto',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                backgroundColor: '#fff'
              }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '0.875rem'
                }}>
                  <thead style={{ backgroundColor: '#f3f4f6', borderBottom: '2px solid #e5e7eb' }}>
                    <tr>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Status</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Rule</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Element</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Severity</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Data Status</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Data Source</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Explanation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredResults.map((result, idx) => (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid #e5e7eb',
                          backgroundColor: idx % 2 === 0 ? '#fff' : '#fafafa',
                          hover: { backgroundColor: '#f3f4f6' }
                        }}
                      >
                        <td style={{ padding: '0.75rem', textAlign: 'center' }}>
                          {result.passed === true ? (
                            <span style={{ color: '#10b981', fontWeight: 'bold' }}>✓</span>
                          ) : result.passed === false ? (
                            <span style={{ color: '#ef4444', fontWeight: 'bold' }}>✗</span>
                          ) : (
                            <span style={{ color: '#6b7280', fontWeight: 'bold' }}>?</span>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div style={{ fontWeight: '500' }}>{result.rule_name}</div>
                          <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{result.rule_id}</div>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <div style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#6b7280' }}>
                            {result.element_guid?.substring(0, 8)}...
                          </div>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.25rem 0.5rem',
                            backgroundColor: getSeverityColor(result.severity),
                            color: '#fff',
                            borderRadius: '0.25rem',
                            fontSize: '0.7rem',
                            fontWeight: 'bold'
                          }}>
                            {getSeverityIcon(result.severity)}
                            {result.severity}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.25rem 0.5rem',
                            backgroundColor: getDataStatusColor(result.data_status),
                            color: '#fff',
                            borderRadius: '0.25rem',
                            fontSize: '0.7rem',
                            fontWeight: 'bold',
                            title: result.data_status ? `Data Status: ${result.data_status}` : 'No data status'
                          }}>
                            {getDataStatusLabel(result.data_status)}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem', fontSize: '0.75rem', fontFamily: 'monospace', color: '#6b7280', maxWidth: '200px', title: result.data_source || 'N/A' }}>
                          {result.data_source || 'N/A'}
                        </td>
                        <td style={{ padding: '0.75rem', maxWidth: '300px' }}>
                          <div style={{ color: '#4b5563', lineHeight: '1.4' }}>
                            {result.explanation}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filteredResults.length === 0 && (
                  <div style={{
                    padding: '2rem',
                    textAlign: 'center',
                    color: '#6b7280'
                  }}>
                    No results match the selected filters
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ComplianceCheckView;
