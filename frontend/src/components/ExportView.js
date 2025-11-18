import React, { useState } from 'react';
import { Download, Copy, CheckCircle } from 'lucide-react';

function ExportView({ graph }) {
  const [copied, setCopied] = useState(false);

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const handleDownloadJSON = () => {
    const jsonString = JSON.stringify(graph, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    // Extract filename from source_file path
    const sourceFile = graph.source_file || graph.building_id || 'graph';
    const fileName = sourceFile.split('\\').pop().split('/').pop().replace('.ifc', '') || 'graph';
    link.download = `${fileName}_dataLayer.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyToClipboard = () => {
    const jsonString = JSON.stringify(graph, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const jsonString = JSON.stringify(graph, null, 2);
  const fileSizeKB = (new Blob([jsonString]).size / 1024).toFixed(2);

  return (
    <div className="layer-view">
      <div className="layer-header">
        <Download size={24} />
        <h2>Export Data Layer</h2>
      </div>

      <div className="layer-content">
        {/* Export Info */}
        <div className="info-section">
          <h3>JSON Graph Export</h3>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Export the extracted IFC data as a structured JSON graph for use in the Rule Layer or external processing.
          </p>
          <table className="info-table">
            <tbody>
              <tr>
                <td><strong>Source File:</strong></td>
                <td style={{ wordBreak: 'break-all' }}>{graph.source_file || 'Unknown'}</td>
              </tr>
              <tr>
                <td><strong>File Size:</strong></td>
                <td>{fileSizeKB} KB</td>
              </tr>
              <tr>
                <td><strong>Generated:</strong></td>
                <td>{new Date(graph.generated_at).toLocaleString()}</td>
              </tr>
              <tr>
                <td><strong>Elements:</strong></td>
                <td>
                  {Object.entries(graph.elements || {})
                    .map(([type, items]) => `${type}: ${Array.isArray(items) ? items.length : 0}`)
                    .join(', ')}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Export Actions */}
        <div className="info-section">
          <h3>Export Options</h3>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <button
              onClick={handleDownloadJSON}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Download size={18} />
              Download JSON
            </button>
            <button
              onClick={handleCopyToClipboard}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                background: copied ? '#10b981' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              {copied ? (
                <>
                  <CheckCircle size={18} />
                  Copied!
                </>
              ) : (
                <>
                  <Copy size={18} />
                  Copy to Clipboard
                </>
              )}
            </button>
          </div>
        </div>

        {/* JSON Preview */}
        <div className="info-section">
          <h3>JSON Preview</h3>
          <pre
            style={{
              background: '#f5f5f5',
              padding: '1rem',
              borderRadius: '6px',
              overflow: 'auto',
              maxHeight: '400px',
              fontSize: '0.85rem',
              lineHeight: '1.5',
              border: '1px solid #ddd'
            }}
          >
            {jsonString}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default ExportView;
