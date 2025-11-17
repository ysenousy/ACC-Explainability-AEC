import React, { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronRight, AlertCircle, AlertTriangle, Info } from 'lucide-react';

function RuleCatalogueModal({ isOpen, onClose }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRules, setExpandedRules] = useState({});

  // Fetch rules catalogue on mount or when modal opens
  useEffect(() => {
    if (!isOpen) return;

    const fetchRules = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/rules/catalogue');
        const data = await response.json();
        if (data.success) {
          setRules(data.rules || []);
        } else {
          setError(data.error || 'Failed to fetch rules');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRules();
  }, [isOpen]);

  const toggleExpanded = (ruleId) => {
    setExpandedRules(prev => ({
      ...prev,
      [ruleId]: !prev[ruleId]
    }));
  };

  const filteredRules = rules.filter(rule =>
    rule.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rule.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rule.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'error':
        return <AlertCircle size={16} className="severity-error" />;
      case 'warning':
        return <AlertTriangle size={16} className="severity-warning" />;
      default:
        return <Info size={16} className="severity-info" />;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'error':
        return '#dc2626';
      case 'warning':
        return '#f59e0b';
      default:
        return '#3b82f6';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '900px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="modal-header">
          <h2>Rules Catalogue</h2>
          <button onClick={onClose} className="close-button">
            <X size={24} />
          </button>
        </div>

        {/* Search */}
        <div style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb', backgroundColor: '#f9fafb' }}>
          <input
            type="text"
            placeholder="Search rules by name, ID, or description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem 0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
            }}
          />
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
              Loading rules...
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

          {!loading && filteredRules.length === 0 && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
              {searchTerm ? 'No rules match your search' : 'No rules available'}
            </div>
          )}

          {!loading && filteredRules.map((rule) => (
            <div
              key={rule.id}
              style={{
                marginBottom: '1rem',
                border: '1px solid #e5e7eb',
                borderRadius: '0.375rem',
                overflow: 'hidden'
              }}
            >
              {/* Rule Header - Expandable */}
              <button
                onClick={() => toggleExpanded(rule.id)}
                style={{
                  width: '100%',
                  padding: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  backgroundColor: '#f3f4f6',
                  border: 'none',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.target.parentElement.style.backgroundColor = '#e5e7eb'}
                onMouseLeave={(e) => e.target.parentElement.style.backgroundColor = '#f3f4f6'}
              >
                {expandedRules[rule.id] ? (
                  <ChevronDown size={18} />
                ) : (
                  <ChevronRight size={18} />
                )}
                <span style={{ flex: 1 }}>
                  <strong>{rule.name || rule.id}</strong>
                  {rule.severity && (
                    <span style={{
                      marginLeft: '0.75rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.25rem 0.5rem',
                      backgroundColor: '#fff',
                      borderRadius: '0.25rem',
                      fontSize: '0.75rem',
                      fontWeight: 'bold',
                      color: getSeverityColor(rule.severity),
                      border: `1px solid ${getSeverityColor(rule.severity)}`
                    }}>
                      {getSeverityIcon(rule.severity)}
                      {rule.severity.toUpperCase()}
                    </span>
                  )}
                </span>
              </button>

              {/* Rule Details - Expandable */}
              {expandedRules[rule.id] && (
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#fafafa',
                  borderTop: '1px solid #e5e7eb'
                }}>
                  {rule.description && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <p style={{ color: '#4b5563', fontSize: '0.875rem', lineHeight: '1.5' }}>
                        {rule.description}
                      </p>
                    </div>
                  )}

                  {rule.code_reference && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <strong style={{ fontSize: '0.75rem', color: '#6b7280' }}>Code Reference:</strong>
                      <p style={{ fontSize: '0.875rem', color: '#4b5563', margin: '0.25rem 0 0 0' }}>
                        {rule.code_reference}
                      </p>
                    </div>
                  )}

                  {rule.parameters && Object.keys(rule.parameters).length > 0 && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <strong style={{ fontSize: '0.75rem', color: '#6b7280' }}>Parameters:</strong>
                      <div style={{
                        marginTop: '0.5rem',
                        padding: '0.5rem',
                        backgroundColor: '#fff',
                        borderRadius: '0.25rem',
                        border: '1px solid #e5e7eb'
                      }}>
                        <table style={{
                          width: '100%',
                          fontSize: '0.75rem',
                          borderCollapse: 'collapse'
                        }}>
                          <tbody>
                            {Object.entries(rule.parameters).map(([key, val]) => (
                              <tr key={key}>
                                <td style={{
                                  padding: '0.25rem 0.5rem',
                                  fontWeight: '500',
                                  color: '#374151',
                                  borderBottom: '1px solid #e5e7eb'
                                }}>
                                  {key}
                                </td>
                                <td style={{
                                  padding: '0.25rem 0.5rem',
                                  color: '#6b7280',
                                  borderBottom: '1px solid #e5e7eb',
                                  textAlign: 'right'
                                }}>
                                  {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.75rem',
          backgroundColor: '#f9fafb'
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#e5e7eb',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#d1d5db'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#e5e7eb'}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default RuleCatalogueModal;
