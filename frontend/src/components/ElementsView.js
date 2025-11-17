import React, { useState } from 'react';
import { FileText, Eye } from 'lucide-react';
import ElementDetailModal from './ElementDetailModal';

function ElementsView({ graph }) {
  // All hooks at the top
  const [searchTerm, setSearchTerm] = useState('');
  const [elementType, setElementType] = useState('all');

  const [selectedElement, setSelectedElement] = useState(null);
  const [selectedElementType, setSelectedElementType] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  // Early return for empty graph
  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const elements = graph.elements || {};
  const spaces = elements.spaces || [];
  const doors = elements.doors || [];

  const filteredSpaces = spaces.filter((s) =>
    (s.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (s.name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  const filteredDoors = doors.filter((d) =>
    (d.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (d.name || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="layer-view">
      <div className="layer-header">
        <FileText size={24} />
        <h2>Elements</h2>
      </div>

      <div className="layer-content">
        {/* Search & Filter */}
        <div className="search-section">
          <input
            type="text"
            placeholder="Search by ID or name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select value={elementType} onChange={(e) => setElementType(e.target.value)} className="filter-select">
            <option value="all">All Elements</option>
            <option value="spaces">Spaces Only</option>
            <option value="doors">Doors Only</option>
          </select>
        </div>

        {/* Spaces */}
        {(elementType === 'all' || elementType === 'spaces') && (
          <div className="elements-section">
            <h3>Spaces ({filteredSpaces.length})</h3>
            {filteredSpaces.length === 0 ? (
              <p style={{ color: '#999' }}>No spaces found</p>
            ) : (
              <table className="elements-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Area (m²)</th>
                    <th>Storey</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSpaces.map((space) => (
                    <tr key={space.guid} style={{ cursor: 'pointer' }}>
                      <td>{space.id || '—'}</td>
                      <td>{space.name || '—'}</td>
                      <td>{space.area_m2 !== null ? space.area_m2.toFixed(2) : '—'}</td>
                      <td>{space.storey_id || '—'}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          onClick={() => {
                            setSelectedElement(space);
                            setSelectedElementType('space');
                            setShowDetailModal(true);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.25rem',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                        >
                          <Eye size={12} />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Doors */}
        {(elementType === 'all' || elementType === 'doors') && (
          <div className="elements-section">
            <h3>Doors ({filteredDoors.length})</h3>
            {filteredDoors.length === 0 ? (
              <p style={{ color: '#999' }}>No doors found</p>
            ) : (
              <table className="elements-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Width (mm)</th>
                    <th>Height (mm)</th>
                    <th>Storey</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDoors.map((door) => (
                    <tr key={door.guid} style={{ cursor: 'pointer' }}>
                      <td>{door.id || '—'}</td>
                      <td>{door.name || '—'}</td>
                      <td>{door.width_mm !== null ? door.width_mm.toFixed(0) : '—'}</td>
                      <td>{door.height_mm !== null ? door.height_mm.toFixed(0) : '—'}</td>
                      <td>{door.storey_id || '—'}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          onClick={() => {
                            setSelectedElement(door);
                            setSelectedElementType('door');
                            setShowDetailModal(true);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.25rem',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                        >
                          <Eye size={12} />
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <ElementDetailModal
        isOpen={showDetailModal}
        onClose={() => {
          setShowDetailModal(false);
          setSelectedElement(null);
        }}
        element={selectedElement}
        elementType={selectedElementType}
      />
    </div>
  );
}

export default ElementsView;
