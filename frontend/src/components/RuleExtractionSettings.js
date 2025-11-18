import React, { useState } from 'react';
import { Settings, CheckCircle2, AlertCircle, TrendingUp } from 'lucide-react';

function RuleExtractionSettings({ isOpen, onClose, onApply }) {
  const [strategies, setStrategies] = useState({
    pset: true,
    statistical: true,
    metadata: true,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const handleToggle = (strategy) => {
    setStrategies(prev => ({
      ...prev,
      [strategy]: !prev[strategy]
    }));
  };

  const handleApply = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const selectedStrategies = Object.keys(strategies).filter(s => strategies[s]);
      if (selectedStrategies.length === 0) {
        setMessage({ type: 'error', text: 'Select at least one extraction strategy' });
        return;
      }
      if (onApply) {
        await onApply(selectedStrategies);
      }
      setMessage({ type: 'success', text: '✓ Extraction strategies updated' });
      setTimeout(() => onClose(), 2000);
    } catch (err) {
      setMessage({ type: 'error', text: `Error: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '500px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Settings size={24} />
            <h2 style={{ margin: 0 }}>Rule Extraction Strategies</h2>
          </div>
          <button onClick={onClose} className="close-button" style={{ fontSize: '1.5rem' }}>✕</button>
        </div>

        <div style={{ padding: '1.5rem' }}>
          <p style={{ marginBottom: '1.5rem', color: '#666', fontSize: '0.9rem' }}>
            Select which strategies to use when extracting rules from IFC data:
          </p>

          {/* PSet Strategy */}
          <div style={{
            padding: '1rem',
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            cursor: 'pointer',
            backgroundColor: strategies.pset ? '#f0f9ff' : '#fff',
            transition: 'background-color 0.2s'
          }} onClick={() => handleToggle('pset')}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
              <input
                type="checkbox"
                checked={strategies.pset}
                onChange={() => handleToggle('pset')}
                style={{ marginTop: '0.25rem', cursor: 'pointer' }}
              />
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', color: '#1f2937' }}>
                  <CheckCircle2 size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Property Set Heuristic
                </h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                  Scans IFC property sets for rule parameters (door widths, space areas, occupancy limits)
                </p>
              </div>
            </div>
          </div>

          {/* Statistical Strategy */}
          <div style={{
            padding: '1rem',
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            marginBottom: '1rem',
            cursor: 'pointer',
            backgroundColor: strategies.statistical ? '#f0fdf4' : '#fff',
            transition: 'background-color 0.2s'
          }} onClick={() => handleToggle('statistical')}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
              <input
                type="checkbox"
                checked={strategies.statistical}
                onChange={() => handleToggle('statistical')}
                style={{ marginTop: '0.25rem', cursor: 'pointer' }}
              />
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', color: '#1f2937' }}>
                  <TrendingUp size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Statistical Baseline
                </h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                  Generates baseline rules from building data (e.g., 10th percentile of all door widths)
                </p>
              </div>
            </div>
          </div>

          {/* Metadata Strategy */}
          <div style={{
            padding: '1rem',
            border: '1px solid #e5e7eb',
            borderRadius: '0.5rem',
            marginBottom: '1.5rem',
            cursor: 'pointer',
            backgroundColor: strategies.metadata ? '#fef2f2' : '#fff',
            transition: 'background-color 0.2s'
          }} onClick={() => handleToggle('metadata')}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
              <input
                type="checkbox"
                checked={strategies.metadata}
                onChange={() => handleToggle('metadata')}
                style={{ marginTop: '0.25rem', cursor: 'pointer' }}
              />
              <div>
                <h4 style={{ margin: '0 0 0.25rem 0', color: '#1f2937' }}>
                  <AlertCircle size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Data Completeness
                </h4>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>
                  Detects missing data and generates validation rules (e.g., doors without width data)
                </p>
              </div>
            </div>
          </div>

          {message && (
            <div style={{
              padding: '0.75rem',
              marginBottom: '1rem',
              borderRadius: '0.375rem',
              backgroundColor: message.type === 'success' ? '#dcfce7' : '#fee2e2',
              color: message.type === 'success' ? '#166534' : '#991b1b',
              fontSize: '0.875rem'
            }}>
              {message.text}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button
              onClick={onClose}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#e5e7eb',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontWeight: '500',
                fontSize: '0.875rem'
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              disabled={loading}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#3b82f6',
                color: '#fff',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: '500',
                fontSize: '0.875rem',
                opacity: loading ? 0.5 : 1
              }}
            >
              {loading ? 'Applying...' : 'Apply Strategies'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default RuleExtractionSettings;
