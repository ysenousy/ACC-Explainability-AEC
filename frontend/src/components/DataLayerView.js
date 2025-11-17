import React from 'react';
import { Database } from 'lucide-react';

function DataLayerView({ graph }) {
  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const meta = graph.meta || {};
  const coverage = meta.coverage || {};

  return (
    <div className="layer-view">
      <div className="layer-header">
        <Database size={24} />
        <h2>Data Layer</h2>
      </div>

      <div className="layer-content">
        <div className="info-section">
          <h3>Schema Information</h3>
          <table className="info-table">
            <tbody>
              <tr>
                <td><strong>Schema:</strong></td>
                <td>{meta.schema || 'Unknown'}</td>
              </tr>
              <tr>
                <td><strong>Version:</strong></td>
                <td>{meta.schema_version || 'N/A'}</td>
              </tr>
              <tr>
                <td><strong>Generated:</strong></td>
                <td>{new Date(graph.generated_at).toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="info-section">
          <h3>Coverage</h3>
          <table className="info-table">
            <tbody>
              <tr>
                <td><strong>Total Spaces:</strong></td>
                <td>{coverage.num_spaces || 0}</td>
              </tr>
              <tr>
                <td><strong>Spaces with Area:</strong></td>
                <td>{coverage.spaces_with_area || 0}</td>
              </tr>
              <tr>
                <td><strong>Total Doors:</strong></td>
                <td>{coverage.num_doors || 0}</td>
              </tr>
              <tr>
                <td><strong>Doors with Width:</strong></td>
                <td>{coverage.doors_with_width || 0}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="info-section">
          <h3>Source</h3>
          <p style={{ fontSize: '0.9rem', wordBreak: 'break-all', color: '#666' }}>
            {graph.source_file || 'N/A'}
          </p>
        </div>
      </div>
    </div>
  );
}

export default DataLayerView;
