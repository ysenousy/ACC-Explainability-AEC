import React, { useState } from 'react';
import { CheckCircle, BookOpen, Plus, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import RuleCatalogueModal from './RuleCatalogueModal';
import RuleManagementPanel from './RuleManagementPanel';

function RuleLayerView({ graph }) {
  const [showCatalogue, setShowCatalogue] = useState(false);
  const [showManagement, setShowManagement] = useState(false);
  const [confirmedRules, setConfirmedRules] = useState([]);

  const handleConfirmRules = (rules) => {
    setConfirmedRules(rules);
    setShowCatalogue(false);
    // Don't close management panel here - let user control it
  };

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'error': return <AlertCircle size={14} />;
      case 'warning': return <AlertTriangle size={14} />;
      case 'info': return <Info size={14} />;
      default: return null;
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'error': return '#ef4444';
      case 'warning': return '#f59e0b';
      case 'info': return '#3b82f6';
      default: return '#6b7280';
    }
  };

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  return (
    <>
      <div className="layer-view">
        <div className="layer-header">
          <CheckCircle size={24} />
          <h2>Regulatory Rules Layer</h2>
        </div>

        <div className="layer-content">
        <div style={{ 
          padding: '0.75rem 1rem', 
          marginBottom: '1rem', 
          backgroundColor: '#e0f2fe', 
          border: '1px solid #0284c7', 
          borderRadius: '0.375rem',
          fontSize: '0.875rem',
          color: '#0c4a6e'
        }}>
          <strong>📋 Regulatory Rules Catalogue:</strong> Select and view compliance rules from your rules catalogue. This section manages verified regulatory standards for compliance checking.
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <button
            onClick={() => setShowCatalogue(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
          >
            <BookOpen size={16} />
            View Regulatory Rules
          </button>
          <button
            onClick={() => setShowManagement(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#d97706'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#f59e0b'}
          >
            <Plus size={16} />
            Manage Regulatory Rules
          </button>
        </div>

        {/* Confirmed Rules Display */}
        {confirmedRules.length > 0 && (
          <div style={{ marginTop: '2rem' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1rem',
              paddingBottom: '0.75rem',
              borderBottom: '2px solid #10b981'
            }}>
              <h3 style={{ margin: 0, color: '#10b981', fontSize: '1rem', fontWeight: '600' }}>
                ✓ Confirmed Regulatory Rules ({confirmedRules.length})
              </h3>
              <button
                onClick={() => setConfirmedRules([])}
                style={{
                  padding: '0.5rem 0.75rem',
                  backgroundColor: '#fee2e2',
                  color: '#991b1b',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: '500',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#fecaca'}
                onMouseLeave={(e) => e.target.style.backgroundColor = '#fee2e2'}
              >
                Clear
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
              gap: '1rem'
            }}>
              {confirmedRules.map((rule) => (
                <div
                  key={rule.id}
                  style={{
                    padding: '1rem',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.5rem',
                    backgroundColor: '#fff',
                    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.1)';
                    e.currentTarget.style.borderColor = '#d1d5db';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = '0 1px 2px rgba(0, 0, 0, 0.05)';
                    e.currentTarget.style.borderColor = '#e5e7eb';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <strong style={{ fontSize: '0.95rem' }}>{rule.name || rule.id}</strong>
                    {rule.severity && (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        padding: '0.25rem 0.5rem',
                        backgroundColor: getSeverityColor(rule.severity),
                        color: 'white',
                        borderRadius: '0.25rem',
                        fontSize: '0.7rem',
                        fontWeight: 'bold'
                      }}>
                        {getSeverityIcon(rule.severity)}
                        {rule.severity.toUpperCase()}
                      </span>
                    )}
                  </div>

                  {rule.description && (
                    <p style={{
                      margin: '0.5rem 0',
                      fontSize: '0.875rem',
                      color: '#6b7280',
                      lineHeight: '1.4'
                    }}>
                      {rule.description}
                    </p>
                  )}

                  {rule.target_type && (
                    <div style={{
                      fontSize: '0.75rem',
                      color: '#6b7280',
                      marginTop: '0.5rem',
                      padding: '0.5rem',
                      backgroundColor: '#f9fafb',
                      borderRadius: '0.25rem'
                    }}>
                      <strong>Target:</strong> {rule.target_type}
                    </div>
                  )}

                  {rule.parameters && Object.keys(rule.parameters).length > 0 && (
                    <div style={{
                      fontSize: '0.75rem',
                      color: '#6b7280',
                      marginTop: '0.5rem',
                      padding: '0.5rem',
                      backgroundColor: '#f9fafb',
                      borderRadius: '0.25rem'
                    }}>
                      <strong>Parameters:</strong>
                      <ul style={{ margin: '0.25rem 0 0 1rem', paddingLeft: '0.5rem' }}>
                        {Object.entries(rule.parameters).map(([key, value]) => (
                          <li key={key}>
                            {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        </div>
      </div>

      {/* Modals */}
      <RuleCatalogueModal 
        isOpen={showCatalogue} 
        onClose={() => setShowCatalogue(false)}
        onConfirmRules={handleConfirmRules}
      />
      <RuleManagementPanel
        isOpen={showManagement}
        onClose={() => setShowManagement(false)}
        extractedRules={[]}
        onRulesUpdated={() => {}}
      />
    </>
  );
}

export default RuleLayerView;
