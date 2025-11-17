import React, { useState } from 'react';
import { X, FileUp } from 'lucide-react';

function FileUploadModal({ onFileSelected, onClose }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) {
      alert('Please select an .ifc file');
      return;
    }

    setLoading(true);
    onFileSelected(file);
  };

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title">Select IFC File</h2>
          <button className="modal-close" onClick={onClose}>
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-content">
            <div className="form-group">
              <label>Choose IFC File</label>
              <input
                type="file"
                accept=".ifc"
                onChange={(e) => setFile(e.target.files && e.target.files[0])}
                disabled={loading}
              />
              <p style={{ fontSize: '0.85rem', color: '#999', marginTop: '0.5rem' }}>
                Use the native file picker to select an `.ifc` file from your machine.
              </p>
            </div>

            <div style={{ marginBottom: '1.5rem' }}>
              <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.5rem' }}>
                <strong>Tip:</strong> Choose the IFC file from your local disk.
              </p>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              <FileUp size={18} />
              {loading ? 'Uploading...' : 'Upload & Load'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default FileUploadModal;
