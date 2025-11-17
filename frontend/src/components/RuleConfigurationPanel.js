import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, AlertCircle, CheckCircle } from 'lucide-react';

function RuleConfigurationPanel({ isOpen, onClose, onConfigUpdate }) {
  // Configuration state
  const [config, setConfig] = useState({
    door: {
      min_width_mm: 900,
      severity: 'ERROR',
      code_reference: 'IBC 2018 §1010.1.1'
    },
    space: {
      min_area_m2: 6,
      severity: 'ERROR',
      code_reference: 'IBC 2018 §1204.2'
    },
    building: {
      max_occupancy_per_storey: 50,
      severity: 'WARNING',
      code_reference: 'IBC 2018 §1004'
    }
  });

  // UI state
  const [expandedSections, setExpandedSections] = useState({
    door: true,
    space: true,
    building: true
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);

  // Toggle section expansion
  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // Handle input change
  const handleInputChange = (section, field, value) => {
    setConfig(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };

  // Reset to defaults
  const handleReset = () => {
    setConfig({
      door: {
        min_width_mm: 900,
        severity: 'ERROR',
        code_reference: 'IBC 2018 §1010.1.1'
      },
      space: {
        min_area_m2: 6,
        severity: 'ERROR',
        code_reference: 'IBC 2018 §1204.2'
      },
      building: {
        max_occupancy_per_storey: 50,
        severity: 'WARNING',
        code_reference: 'IBC 2018 §1004'
      }
    });
    setMessage('Reset to default configuration');
    setMessageType('info');
    setTimeout(() => setMessage(null), 3000);
  };

  // Save configuration
  const handleSave = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const response = await fetch('/api/rules/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const data = await response.json();
      if (data.success) {
        setMessage('Configuration updated successfully');
        setMessageType('success');
        if (onConfigUpdate) {
          onConfigUpdate(data.config);
        }
        setTimeout(() => {
          setMessage(null);
          if (onClose) onClose();
        }, 2000);
      } else {
        setMessage(data.error || 'Failed to update configuration');
        setMessageType('error');
      }
    } catch (err) {
      setMessage(err.message);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const renderConfigSection = (title, section, fields) => (
    <div style={{
      marginBottom: '1rem',
      border: '1px solid #e5e7eb',
      borderRadius: '0.375rem',
      overflow: 'hidden'
    }}>
      {/* Section Header */}
      <button
        onClick={() => toggleSection(section)}
        style={{
          width: '100%',
          padding: '1rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#f3f4f6',
          border: 'none',
          cursor: 'pointer',
          fontWeight: '500',
          fontSize: '0.875rem',
          transition: 'background-color 0.2s'
        }}
        onMouseEnter={(e) => e.target.style.backgroundColor = '#e5e7eb'}
        onMouseLeave={(e) => e.target.style.backgroundColor = '#f3f4f6'}
      >
        <span>{title}</span>
        {expandedSections[section] ? (
          <ChevronUp size={18} />
        ) : (
          <ChevronDown size={18} />
        )}
      </button>

      {/* Section Content */}
      {expandedSections[section] && (
        <div style={{
          padding: '1rem',
          backgroundColor: '#fafafa',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem'
        }}>
          {fields.map(field => (
            <div key={field.name} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <label style={{
                fontSize: '0.75rem',
                fontWeight: '500',
                color: '#374151',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                {field.label}
              </label>
              {field.type === 'select' ? (
                <select
                  value={config[section][field.name]}
                  onChange={(e) => handleInputChange(section, field.name, e.target.value)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    backgroundColor: '#fff'
                  }}
                >
                  {field.options.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : (
                <input
                  type={field.type || 'text'}
                  value={config[section][field.name]}
                  onChange={(e) => handleInputChange(section, field.name, e.target.value)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem'
                  }}
                />
              )}
              {field.help && (
                <small style={{ color: '#6b7280', fontSize: '0.75rem' }}>
                  {field.help}
                </small>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '600px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="modal-header">
          <h2>Rule Configuration</h2>
          <button onClick={onClose} className="close-button">
            ✕
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {message && (
            <div style={{
              padding: '0.75rem 1rem',
              marginBottom: '1rem',
              borderRadius: '0.375rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              backgroundColor: messageType === 'success' ? '#dcfce7' : messageType === 'error' ? '#fee2e2' : '#dbeafe',
              color: messageType === 'success' ? '#166534' : messageType === 'error' ? '#991b1b' : '#0c4a6e',
              fontSize: '0.875rem'
            }}>
              {messageType === 'success' && <CheckCircle size={18} />}
              {messageType === 'error' && <AlertCircle size={18} />}
              {message}
            </div>
          )}

          {/* Door Configuration */}
          {renderConfigSection('Door Rules', 'door', [
            {
              name: 'min_width_mm',
              label: 'Minimum Width (mm)',
              type: 'number',
              help: 'Minimum required door width in millimeters'
            },
            {
              name: 'severity',
              label: 'Severity Level',
              type: 'select',
              options: ['ERROR', 'WARNING', 'INFO'],
              help: 'Severity level for violations'
            },
            {
              name: 'code_reference',
              label: 'Code Reference',
              type: 'text',
              help: 'Building code reference'
            }
          ])}

          {/* Space Configuration */}
          {renderConfigSection('Space Rules', 'space', [
            {
              name: 'min_area_m2',
              label: 'Minimum Area (m²)',
              type: 'number',
              step: '0.1',
              help: 'Minimum required space area in square meters'
            },
            {
              name: 'severity',
              label: 'Severity Level',
              type: 'select',
              options: ['ERROR', 'WARNING', 'INFO'],
              help: 'Severity level for violations'
            },
            {
              name: 'code_reference',
              label: 'Code Reference',
              type: 'text',
              help: 'Building code reference'
            }
          ])}

          {/* Building Configuration */}
          {renderConfigSection('Building Rules', 'building', [
            {
              name: 'max_occupancy_per_storey',
              label: 'Max Occupancy per Storey',
              type: 'number',
              help: 'Maximum occupancy allowed per storey'
            },
            {
              name: 'severity',
              label: 'Severity Level',
              type: 'select',
              options: ['ERROR', 'WARNING', 'INFO'],
              help: 'Severity level for violations'
            },
            {
              name: 'code_reference',
              label: 'Code Reference',
              type: 'text',
              help: 'Building code reference'
            }
          ])}
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
            onClick={handleReset}
            disabled={loading}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#e5e7eb',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              opacity: loading ? 0.6 : 1,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => !loading && (e.target.style.backgroundColor = '#d1d5db')}
            onMouseLeave={(e) => !loading && (e.target.style.backgroundColor = '#e5e7eb')}
          >
            Reset to Default
          </button>
          <button
            onClick={onClose}
            disabled={loading}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#d1d5db',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              opacity: loading ? 0.6 : 1,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => !loading && (e.target.style.backgroundColor = '#9ca3af')}
            onMouseLeave={(e) => !loading && (e.target.style.backgroundColor = '#d1d5db')}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: loading ? '#9ca3af' : '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => !loading && (e.target.style.backgroundColor = '#2563eb')}
            onMouseLeave={(e) => !loading && (e.target.style.backgroundColor = '#3b82f6')}
          >
            {loading ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default RuleConfigurationPanel;
