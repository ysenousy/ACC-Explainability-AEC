import React, { useState } from 'react';
import { CheckCircle, BookOpen, Settings } from 'lucide-react';
import RuleCatalogueModal from './RuleCatalogueModal';
import RuleConfigurationPanel from './RuleConfigurationPanel';

function RuleLayerView({ graph }) {
  const [showCatalogue, setShowCatalogue] = useState(false);
  const [showConfiguration, setShowConfiguration] = useState(false);

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const meta = graph.meta || {};
  const manifest = meta.rules_manifest || {};
  const rules = manifest.rules || [];

  return (
    <>
      <div className="layer-view">
        <div className="layer-header">
          <CheckCircle size={24} />
          <h2>Rule Layer</h2>
        </div>

        <div className="layer-content">
          <div className="info-section">
            <h3>Rules Manifest</h3>
            <p>
              <strong>Total Rules:</strong> {rules.length}
            </p>
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
              View Catalogue
            </button>
            <button
              onClick={() => setShowConfiguration(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontWeight: '500',
                fontSize: '0.875rem',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = '#059669'}
              onMouseLeave={(e) => e.target.style.backgroundColor = '#10b981'}
            >
              <Settings size={16} />
              Configure
            </button>
          </div>

          {rules.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: '#999' }}>
              <p>No rules extracted from this IFC file</p>
            </div>
          ) : (
            <div className="rules-list">
              {rules.map((rule, idx) => (
                <div key={idx} className="rule-item">
                  <div className="rule-header">
                    <span className="rule-id">{rule.id || `Rule ${idx + 1}`}</span>
                    <span className="rule-type">{rule.type || 'parametric'}</span>
                  </div>
                  <p className="rule-description">{rule.description || 'No description'}</p>
                  {rule.parameters && Object.keys(rule.parameters).length > 0 && (
                    <div className="rule-params">
                      <strong>Parameters:</strong>
                      <ul>
                        {Object.entries(rule.parameters).map(([key, val]) => (
                          <li key={key}>
                            {key}: {JSON.stringify(val)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modals */}
      <RuleCatalogueModal isOpen={showCatalogue} onClose={() => setShowCatalogue(false)} />
      <RuleConfigurationPanel 
        isOpen={showConfiguration} 
        onClose={() => setShowConfiguration(false)}
      />
    </>
  );
}

export default RuleLayerView;
