import React from 'react';
import { X, CheckCircle, AlertCircle, Loader } from 'lucide-react';

function PreviewConfirmationModal({ preview, summary, fileName, onConfirm, onCancel, loading }) {
  if (!preview || !summary) {
    return null;
  }

  const counts = preview.counts || {};
  const storeys = preview.storey_summary || [];

  return (
    <div className="modal-overlay">
      <div className="modal modal-large">
        <div className="modal-header">
          <h2 className="modal-title">Preview IFC File</h2>
          <button className="modal-close" onClick={onCancel} disabled={loading}>
            <X size={24} />
          </button>
        </div>

        <div className="modal-content">
          {/* File Info */}
          <div className="preview-section">
            <h3>File Information</h3>
            <table className="preview-table">
              <tbody>
                <tr>
                  <td><strong>File Name:</strong></td>
                  <td>{fileName}</td>
                </tr>
                <tr>
                  <td><strong>Schema:</strong></td>
                  <td>{preview.schema || 'Unknown'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Summary Statistics */}
          <div className="preview-section">
            <h3>Summary Statistics</h3>
            <div className="preview-grid">
              <div className="preview-stat">
                <div className="stat-value">{summary.num_spaces}</div>
                <div className="stat-label">Spaces</div>
              </div>
              <div className="preview-stat">
                <div className="stat-value">{summary.num_doors}</div>
                <div className="stat-label">Doors</div>
              </div>
              <div className="preview-stat">
                <div className="stat-value">{summary.spaces_with_area}</div>
                <div className="stat-label">Spaces with Area</div>
              </div>
              <div className="preview-stat">
                <div className="stat-value">{summary.doors_with_width}</div>
                <div className="stat-label">Doors with Width</div>
              </div>
            </div>
          </div>

          {/* Element Counts */}
          <div className="preview-section">
            <h3>Element Types</h3>
            {Object.keys(counts).length === 0 ? (
              <p style={{ color: '#999' }}>No additional elements</p>
            ) : (
              <table className="preview-table">
                <thead>
                  <tr>
                    <th>Type</th>
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
            )}
          </div>

          {/* Per-Storey Breakdown */}
          {storeys.length > 0 && (
            <div className="preview-section">
              <h3>Per-Storey Breakdown</h3>
              <table className="preview-table">
                <thead>
                  <tr>
                    <th>Storey</th>
                    <th>Elevation</th>
                    <th>Elements</th>
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

          {/* Verification Message */}
          <div className="preview-verification">
            <CheckCircle size={20} style={{ color: '#10b981' }} />
            <p>Please verify the above information is correct before proceeding.</p>
          </div>
        </div>

        <div className="modal-footer">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
                Building Graph...
              </>
            ) : (
              <>
                <CheckCircle size={18} />
                Confirm & Build Graph
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default PreviewConfirmationModal;
