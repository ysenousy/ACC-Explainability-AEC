import React, { useState } from 'react';
import { X, ChevronDown, ChevronRight } from 'lucide-react';

function ElementDetailModal({ isOpen, onClose, element, elementType }) {
  const [expandedPsets, setExpandedPsets] = useState({});

  if (!isOpen || !element) return null;

  const togglePset = (psetName) => {
    setExpandedPsets(prev => ({
      ...prev,
      [psetName]: !prev[psetName]
    }));
  };

  const attributes = element.attributes || {};
  const propertySets = attributes.property_sets || {};
  const psetNames = Object.keys(propertySets);

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '700px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="modal-header">
          <h2>{element.name || element.id || 'Element Details'}</h2>
          <button onClick={onClose} className="close-button">
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
          {/* Basic Properties */}
          <div style={{
            marginBottom: '1.5rem',
            padding: '1rem',
            backgroundColor: '#f3f4f6',
            borderRadius: '0.375rem',
            border: '1px solid #e5e7eb'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '0.875rem', fontWeight: '600', textTransform: 'uppercase', color: '#374151' }}>
              Basic Properties
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.875rem' }}>
              {/* ID */}
              <div>
                <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>ID</span>
                <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem' }}>{element.id || '—'}</p>
              </div>

              {/* GUID */}
              {element.guid && (
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>GUID</span>
                  <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem', wordBreak: 'break-all', fontSize: '0.75rem' }}>
                    {element.guid}
                  </p>
                </div>
              )}

              {/* Name */}
              <div>
                <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>Name</span>
                <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem' }}>{element.name || '—'}</p>
              </div>

              {/* Storey ID */}
              {element.storey_id && (
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>Storey</span>
                  <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem' }}>{element.storey_id}</p>
                </div>
              )}

              {/* Type-specific properties for Spaces */}
              {elementType === 'space' && element.area_m2 !== null && (
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>Area (m²)</span>
                  <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem' }}>{element.area_m2.toFixed(2)}</p>
                </div>
              )}

              {/* Type-specific properties for Doors */}
              {elementType === 'door' && element.width_mm !== null && (
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>Width (mm)</span>
                  <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem' }}>{element.width_mm.toFixed(0)}</p>
                </div>
              )}

              {elementType === 'door' && element.height_mm !== null && (
                <div>
                  <span style={{ color: '#6b7280', fontSize: '0.75rem', fontWeight: '500', textTransform: 'uppercase' }}>Height (mm)</span>
                  <p style={{ margin: 0, color: '#111827', marginTop: '0.25rem' }}>{element.height_mm.toFixed(0)}</p>
                </div>
              )}
            </div>
          </div>

          {/* Property Sets */}
          <div>
            <h3 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '0.875rem', fontWeight: '600', textTransform: 'uppercase', color: '#374151' }}>
              Property Sets ({psetNames.length})
            </h3>

            {psetNames.length === 0 ? (
              <div style={{
                padding: '1rem',
                backgroundColor: '#f9fafb',
                borderRadius: '0.375rem',
                textAlign: 'center',
                color: '#6b7280',
                fontSize: '0.875rem'
              }}>
                No property sets available
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {psetNames.map(psetName => {
                  const psetData = propertySets[psetName] || {};
                  const propCount = Object.keys(psetData).length;
                  const isExpanded = expandedPsets[psetName];

                  return (
                    <div
                      key={psetName}
                      style={{
                        border: '1px solid #e5e7eb',
                        borderRadius: '0.375rem',
                        overflow: 'hidden'
                      }}
                    >
                      {/* Pset Header */}
                      <button
                        onClick={() => togglePset(psetName)}
                        style={{
                          width: '100%',
                          padding: '0.75rem',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          backgroundColor: '#f3f4f6',
                          border: 'none',
                          cursor: 'pointer',
                          fontWeight: '500',
                          fontSize: '0.875rem',
                          textAlign: 'left',
                          transition: 'background-color 0.2s'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#e5e7eb'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#f3f4f6'}
                      >
                        {isExpanded ? (
                          <ChevronDown size={16} />
                        ) : (
                          <ChevronRight size={16} />
                        )}
                        <span>{psetName}</span>
                        <span style={{
                          marginLeft: 'auto',
                          fontSize: '0.75rem',
                          color: '#6b7280',
                          backgroundColor: '#fff',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '0.25rem'
                        }}>
                          {propCount} {propCount === 1 ? 'property' : 'properties'}
                        </span>
                      </button>

                      {/* Pset Content */}
                      {isExpanded && (
                        <div style={{
                          padding: '1rem',
                          backgroundColor: '#fafafa',
                          borderTop: '1px solid #e5e7eb',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.5rem'
                        }}>
                          {Object.entries(psetData).map(([propName, propValue]) => (
                            <div key={propName} style={{
                              display: 'grid',
                              gridTemplateColumns: '150px 1fr',
                              gap: '0.75rem',
                              paddingBottom: '0.5rem',
                              borderBottom: '1px solid #e5e7eb',
                              fontSize: '0.875rem'
                            }}>
                              <span style={{
                                fontWeight: '500',
                                color: '#374151',
                                wordBreak: 'break-word'
                              }}>
                                {propName}
                              </span>
                              <span style={{
                                color: '#4b5563',
                                wordBreak: 'break-word',
                                fontFamily: 'monospace',
                                fontSize: '0.8125rem'
                              }}>
                                {typeof propValue === 'object' ? JSON.stringify(propValue, null, 2) : String(propValue)}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
          backgroundColor: '#f9fafb'
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#e5e7eb',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.target.style.backgroundColor = '#d1d5db'}
            onMouseLeave={(e) => e.target.style.backgroundColor = '#e5e7eb'}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default ElementDetailModal;
