import React, { useState, useEffect } from 'react';
import { AlertCircle, AlertTriangle, CheckCircle, Info, Filter, Download, RefreshCw } from 'lucide-react';

function DataValidationView({ graph }) {
  const [validationResults, setValidationResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [severityFilter, setSeverityFilter] = useState('all'); // 'all', 'error', 'warning', 'info'
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'pass', 'fail'
  const [expandedTypes, setExpandedTypes] = useState({});
  const [expandedElements, setExpandedElements] = useState({});

  // Validate IFC data on load
  useEffect(() => {
    if (!graph) return;
    validateIFCData();
  }, [graph]);

  const validateIFCData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/validation/validate-ifc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph })
      });

      const data = await response.json();
      if (data.success) {
        setValidationResults(data.validation);
        // Auto-expand first element type
        const firstType = Object.keys(data.validation.by_element_type || {})[0];
        if (firstType) {
          setExpandedTypes({ [firstType]: true });
        }
      } else {
        setError(data.error || 'Failed to validate IFC data');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'error':
        return <AlertCircle size={14} />;
      case 'warning':
        return <AlertTriangle size={14} />;
      default:
        return <Info size={14} />;
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

  const getStatusColor = (status) => {
    return status === 'pass' ? '#10b981' : '#ef4444';
  };

  const getStatusIcon = (status) => {
    return status === 'pass' ? '✓' : '✗';
  };

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  // Filter properties based on filters
  const filterProperties = (properties) => {
    if (!properties) return [];
    return properties.filter(prop => {
      if (severityFilter !== 'all' && prop.severity?.toLowerCase() !== severityFilter) {
        return false;
      }
      if (statusFilter !== 'all' && prop.status !== statusFilter) {
        return false;
      }
      return true;
    });
  };

  // Calculate statistics
  const calculateStats = () => {
    if (!validationResults) return { total: 0, passed: 0, failed: 0, errors: 0, warnings: 0 };

    let total = 0;
    let passed = 0;
    let failed = 0;
    let errors = 0;
    let warnings = 0;

    Object.values(validationResults.by_element_type || {}).forEach(elemTypeData => {
      (elemTypeData.elements || []).forEach(elem => {
        (elem.properties || []).forEach(prop => {
          total++;
          if (prop.status === 'pass') passed++;
          else failed++;

          if (prop.severity === 'error') errors++;
          else if (prop.severity === 'warning') warnings++;
        });
      });
    });

    return { total, passed, failed, errors, warnings };
  };

  const stats = calculateStats();
  const elementTypes = Object.keys(validationResults?.by_element_type || {});

  return (
    <div className="layer-view">
      <div className="layer-header">
        <CheckCircle size={24} />
        <h2>Data Validation Report</h2>
      </div>

      <div className="layer-content">
        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
            Validating IFC data...
          </div>
        )}

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

        {!loading && validationResults && (
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
                  TOTAL PROPERTIES
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1f2937' }}>
                  {stats.total}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#ecfdf5',
                borderRadius: '0.5rem',
                border: '1px solid #d1fae5'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#047857', fontWeight: '600', marginBottom: '0.5rem' }}>
                  PASSED
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#10b981' }}>
                  {stats.passed}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#fef2f2',
                borderRadius: '0.5rem',
                border: '1px solid #fecaca'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#991b1b', fontWeight: '600', marginBottom: '0.5rem' }}>
                  FAILED
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#ef4444' }}>
                  {stats.failed}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#fef3c7',
                borderRadius: '0.5rem',
                border: '1px solid #fde68a'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#92400e', fontWeight: '600', marginBottom: '0.5rem' }}>
                  WARNINGS
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#f59e0b' }}>
                  {stats.warnings}
                </div>
              </div>

              <div style={{
                padding: '1rem',
                backgroundColor: '#fee2e2',
                borderRadius: '0.5rem',
                border: '1px solid #fecaca'
              }}>
                <div style={{ fontSize: '0.75rem', color: '#991b1b', fontWeight: '600', marginBottom: '0.5rem' }}>
                  ERRORS
                </div>
                <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#ef4444' }}>
                  {stats.errors}
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
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <Filter size={16} />
                <span style={{ fontSize: '0.875rem', fontWeight: '600' }}>Severity:</span>
              </div>
              {['all', 'error', 'warning', 'info'].map(level => (
                <button
                  key={level}
                  onClick={() => setSeverityFilter(level)}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: severityFilter === level ? getSeverityColor(level) : '#e5e7eb',
                    color: severityFilter === level ? 'white' : '#1f2937',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    fontWeight: '600'
                  }}
                >
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}

              <div style={{ borderLeft: '1px solid #d1d5db', marginLeft: '1rem', paddingLeft: '1rem', display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: '600' }}>Status:</span>
              </div>
              {['all', 'pass', 'fail'].map(status => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: statusFilter === status ? getStatusColor(status) : '#e5e7eb',
                    color: statusFilter === status ? 'white' : '#1f2937',
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
            </div>

            {/* Validation Details */}
            <div style={{
              maxHeight: '700px',
              overflowY: 'auto',
              border: '1px solid #e5e7eb',
              borderRadius: '0.5rem',
              backgroundColor: '#fff'
            }}>
              {elementTypes.map(elemType => {
                const elemTypeData = validationResults.by_element_type[elemType];
                const elements = elemTypeData.elements || [];
                
                return (
                  <div key={elemType} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    {/* Element Type Header */}
                    <div
                      onClick={() => setExpandedTypes(prev => ({
                        ...prev,
                        [elemType]: !prev[elemType]
                      }))}
                      style={{
                        padding: '1rem',
                        backgroundColor: '#f3f4f6',
                        fontWeight: '600',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <span>
                        {elemType.charAt(0).toUpperCase() + elemType.slice(1)} ({elements.length} items)
                      </span>
                      <span>{expandedTypes[elemType] ? '▼' : '▶'}</span>
                    </div>

                    {/* Elements in this type */}
                    {expandedTypes[elemType] && (
                      <div>
                        {elements.map((element, elemIdx) => {
                          const filteredProps = filterProperties(element.properties);
                          return (
                            <div key={elemIdx} style={{ borderTop: elemIdx > 0 ? '1px solid #e5e7eb' : 'none' }}>
                              {/* Element Header */}
                              <div
                                onClick={() => setExpandedElements(prev => ({
                                  ...prev,
                                  [`${elemType}-${elemIdx}`]: !prev[`${elemType}-${elemIdx}`]
                                }))}
                                style={{
                                  padding: '0.75rem 1rem',
                                  backgroundColor: '#f9fafb',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  alignItems: 'center',
                                  marginLeft: '1rem',
                                  borderRadius: '0.25rem'
                                }}
                              >
                                <div>
                                  <strong style={{ fontSize: '0.9rem' }}>{element.name || 'Element'}</strong>
                                  <span style={{ fontSize: '0.75rem', color: '#6b7280', marginLeft: '0.5rem' }}>
                                    ID: {element.guid}
                                  </span>
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                  <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                                    {filteredProps.length} properties
                                  </span>
                                  <span>{expandedElements[`${elemType}-${elemIdx}`] ? '▼' : '▶'}</span>
                                </div>
                              </div>

                              {/* Properties */}
                              {expandedElements[`${elemType}-${elemIdx}`] && (
                                <div>
                                  {filteredProps.map((prop, propIdx) => (
                                    <div
                                      key={propIdx}
                                      style={{
                                        padding: '0.75rem 1rem',
                                        borderTop: '1px solid #f3f4f6',
                                        backgroundColor: propIdx % 2 === 0 ? '#fafafa' : '#ffffff',
                                        marginLeft: '1rem',
                                        display: 'flex',
                                        gap: '1rem',
                                        alignItems: 'flex-start'
                                      }}
                                    >
                                      {/* Status Icon */}
                                      <div style={{
                                        fontSize: '1.1rem',
                                        fontWeight: 'bold',
                                        color: getStatusColor(prop.status),
                                        minWidth: '1.2rem',
                                        textAlign: 'center',
                                        marginTop: '0.2rem'
                                      }}>
                                        {getStatusIcon(prop.status)}
                                      </div>

                                      {/* Content */}
                                      <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{
                                          display: 'flex',
                                          gap: '0.5rem',
                                          alignItems: 'center',
                                          marginBottom: '0.5rem',
                                          flexWrap: 'wrap'
                                        }}>
                                          <strong style={{ fontSize: '0.85rem' }}>
                                            {prop.property}
                                          </strong>
                                          <span style={{
                                            display: 'inline-flex',
                                            alignItems: 'center',
                                            gap: '0.25rem',
                                            padding: '0.2rem 0.4rem',
                                            backgroundColor: getStatusColor(prop.status),
                                            color: 'white',
                                            borderRadius: '0.25rem',
                                            fontSize: '0.65rem',
                                            fontWeight: 'bold'
                                          }}>
                                            {prop.status.toUpperCase()}
                                          </span>
                                          {prop.severity && (
                                            <span style={{
                                              display: 'inline-flex',
                                              alignItems: 'center',
                                              gap: '0.25rem',
                                              padding: '0.2rem 0.4rem',
                                              backgroundColor: getSeverityColor(prop.severity),
                                              color: 'white',
                                              borderRadius: '0.25rem',
                                              fontSize: '0.65rem',
                                              fontWeight: 'bold'
                                            }}>
                                              {getSeverityIcon(prop.severity)}
                                              {prop.severity.toUpperCase()}
                                            </span>
                                          )}
                                        </div>

                                        {/* Actual vs Required */}
                                        <div style={{
                                          display: 'grid',
                                          gridTemplateColumns: '1fr 1fr',
                                          gap: '0.5rem',
                                          fontSize: '0.8rem',
                                          marginBottom: '0.5rem'
                                        }}>
                                          <div style={{
                                            padding: '0.4rem 0.5rem',
                                            backgroundColor: '#f0f9ff',
                                            borderRadius: '0.25rem',
                                            border: '1px solid #bfdbfe'
                                          }}>
                                            <strong>ACTUAL VALUE</strong>
                                            <div style={{ color: '#1e40af', marginTop: '0.2rem' }}>
                                              {prop.actual_value}
                                            </div>
                                          </div>
                                          <div style={{
                                            padding: '0.4rem 0.5rem',
                                            backgroundColor: '#f0fdf4',
                                            borderRadius: '0.25rem',
                                            border: '1px solid #bbf7d0'
                                          }}>
                                            <strong>REQUIRED VALUE</strong>
                                            <div style={{ color: '#166534', marginTop: '0.2rem' }}>
                                              {prop.required_value}
                                            </div>
                                          </div>
                                        </div>

                                        {/* Message */}
                                        {prop.message && (
                                          <div style={{
                                            fontSize: '0.8rem',
                                            color: '#4b5563',
                                            marginBottom: '0.5rem'
                                          }}>
                                            <strong>Message:</strong> {prop.message}
                                          </div>
                                        )}

                                        {/* Reason */}
                                        {prop.reason && (
                                          <div style={{
                                            fontSize: '0.75rem',
                                            color: '#6b7280',
                                            padding: '0.4rem 0.5rem',
                                            backgroundColor: '#f3f4f6',
                                            borderRadius: '0.25rem',
                                            borderLeft: `3px solid ${getSeverityColor(prop.severity)}`
                                          }}>
                                            <strong>Reason:</strong> {prop.reason}
                                          </div>
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
                );
              })}
            </div>

            {/* Action Buttons */}
            <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem' }}>
              <button
                onClick={validateIFCData}
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
                Refresh Validation
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default DataValidationView;
