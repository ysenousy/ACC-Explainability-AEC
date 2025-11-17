import React from 'react';
import { Zap } from 'lucide-react';

function ReasoningView({ graph }) {
  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  // Placeholder: Reasoning layer will show inference logic, rule dependencies, etc.
  const manifest = graph.meta?.rules_manifest || {};
  const rules = manifest.rules || [];

  return (
    <div className="layer-view">
      <div className="layer-header">
        <Zap size={24} />
        <h2>Reasoning</h2>
      </div>

      <div className="layer-content">
        <div className="info-section">
          <h3>Rule Dependencies & Logic</h3>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            This view displays how rules depend on each other and their inference logic.
          </p>

          {rules.length === 0 ? (
            <p style={{ color: '#999' }}>No rules to analyze</p>
          ) : (
            <div style={{ fontSize: '0.9rem' }}>
              <p>
                <strong>Total rules:</strong> {rules.length}
              </p>
              <p style={{ marginTop: '0.5rem', color: '#666' }}>
                Rule dependency graph, inference chains, and logical deductions would appear here.
              </p>
            </div>
          )}
        </div>

        <div className="info-section">
          <h3>Inference Chains</h3>
          <p style={{ color: '#999' }}>No inference chains available yet (placeholder)</p>
        </div>
      </div>
    </div>
  );
}

export default ReasoningView;
