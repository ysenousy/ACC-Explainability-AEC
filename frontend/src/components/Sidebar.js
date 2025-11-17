import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Database, CheckCircle, Zap, Network, FileText, AlertCircle } from 'lucide-react';

function Sidebar({ currentGraph, onLayerSelect, activeLayer }) {
  const [expandedGroups, setExpandedGroups] = useState({
    model: true,
    compliance: true,
  });

  const toggleGroup = (group) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  const layers = {
    model: [
      { id: 'data-layer', label: 'Data Layer', icon: Database, description: 'IFC structure & elements' },
      { id: 'elements', label: 'Elements', icon: FileText, description: 'Spaces & Doors' },
    ],
    compliance: [
      { id: 'rule-layer', label: 'Rule Layer', icon: CheckCircle, description: 'Compliance rules' },
      { id: 'reasoning', label: 'Reasoning', icon: Zap, description: 'Rule logic & inference' },
      { id: 'results', label: 'Results', icon: AlertCircle, description: 'Rule evaluation outcomes' },
    ],
  };

  const groups = [
    { key: 'model', label: '📊 Model', color: 'sidebar-model' },
    { key: 'compliance', label: '✅ Compliance', color: 'sidebar-compliance' },
  ];

  const handleLayerClick = (layerId) => {
    onLayerSelect(layerId);
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Layers</h2>
      </div>

      <nav className="sidebar-nav">
        {groups.map((group) => (
          <div key={group.key} className={`sidebar-group ${group.color}`}>
            {/* Group Header */}
            <button
              className="sidebar-group-header"
              onClick={() => toggleGroup(group.key)}
            >
              {expandedGroups[group.key] ? (
                <ChevronDown size={18} />
              ) : (
                <ChevronRight size={18} />
              )}
              <span className="group-label">{group.label}</span>
            </button>

            {/* Group Items */}
            {expandedGroups[group.key] && (
              <div className="sidebar-items">
                {layers[group.key].map((layer) => {
                  const Icon = layer.icon;
                  const isActive = activeLayer === layer.id;
                  return (
                    <button
                      key={layer.id}
                      className={`sidebar-item ${isActive ? 'active' : ''}`}
                      onClick={() => handleLayerClick(layer.id)}
                      title={layer.description}
                    >
                      <Icon size={16} className="sidebar-item-icon" />
                      <span className="sidebar-item-label">{layer.label}</span>
                      {isActive && <div className="sidebar-item-indicator" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer Info */}
      {currentGraph && (
        <div className="sidebar-footer">
          <div className="sidebar-info">
            <p className="info-label">Loaded:</p>
            <p className="info-value">{currentGraph.building_id || 'Unknown'}</p>
          </div>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
