import React, { useState } from 'react';
import { CheckCircle, BookOpen, Plus } from 'lucide-react';
import RuleCatalogueModal from './RuleCatalogueModal';
import RuleManagementPanel from './RuleManagementPanel';

function RuleLayerView({ graph }) {
  const [showCatalogue, setShowCatalogue] = useState(false);
  const [showManagement, setShowManagement] = useState(false);

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
          <h2>Rule Layer</h2>
        </div>

        <div className="layer-content">
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
            Manage Rules
          </button>
        </div>
        </div>
      </div>

      {/* Modals */}
      <RuleCatalogueModal isOpen={showCatalogue} onClose={() => setShowCatalogue(false)} />
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
