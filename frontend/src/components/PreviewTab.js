import React from 'react';
import { BarChart3 } from 'lucide-react';

function PreviewTab({ preview, summary }) {
  if (!preview || !summary) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <p>Loading preview...</p>
      </div>
    );
  }

  const counts = preview.counts || {};
  const storeys = preview.storey_summary || [];

  return (
    <div className="preview-tab">
      {/* Summary Stats */}
      <div className="grid">
        <div className="stat-card">
          <div className="stat-card-label">Total Spaces</div>
          <div className="stat-card-value">{summary.num_spaces}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Total Doors</div>
          <div className="stat-card-value">{summary.num_doors}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Spaces with Area</div>
          <div className="stat-card-value">{summary.spaces_with_area}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Doors with Width</div>
          <div className="stat-card-value">{summary.doors_with_width}</div>
        </div>
      </div>

      {/* Schema Info */}
      <div className="card">
        <div className="card-title">IFC Schema</div>
        <p><strong>Schema:</strong> {preview.schema || 'Unknown'}</p>
      </div>

      {/* Element Counts */}
      <div className="card">
        <div className="card-title">Element Counts</div>
        <table>
          <thead>
            <tr>
              <th>Element Type</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(counts).map(([type, count]) => (
              <tr key={type}>
                <td>{type}</td>
                <td className="badge badge-info">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Per-Storey Breakdown */}
      {storeys.length > 0 && (
        <div className="card">
          <div className="card-title">Per-Storey Breakdown</div>
          <table>
            <thead>
              <tr>
                <th>Storey</th>
                <th>Elevation</th>
                <th>Total Elements</th>
                <th>Spaces</th>
                <th>Doors</th>
              </tr>
            </thead>
            <tbody>
              {storeys.map((storey) => (
                <tr key={storey.storey_id}>
                  <td>{storey.storey_name || 'Unknown'}</td>
                  <td>{storey.elevation ?? '—'}</td>
                  <td>{storey.counts.total_elements}</td>
                  <td>{storey.counts.spaces || 0}</td>
                  <td>{storey.counts.doors || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default PreviewTab;
