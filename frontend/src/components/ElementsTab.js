import React, { useState } from 'react';
import { Filter } from 'lucide-react';

function ElementsTab({ graph }) {
  const [filterType, setFilterType] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const elements = graph?.elements || {};
  const spaces = elements.spaces || [];
  const doors = elements.doors || [];

  let filteredItems = [];

  if (filterType === 'all' || filterType === 'spaces') {
    filteredItems = [
      ...spaces
        .filter((s) =>
          !searchTerm ||
          s.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          s.id?.toLowerCase().includes(searchTerm.toLowerCase())
        )
        .map((s) => ({ ...s, type: 'space' })),
    ];
  }

  if (filterType === 'all' || filterType === 'doors') {
    filteredItems = [
      ...filteredItems,
      ...doors
        .filter((d) =>
          !searchTerm ||
          d.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          d.id?.toLowerCase().includes(searchTerm.toLowerCase())
        )
        .map((d) => ({ ...d, type: 'door' })),
    ];
  }

  return (
    <div className="elements-tab">
      {/* Filters */}
      <div style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <div className="form-group">
            <label>Filter by Type</label>
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="all">All Elements</option>
              <option value="spaces">Spaces Only</option>
              <option value="doors">Doors Only</option>
            </select>
          </div>
          <div className="form-group">
            <label>Search</label>
            <input
              type="text"
              placeholder="Search by ID or name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div style={{ marginBottom: '1rem', color: '#666' }}>
        Found <strong>{filteredItems.length}</strong> element(s)
      </div>

      {/* Table */}
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>ID</th>
              <th>Name</th>
              <th>Width / Area</th>
              <th>Connections</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => (
              <tr key={`${item.type}-${item.id}`}>
                <td>
                  <span className={`badge badge-${item.type === 'space' ? 'success' : 'info'}`}>
                    {item.type}
                  </span>
                </td>
                <td style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>
                  {item.id}
                </td>
                <td>{item.name || '—'}</td>
                <td>
                  {item.type === 'space'
                    ? item.area_m2
                      ? `${item.area_m2.toFixed(2)} m²`
                      : '—'
                    : item.width_mm
                    ? `${item.width_mm.toFixed(1)} mm`
                    : '—'}
                </td>
                <td>
                  {item.type === 'door'
                    ? item.connected_spaces?.length || 0
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filteredItems.length === 0 && (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#999' }}>
          <p>No elements found matching your criteria</p>
        </div>
      )}
    </div>
  );
}

export default ElementsTab;
