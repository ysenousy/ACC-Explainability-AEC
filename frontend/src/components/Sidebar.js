import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Database, CheckCircle, Zap, Network, FileText, AlertCircle, Download, BarChart3 } from 'lucide-react';

function Sidebar({ currentGraph, onLayerSelect, activeLayer }) {
  const [expandedGroups, setExpandedGroups] = useState({
    dataLayer: true,
    ruleLayer: true,
    reasoningLayer: true,
  });

  const toggleGroup = (group) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  const layers = {
    dataLayer: [
      { id: 'data-layer', label: 'Model Summary', icon: Database, description: 'IFC structure & elements' },
      { id: 'elements', label: 'Model Elements', icon: FileText, description: 'Spaces & Doors' },
      { id: 'validation', label: 'Data Validation', icon: CheckCircle, description: 'Validate IFC data properties' },
      { id: 'export', label: 'Export JSON Graph', icon: Download, description: 'Export JSON graph' },
    ],
    ruleLayer: [
      { id: 'rule-layer', label: 'Regulatory Rules', icon: CheckCircle, description: 'Compliance rules' },
      { id: 'rule-generate', label: 'Generate Rule', icon: Zap, description: 'Generate new rules' },
      { id: 'rule-check', label: 'Check Compliance', icon: CheckCircle, description: 'Check IFC compliance against rules' },
      { id: 'compliance-report', label: 'Compliance Report', icon: FileText, description: 'Generate comprehensive compliance report' },
    ],
    reasoningLayer: [
      { id: 'reasoning', label: 'Reasoning Layer', icon: Network, description: 'Rule justifications & failure analysis' },
      { id: 'results', label: 'Analysis Results', icon: AlertCircle, description: 'Rule evaluation outcomes' },
    ],
  };

  const groups = [
    { key: 'dataLayer', label: '📊 Data Layer', color: 'sidebar-model' },
    { key: 'ruleLayer', label: '✅ Rules Layer', color: 'sidebar-compliance' },
    { key: 'reasoningLayer', label: '🧠 Reasoning Layer', color: 'sidebar-reasoning' },
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
    </aside>
  );
}

export default Sidebar;
