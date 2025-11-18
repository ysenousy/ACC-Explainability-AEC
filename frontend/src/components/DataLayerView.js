import React from 'react';
import { Database } from 'lucide-react';

function DataLayerView({ graph, summary }) {
  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const meta = graph.meta || {};
  const coverage = summary || {};

  return (
    <div className="layer-view">
      <div className="layer-header">
        <Database size={24} />
        <h2>Model Summary</h2>
      </div>

      <div className="layer-content">
        {/* Summary Statistics */}
        <div className="info-section">
          <h3>IFC Entity Summary</h3>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '0.75rem',
            marginBottom: '1.5rem'
          }}>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem' }}>{coverage.ifc_building || 0}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.95 }}>IfcBuilding</div>
            </div>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem' }}>{coverage.ifc_building_storey || 0}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.95 }}>IfcBuildingStorey</div>
            </div>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem' }}>{coverage.ifc_space || 0}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.95 }}>IfcSpace</div>
            </div>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem' }}>{coverage.ifc_door || 0}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.95 }}>IfcDoor</div>
            </div>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem' }}>{coverage.ifc_wall || 0}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.95 }}>IfcWall</div>
            </div>
            <div style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center',
              boxShadow: '0 2px 8px rgba(102, 126, 234, 0.2)'
            }}>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', marginBottom: '0.25rem' }}>{coverage.ifc_window || 0}</div>
              <div style={{ fontSize: '0.75rem', opacity: 0.95 }}>IfcWindow</div>
            </div>
          </div>
        </div>

        <div className="info-section">
          <h3>Schema Information</h3>
          <table className="info-table">
            <tbody>
              <tr>
                <td><strong>File Name:</strong></td>
                <td style={{ wordBreak: 'break-all' }}>{graph.source_file || 'Unknown'}</td>
              </tr>
              <tr>
                <td><strong>Schema Type:</strong></td>
                <td>{meta.schema || 'Unknown'}</td>
              </tr>
              <tr>
                <td><strong>Generated:</strong></td>
                <td>{new Date(graph.generated_at).toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default DataLayerView;
