import React, { useState, useMemo } from 'react';
import { FileText, Eye } from 'lucide-react';
import ElementDetailModal from './ElementDetailModal';

function ElementsView({ graph }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [elementType, setElementType] = useState('all');
  const [selectedElement, setSelectedElement] = useState(null);
  const [selectedElementType, setSelectedElementType] = useState(null);
  const [showDetailModal, setShowDetailModal] = useState(false);

  const elements = graph?.elements || {};

  // Get all available element types sorted
  const elementTypes = useMemo(() => {
    return Object.keys(elements)
      .filter(type => elements[type] && elements[type].length > 0)
      .sort();
  }, [elements]);

  // Get filtered elements with their type info
  const filteredElements = useMemo(() => {
    const searchLower = searchTerm.toLowerCase();
    const all = [];

    if (elementType === 'all') {
      // Include all element types
      Object.entries(elements).forEach(([type, items]) => {
        if (Array.isArray(items)) {
          items.forEach(item => {
            all.push({ ...item, _type: type });
          });
        }
      });
    } else {
      // Include only selected type
      const items = elements[elementType] || [];
      if (Array.isArray(items)) {
        items.forEach(item => {
          all.push({ ...item, _type: elementType });
        });
      }
    }

    // Filter by search term
    return all.filter(e =>
      (e.id || '').toLowerCase().includes(searchLower) ||
      (e.name || '').toLowerCase().includes(searchLower) ||
      (e.ifc_type || '').toLowerCase().includes(searchLower)
    );
  }, [elements, elementType, searchTerm]);

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  return (
    <div className="layer-view">
      <div className="layer-header">
        <FileText size={24} />
        <h2>Model Elements</h2>
      </div>

      <div className="layer-content">
        {/* Search & Filter */}
        <div className="search-section">
          <input
            type="text"
            placeholder="Search by ID, name, or type..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <select
            value={elementType}
            onChange={(e) => setElementType(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Elements</option>
            {elementTypes.map((type) => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Display all element types */}
        {elementType === 'all' ? (
          elementTypes.map((type) => {
            const typeElements = elements[type] || [];
            const typeFiltered = typeElements.filter(e =>
              (e.id || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
              (e.name || '').toLowerCase().includes(searchTerm.toLowerCase())
            );

            if (typeFiltered.length === 0) return null;

            return (
              <div key={type} className="elements-section">
                <h3>{type.charAt(0).toUpperCase() + type.slice(1)} ({typeFiltered.length})</h3>
                <table className="elements-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      {type === 'spaces' && <th>Area (m²)</th>}
                      {type === 'doors' && <th>Width (mm)</th>}
                      {type === 'doors' && <th>Height (mm)</th>}
                      {type !== 'spaces' && type !== 'doors' && <th>IFC Type</th>}
                      {type === 'spaces' || type === 'doors' ? <th>Storey</th> : <th>Properties</th>}
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {typeFiltered.map((item) => (
                      <tr key={item.id || item.ifc_guid}>
                        <td>{item.id || '—'}</td>
                        <td>{item.name || '—'}</td>
                        {type === 'spaces' && <td>{item.area_m2 !== null ? item.area_m2.toFixed(2) : '—'}</td>}
                        {type === 'doors' && <td>{item.width_mm !== null ? item.width_mm.toFixed(0) : '—'}</td>}
                        {type === 'doors' && <td>{item.height_mm !== null ? item.height_mm.toFixed(0) : '—'}</td>}
                        {type !== 'spaces' && type !== 'doors' && <td>{item.ifc_type || '—'}</td>}
                        {type === 'spaces' || type === 'doors' ? (
                          <td>{item.storey_id || item.storey || '—'}</td>
                        ) : (
                          <td style={{ fontSize: '0.85rem' }}>
                            {Object.keys(item.attributes || {}).length > 0 ? 'Has data' : 'Basic'}
                          </td>
                        )}
                        <td style={{ textAlign: 'center' }}>
                          <button
                            onClick={() => {
                              setSelectedElement(item);
                              setSelectedElementType(type);
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
              </div>
            );
          })
        ) : (
          <div className="elements-section">
            <h3>{elementType.charAt(0).toUpperCase() + elementType.slice(1)} ({filteredElements.length})</h3>
            {filteredElements.length === 0 ? (
              <p style={{ color: '#999' }}>No {elementType} found</p>
            ) : (
              <table className="elements-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    {elementType === 'spaces' && <th>Area (m²)</th>}
                    {elementType === 'doors' && <th>Width (mm)</th>}
                    {elementType === 'doors' && <th>Height (mm)</th>}
                    {elementType !== 'spaces' && elementType !== 'doors' && <th>IFC Type</th>}
                    {elementType === 'spaces' || elementType === 'doors' ? <th>Storey</th> : <th>Properties</th>}
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredElements.map((item) => (
                    <tr key={item.id || item.ifc_guid}>
                      <td>{item.id || '—'}</td>
                      <td>{item.name || '—'}</td>
                      {elementType === 'spaces' && <td>{item.area_m2 !== null ? item.area_m2.toFixed(2) : '—'}</td>}
                      {elementType === 'doors' && <td>{item.width_mm !== null ? item.width_mm.toFixed(0) : '—'}</td>}
                      {elementType === 'doors' && <td>{item.height_mm !== null ? item.height_mm.toFixed(0) : '—'}</td>}
                      {elementType !== 'spaces' && elementType !== 'doors' && <td>{item.ifc_type || '—'}</td>}
                      {elementType === 'spaces' || elementType === 'doors' ? (
                        <td>{item.storey_id || item.storey || '—'}</td>
                      ) : (
                        <td style={{ fontSize: '0.85rem' }}>
                          {Object.keys(item.attributes || {}).length > 0 ? 'Has data' : 'Basic'}
                        </td>
                      )}
                      <td style={{ textAlign: 'center' }}>
                        <button
                          onClick={() => {
                            setSelectedElement(item);
                            setSelectedElementType(elementType);
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
