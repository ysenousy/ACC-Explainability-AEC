import React, { useState, useEffect } from 'react';
import { FileText, CheckCircle, AlertCircle, AlertTriangle, Download, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react';

function ComplianceReportView({ graph }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});
  const [typeFilter, setTypeFilter] = useState('all'); // 'all', 'pass', 'fail', 'partial'
  const [itemTypeFilter, setItemTypeFilter] = useState('all'); // 'all', 'door', 'space', etc.
  const [rulesLoaded, setRulesLoaded] = useState(null); // null = checking, false = not loaded, true = loaded
  const [checkingRules, setCheckingRules] = useState(true); // Start as true (checking)

  // Check if rules are loaded on component mount
  useEffect(() => {
    checkRulesStatus();
    
    // Cleanup on unmount - clear cached report so it refreshes next time
    return () => {
      setReport(null);
    };
  }, []);

  // Generate report only after rules check completes and rules are loaded
  useEffect(() => {
    console.log('Report generation effect:', { graph: !!graph, rulesLoaded, checkingRules });
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
      console.log('Rules loaded, calling generateReport');
      generateReport();
    }
  }, [graph, rulesLoaded]);

  const checkRulesStatus = async (forceRefresh = false) => {
    setCheckingRules(true);
    try {
      const url = `/api/rules/check-status${forceRefresh ? '?refresh=true' : ''}`;
      const response = await fetch(url);
      const data = await response.json();
      console.log('Rules status check result:', data);
      setRulesLoaded(data.rules_loaded || false);
      if (!data.rules_loaded) {
        setReport(null); // Clear any existing report
        setError('Regulatory rules not imported. Please import regulation rules from the Rules menu first.');
      } else {
        setError(null);
        // Rules are now loaded, proceed with generating report
        setLoading(true);
        try {
          const response = await fetch('/api/reports/generate-compliance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ graph })
          });

          const data = await response.json();
          if (data.success) {
            setReport(data.report);
            // Store in sessionStorage for ReasoningView to access
            if (data.report && data.report.items) {
              // Transform report structure to compliance results format for ReasoningView
              const complianceResults = {
                results: data.report.items.flatMap(item =>
                  item.rules_evaluated.map(rule => ({
                    rule_id: rule.rule_id,
                    rule_name: rule.rule_name,
                    element_id: item.id,
                    element_guid: item.id,
                    element_type: item.type,
                    element_name: item.name,
                    passed: rule.status === 'pass',
                    severity: rule.severity,
                    explanation: rule.message,
                    properties: item.properties || {},
                    // Flat fields for reasoningService transformation
                    regulation: rule.regulatory_reference,
                    section: rule.code_reference,
                    jurisdiction: rule.jurisdiction,
                    source_link: rule.source_link
                  }))
                ),
                total_checks: data.report.summary.total_items,
                total_elements: data.report.summary.total_items,
                summary: data.report.summary
              };
              sessionStorage.setItem('lastComplianceResults', JSON.stringify(complianceResults));
              sessionStorage.setItem('lastComplianceCheckTime', Date.now().toString());
              console.log('[ComplianceReportView] Stored compliance results:', {
                num_results: complianceResults.results.length,
                total_elements: complianceResults.total_elements
              });
            }
          } else {
            setError(data.error || 'Failed to generate report');
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
      setReport(null); // Clear any existing report
      setError('Failed to verify regulatory rules availability.');
    } finally {
      setCheckingRules(false);
    }
  };

  const generateReport = async () => {
    console.log('generateReport called, rulesLoaded:', rulesLoaded);
    
    // Always re-check rules status before generating report
    // (in case rules were generated/imported after initial check)
    await checkRulesStatus();
  };

  const exportReport = async () => {
    if (!report) {
      alert('No report to export');
      return;
    }

    setExporting(true);
    try {
      const response = await fetch('/api/reports/export-compliance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          report: report,
          graph_name: report.ifc_file || 'compliance'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to export report');
      }

      // Get filename from response headers
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'compliance-report.json';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
        if (filenameMatch) filename = filenameMatch[1];
      }

      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      console.log('Report exported successfully:', filename);
    } catch (err) {
      console.error('Error exporting report:', err);
      alert('Failed to export report: ' + err.message);
    } finally {
      setExporting(false);
    }
  };

  const getComplianceColor = (status) => {
    switch (status) {
      case 'pass':
        return '#10b981';
      case 'fail':
        return '#ef4444';
      case 'partial':
        return '#f59e0b';
      default:
        return '#6b7280';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pass':
        return <CheckCircle size={18} />;
      case 'fail':
        return <AlertCircle size={18} />;
      case 'partial':
        return <AlertTriangle size={18} />;
      default:
        return <AlertCircle size={18} />;
    }
  };

  const getRuleStatusColor = (status) => {
    switch (status) {
      case 'pass':
        return '#d1fae5';
      case 'fail':
        return '#fee2e2';
      case 'unknown':
        return '#f3f4f6';
      default:
        return '#f3f4f6';
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

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  // Show warning if rules not loaded or still checking
  if (checkingRules || rulesLoaded === false || rulesLoaded === null) {
    return (
      <div className="layer-view">
        <div className="layer-header">
          <FileText size={24} />
          <h2>Compliance Report</h2>
        </div>
        <div className="layer-content">
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
                  : 'Please import regulatory rules first to generate compliance reports.'}
              </p>
              {!checkingRules && (
                <p style={{ margin: '1rem 0 0 0', color: '#78350f', fontSize: '0.85rem' }}>
                  1. Go to <strong>Rules</strong> menu → <strong>Regulatory Rules</strong><br/>
                  2. Click <strong>Import Rules</strong> to load the regulation rules<br/>
                  3. Return to this view to generate compliance reports
                </p>
              )}
            </div>
            <button
              onClick={() => checkRulesStatus(true)}
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
        </div>
      </div>
    );
  }

  // Filter items
  const filterItems = (items) => {
    if (!items) return [];
    return items.filter(item => {
      if (typeFilter !== 'all' && item.compliance_status !== typeFilter) {
        return false;
      }
      if (itemTypeFilter !== 'all' && item.type !== itemTypeFilter) {
        return false;
      }
      return true;
    });
  };

  const filteredItems = filterItems(report?.items || []);
  
  // Get unique item types from actual items and count them
  const getItemTypesAndCounts = () => {
    const counts = {};
    (report?.items || []).forEach(item => {
      const type = item.type || 'unknown';
      counts[type] = (counts[type] || 0) + 1;
    });
    return counts;
  };
  
  const itemTypeCounts = getItemTypesAndCounts();
  const itemTypes = Object.keys(itemTypeCounts).sort();

  return (
    <div className="layer-view">
      <div className="layer-header">
        <FileText size={24} />
        <h2>Compliance Report</h2>
        <button
          onClick={generateReport}
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
          title={rulesLoaded !== true ? 'Rules must be imported first' : 'Generate compliance report'}
        >
          <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          {loading ? 'Generating...' : 'Generate Report'}
        </button>
      </div>

      <div className="layer-content">
        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
            Generating compliance report...
          </div>
        )}

        {error && !error.includes('rules') && (
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

        {!loading && report && (
          <>
            {/* Header with File Info */}
            <div style={{
              padding: '1rem',
              backgroundColor: '#f3f4f6',
              borderRadius: '0.5rem',
              marginBottom: '1.5rem',
              border: '1px solid #e5e7eb'
            }}>
              <div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                <strong>IFC File:</strong> {report.ifc_file}
              </div>
              <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
                <strong>Generated:</strong> {new Date(report.generated_at).toLocaleString()}
              </div>
            </div>

            {/* Executive Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '1rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{
                padding: '1rem',
                backgroundColor: '#f3f4f6',
                borderRadius: '0.5rem',
                border: '1px solid #e5e7eb',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: '600', marginBottom: '0.5rem' }}>
                  TOTAL ITEMS
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1f2937' }}>
                  {report.summary.total_items}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#ecfdf5',
                borderRadius: '0.5rem',
                border: '1px solid #d1fae5',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#047857', fontWeight: '600', marginBottom: '0.5rem' }}>
                  COMPLIANT
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#10b981' }}>
                  {report.summary.compliant_items}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#fef2f2',
                borderRadius: '0.5rem',
                border: '1px solid #fecaca',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#991b1b', fontWeight: '600', marginBottom: '0.5rem' }}>
                  NON-COMPLIANT
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#ef4444' }}>
                  {report.summary.non_compliant_items}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#fef3c7',
                borderRadius: '0.5rem',
                border: '1px solid #fde68a',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#92400e', fontWeight: '600', marginBottom: '0.5rem' }}>
                  PARTIAL
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#f59e0b' }}>
                  {report.summary.partial_compliance_items}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#ecf0ff',
                borderRadius: '0.5rem',
                border: '1px solid #c7d2fe',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#3730a3', fontWeight: '600', marginBottom: '0.5rem' }}>
                  OVERALL COMPLIANCE
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#4f46e5' }}>
                  {report.summary.overall_compliance_percentage.toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Explanation Card */}
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
              <div style={{ fontWeight: '600', marginBottom: '0.5rem' }}>📊 Understanding These Metrics:</div>
              <ul style={{ margin: '0.5rem 0', paddingLeft: '1.25rem' }}>
                <li><strong>Overall Compliance %</strong>: Percentage of individual rule checks that <strong>passed</strong> (test-level)</li>
                <li><strong>Compliant Items</strong>: Elements that passed all applicable rules</li>
                <li><strong>Non-Compliant Items</strong>: Elements that failed one or more rules</li>
                <li><strong>Partial</strong>: Elements that passed some rules but failed others</li>
              </ul>
              <div style={{ fontSize: '0.8rem', marginTop: '0.5rem', fontStyle: 'italic', opacity: 0.9 }}>
                The Overall Compliance % measures how many individual rule evaluations passed, not how many elements are compliant
              </div>
            </div>

            {/* Filters */}
            <div style={{
              display: 'flex',
              gap: '1rem',
              marginBottom: '1.5rem',
              flexWrap: 'wrap'
            }}>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: '600' }}>Status:</span>
              </div>
              {['all', 'pass', 'fail', 'partial'].map(status => (
                <button
                  key={status}
                  onClick={() => setTypeFilter(status)}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: typeFilter === status ? getComplianceColor(status) : '#e5e7eb',
                    color: typeFilter === status ? 'white' : '#1f2937',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '600'
                  }}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}

              <div style={{ borderLeft: '1px solid #d1d5db', marginLeft: '1rem', paddingLeft: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: '600' }}>Type:</span>
                <select
                  value={itemTypeFilter}
                  onChange={(e) => setItemTypeFilter(e.target.value)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    backgroundColor: '#fff',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '600',
                    color: '#1f2937'
                  }}
                >
                  <option value="all">All Types ({report?.items?.length || 0} total)</option>
                  {itemTypes.map(type => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)} ({itemTypeCounts[type]})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Items List */}
            <div style={{
              maxHeight: '700px',
              overflowY: 'auto',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              backgroundColor: '#fff'
            }}>
              {filteredItems.length === 0 ? (
                <div style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: '#6b7280'
                }}>
                  No items match the selected filters
                </div>
              ) : (
                filteredItems.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      borderBottom: idx < filteredItems.length - 1 ? '1px solid #e5e7eb' : 'none'
                    }}
                  >
                    {/* Item Header */}
                    <div
                      onClick={() => setExpandedItems(prev => ({
                        ...prev,
                        [idx]: !prev[idx]
                      }))}
                      style={{
                        padding: '1rem',
                        cursor: 'pointer',
                        display: 'flex',
                        gap: '1rem',
                        alignItems: 'flex-start',
                        backgroundColor: idx % 2 === 0 ? '#ffffff' : '#f9fafb'
                      }}
                    >
                      {/* Status Icon */}
                      <div style={{
                        color: getComplianceColor(item.compliance_status),
                        display: 'flex',
                        alignItems: 'center',
                        marginTop: '0.2rem'
                      }}>
                        {getStatusIcon(item.compliance_status)}
                      </div>

                      {/* Item Info */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          display: 'flex',
                          gap: '0.5rem',
                          alignItems: 'center',
                          marginBottom: '0.5rem',
                          flexWrap: 'wrap'
                        }}>
                          <strong style={{ fontSize: '0.95rem' }}>
                            {item.name}
                          </strong>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.2rem 0.5rem',
                            backgroundColor: getComplianceColor(item.compliance_status),
                            color: 'white',
                            borderRadius: '0.25rem',
                            fontSize: '0.7rem',
                            fontWeight: 'bold'
                          }}>
                            {item.compliance_status.toUpperCase()}
                          </span>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.2rem 0.5rem',
                            backgroundColor: '#f0f0f0',
                            color: '#666',
                            borderRadius: '0.25rem',
                            fontSize: '0.7rem'
                          }}>
                            {item.type}
                          </span>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.2rem 0.5rem',
                            backgroundColor: '#ecf0ff',
                            color: '#3730a3',
                            borderRadius: '0.25rem',
                            fontSize: '0.7rem',
                            fontWeight: 'bold'
                          }}>
                            {item.compliance_percentage.toFixed(0)}%
                          </span>
                        </div>

                        {/* ID */}
                        <div style={{
                          fontSize: '0.8rem',
                          color: '#6b7280'
                        }}>
                          ID: {item.id}
                        </div>
                      </div>

                      {/* Expand Arrow */}
                      <span style={{
                        color: '#9ca3af',
                        marginTop: '0.2rem'
                      }}>
                        {expandedItems[idx] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      </span>
                    </div>

                    {/* Expanded Details */}
                    {expandedItems[idx] && (
                      <div style={{
                        padding: '1rem',
                        backgroundColor: idx % 2 === 0 ? '#f9fafb' : '#ffffff',
                        borderTop: '1px solid #e5e7eb',
                        marginLeft: '3rem'
                      }}>
                        {/* Properties */}
                        {item.properties && Object.keys(item.properties).length > 0 && (
                          <div style={{ marginBottom: '1rem' }}>
                            <strong style={{ fontSize: '0.85rem', color: '#1f2937' }}>Properties:</strong>
                            <div style={{
                              marginTop: '0.5rem',
                              padding: '0.75rem',
                              backgroundColor: '#f0f9ff',
                              borderRadius: '0.375rem',
                              border: '1px solid #bfdbfe',
                              fontSize: '0.85rem'
                            }}>
                              {Object.entries(item.properties).map(([key, value]) => (
                                value !== null && value !== undefined && (
                                  <div key={key} style={{ marginBottom: '0.25rem' }}>
                                    <strong>{key}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                  </div>
                                )
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Rules Evaluation */}
                        <div>
                          <strong style={{ fontSize: '0.85rem', color: '#1f2937' }}>
                            Rules Evaluated: ({item.rules_evaluated.length})
                          </strong>
                          <div style={{
                            marginTop: '0.5rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.5rem'
                          }}>
                            {item.rules_evaluated.map((rule, ruleIdx) => (
                              <div
                                key={ruleIdx}
                                style={{
                                  padding: '0.75rem',
                                  backgroundColor: getRuleStatusColor(rule.status),
                                  borderRadius: '0.375rem',
                                  border: `1px solid ${rule.status === 'pass' ? '#a7f3d0' : rule.status === 'fail' ? '#fecaca' : '#e5e7eb'}`,
                                  fontSize: '0.85rem'
                                }}
                              >
                                {/* Rule Header */}
                                <div style={{
                                  display: 'flex',
                                  gap: '0.5rem',
                                  alignItems: 'flex-start',
                                  marginBottom: '0.5rem'
                                }}>
                                  <strong style={{ color: '#1f2937', flex: 1 }}>
                                    {rule.rule_name}
                                  </strong>
                                  <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    padding: '0.15rem 0.4rem',
                                    backgroundColor: getComplianceColor(rule.status),
                                    color: 'white',
                                    borderRadius: '0.25rem',
                                    fontSize: '0.65rem',
                                    fontWeight: 'bold'
                                  }}>
                                    {rule.status.toUpperCase()}
                                  </span>
                                  <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    padding: '0.15rem 0.4rem',
                                    backgroundColor: getSeverityColor(rule.severity),
                                    color: 'white',
                                    borderRadius: '0.25rem',
                                    fontSize: '0.65rem',
                                    fontWeight: 'bold'
                                  }}>
                                    {rule.severity.toUpperCase()}
                                  </span>
                                </div>

                                {/* Evaluation Message */}
                                <div style={{
                                  fontSize: '0.8rem',
                                  color: '#4b5563',
                                  marginBottom: '0.5rem'
                                }}>
                                  {rule.message}
                                </div>

                                {/* Code Reference and Regulatory Info */}
                                <div style={{
                                  fontSize: '0.75rem',
                                  color: '#6b7280',
                                  padding: '0.4rem 0.5rem',
                                  backgroundColor: 'rgba(0,0,0,0.05)',
                                  borderRadius: '0.25rem',
                                  marginBottom: '0.5rem'
                                }}>
                                  <strong>Code:</strong> {rule.code_reference}
                                  {rule.regulatory_reference && (
                                    <>
                                      <br />
                                      <strong>Regulation:</strong> {rule.regulatory_reference}
                                    </>
                                  )}
                                  {rule.jurisdiction && (
                                    <>
                                      <br />
                                      <strong>Jurisdiction:</strong> {rule.jurisdiction}
                                    </>
                                  )}
                                  {rule.source_link && (
                                    <>
                                      <br />
                                      <strong>Source:</strong> <a href={rule.source_link} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6' }}>{rule.source_link}</a>
                                    </>
                                  )}
                                </div>

                                {/* Reasoning Layer */}
                                {rule.reasoning && (
                                  <div style={{
                                    marginBottom: '0.5rem',
                                    padding: '0.4rem 0.5rem',
                                    backgroundColor: 'rgba(59, 130, 246, 0.05)',
                                    borderLeft: '3px solid #3b82f6',
                                    borderRadius: '0.25rem'
                                  }}>
                                    <strong style={{ color: '#1e40af', fontSize: '0.75rem' }}>📚 Reasoning:</strong>
                                    <div style={{ fontSize: '0.75rem', color: '#1e3a8a', marginTop: '0.3rem' }}>
                                      <p style={{ margin: '0.2rem 0' }}>
                                        <strong>Explanation:</strong> {rule.reasoning.short_explanation}
                                      </p>
                                      {rule.reasoning.regulatory_basis && (
                                        <p style={{ margin: '0.2rem 0' }}>
                                          <strong>Regulation:</strong> {rule.reasoning.regulatory_basis}
                                          {rule.reasoning.jurisdiction && ` (${rule.reasoning.jurisdiction})`}
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Remediation for Failed Rules */}
                                {rule.status === 'fail' && rule.remediation && (
                                  <div style={{
                                    marginBottom: '0.5rem',
                                    padding: '0.4rem 0.5rem',
                                    backgroundColor: 'rgba(239, 68, 68, 0.05)',
                                    borderLeft: '3px solid #ef4444',
                                    borderRadius: '0.25rem'
                                  }}>
                                    <strong style={{ color: '#991b1b', fontSize: '0.75rem' }}>🔧 Recommended Fix:</strong>
                                    <div style={{ fontSize: '0.75rem', color: '#7f1d1d', marginTop: '0.3rem' }}>
                                      <p style={{ margin: '0.2rem 0' }}>
                                        {rule.remediation.recommended_fix}
                                      </p>
                                      {rule.remediation.estimated_effort && (
                                        <p style={{ margin: '0.2rem 0' }}>
                                          <strong>Estimated Effort:</strong> {rule.remediation.estimated_effort}
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                )}

                                {/* Benefits */}
                                {(rule.benefits || (rule.remediation && rule.remediation.benefits)) && (
                                  <div style={{
                                    padding: '0.4rem 0.5rem',
                                    backgroundColor: 'rgba(34, 197, 94, 0.05)',
                                    borderLeft: '3px solid #22c55e',
                                    borderRadius: '0.25rem'
                                  }}>
                                    <strong style={{ color: '#15803d', fontSize: '0.75rem' }}>✓ Benefits:</strong>
                                    <ul style={{
                                      fontSize: '0.75rem',
                                      color: '#166534',
                                      margin: '0.3rem 0 0 0',
                                      paddingLeft: '1.2rem'
                                    }}>
                                      {(rule.benefits || rule.remediation.benefits).slice(0, 3).map((benefit, bIdx) => (
                                        <li key={bIdx} style={{ margin: '0.1rem 0' }}>
                                          {benefit}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Action Buttons */}
            <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <button
                onClick={generateReport}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#06b6d4',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                <RefreshCw size={16} />
                Regenerate Report
              </button>

              <button
                onClick={exportReport}
                disabled={exporting || !report}
                style={{
                  padding: '0.75rem 1.5rem',
                  backgroundColor: exporting || !report ? '#d1d5db' : '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: exporting || !report ? 'not-allowed' : 'pointer',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
                title={!report ? 'Generate a report first' : 'Export report as JSON'}
              >
                <Download size={16} />
                {exporting ? 'Exporting...' : 'Export as JSON'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default ComplianceReportView;

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
