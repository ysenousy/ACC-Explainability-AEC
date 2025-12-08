import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Database, CheckCircle, Network, FileText, AlertCircle, Download, BarChart3, Settings } from 'lucide-react';

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
      { id: 'model-visualization', label: 'Model Visualization', icon: Network, description: '3D model viewer' },
      { id: 'validation', label: 'Model Validation', icon: CheckCircle, description: 'Validate IFC model properties' },
      { id: 'export', label: 'Export JSON Graph', icon: Download, description: 'Export JSON graph' },
    ],
    ruleLayer: [
      { id: 'rule-layer', label: 'Regulatory Rules', icon: CheckCircle, description: 'Compliance rules' },
      { id: 'rule-config', label: 'Rule Config', icon: Settings, description: 'Manage unified rule configuration' },
      { id: 'rule-check', label: 'Check Compliance', icon: CheckCircle, description: 'Check IFC compliance against rules' },
      { id: 'compliance-report', label: 'Compliance Report', icon: FileText, description: 'Generate comprehensive compliance report' },
    ],
    reasoningLayer: [
      { id: 'reasoning-why', label: 'Why It Failed', icon: AlertCircle, description: 'Explains compliance failures with context' },
      { id: 'reasoning-impact', label: 'Impact Assessment', icon: BarChart3, description: 'Quantifies scope and severity of failures' },
      { id: 'reasoning-fix', label: 'How To Fix', icon: Settings, description: 'Provides tiered recommendations' },
      { id: 'trm-model', label: 'TRM Model Management', icon: Settings, description: 'Manage model versions and training history' },
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
