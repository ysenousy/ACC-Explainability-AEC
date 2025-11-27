import React, { useState, useEffect } from 'react';
import { Upload, Save, Plus, Trash2, Edit2, ChevronDown, ChevronUp, CheckCircle, AlertCircle, Download, BarChart3 } from 'lucide-react';

const UnifiedConfigurationView = ({ graph }) => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [activeTab, setActiveTab] = useState('elements');
  const [expandedElement, setExpandedElement] = useState(null);
  const [expandedMapping, setExpandedMapping] = useState(null);
  const [availableRules, setAvailableRules] = useState([]);
  const [editingAttribute, setEditingAttribute] = useState(null);
  const [editAttributeData, setEditAttributeData] = useState(null);
  const [rulesLoadError, setRulesLoadError] = useState(null);
  
  // Modal states
  const [showAddAttribute, setShowAddAttribute] = useState(false);
  const [showAddMapping, setShowAddMapping] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);
  const [showMappingCheckModal, setShowMappingCheckModal] = useState(false);
  const [mappingCheckResults, setMappingCheckResults] = useState(null);
  const [checkingMappings, setCheckingMappings] = useState(false);
  
  // Form states
  const [newAttribute, setNewAttribute] = useState({
    name: '',
    source: 'qto',
    unit: 'mm',
    required: false
  });
  
  const [newMapping, setNewMapping] = useState({
    mapping_id: '',
    element_type: 'door',
    enabled: true,
    rule_reference: { format: 'regulation', rule_id: '' },
    attribute_extraction: { operator: '>=' }
  });

  // Load config on mount
  useEffect(() => {
    loadConfig();
    loadAvailableRules();
  }, []);

  const loadAvailableRules = async () => {
    try {
      // Load rules from backend API endpoint
      const response = await fetch('/api/rules/available');
      if (!response.ok) throw new Error('Failed to load rules');
      const data = await response.json();
      if (data.success && data.rules && Array.isArray(data.rules)) {
        setAvailableRules(data.rules);
        setSuccess('Available rules updated');
        setRulesLoadError(null);
        setTimeout(() => setSuccess(null), 2000);
      } else {
        throw new Error(data.error || 'Failed to load rules');
      }
    } catch (e) {
      console.warn('Could not load available rules:', e.message);
      setRulesLoadError('Could not load available rules');
    }
  };

  const loadConfig = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/config/load');
      const data = await response.json();
      if (data.success) {
        setConfig(data.config);
        setError(null);
      } else {
        setError('Failed to load configuration');
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const generateMappingId = (ruleId) => {
    if (!ruleId) return '';
    // Convert rule_id to mapping_id format
    // e.g., ADA_DOOR_MIN_CLEAR_WIDTH -> MAP_ADA_DOOR_MIN_CLEAR_WIDTH
    return `MAP_${ruleId}`;
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      const response = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config })
      });
      const data = await response.json();
      if (data.success) {
        setSuccess('Configuration saved successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to save configuration');
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const validateConfig = async () => {
    try {
      const response = await fetch('/api/config/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config })
      });
      const data = await response.json();
      if (data.is_valid) {
        setSuccess('Configuration is valid');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(`Validation errors: ${data.errors.join(', ')}`);
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
    }
  };

  const addAttribute = async () => {
    if (!selectedElement || !newAttribute.name) {
      setError('Element type and attribute name are required');
      return;
    }

    try {
      const response = await fetch(`/api/config/element-attributes/${selectedElement}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attribute: newAttribute })
      });
      const data = await response.json();
      if (data.success) {
        await loadConfig();
        setShowAddAttribute(false);
        setNewAttribute({ name: '', source: 'qto', unit: 'mm', required: false });
        setSuccess('Attribute added successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to add attribute');
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
    }
  };

  const deleteAttribute = async (elementType, attributeName) => {
    if (!window.confirm(`Delete attribute '${attributeName}'?`)) return;

    try {
      const response = await fetch(
        `/api/config/element-attributes/${elementType}/${attributeName}`,
        { method: 'DELETE' }
      );
      const data = await response.json();
      if (data.success) {
        await loadConfig();
        setSuccess('Attribute deleted successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to delete attribute');
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
    }
  };

  const startEditAttribute = (elementType, attribute) => {
    setEditingAttribute({ elementType, oldName: attribute.name });
    setEditAttributeData({ ...attribute });
  };

  const cancelEditAttribute = () => {
    setEditingAttribute(null);
    setEditAttributeData(null);
  };

  const saveEditAttribute = async () => {
    if (!editingAttribute || !editAttributeData) return;

    try {
      const response = await fetch(
        `/api/config/element-attributes/${editingAttribute.elementType}/${editingAttribute.oldName}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ attribute: editAttributeData })
        }
      );
      const data = await response.json();
      if (data.success) {
        await loadConfig();
        cancelEditAttribute();
        setSuccess('Attribute updated successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to update attribute');
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
    }
  };

  const addRuleMapping = async () => {
    if (!newMapping.mapping_id || !newMapping.rule_reference.rule_id) {
      setError('Mapping ID and Rule ID are required');
      setTimeout(() => setError(null), 3000);
      return;
    }

    try {
      const response = await fetch('/api/config/rule-mappings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mapping: newMapping })
      });
      const data = await response.json();
      if (data.success) {
        await loadConfig();
        setShowAddMapping(false);
        setNewMapping({
          mapping_id: '',
          element_type: 'door',
          enabled: true,
          rule_reference: { format: 'regulation', rule_id: '' },
          attribute_extraction: { operator: '>=' }
        });
        setSuccess('Rule mapping added successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to add rule mapping');
        setTimeout(() => setError(null), 3000);
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
      setTimeout(() => setError(null), 3000);
    }
  };

  const deleteRuleMapping = async (mappingId) => {
    if (!window.confirm(`Delete rule mapping '${mappingId}'?`)) return;

    try {
      const response = await fetch(`/api/config/rule-mappings/${mappingId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (data.success) {
        await loadConfig();
        setSuccess('Rule mapping deleted successfully');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to delete rule mapping');
        setTimeout(() => setError(null), 3000);
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
      setTimeout(() => setError(null), 3000);
    }
  };

  const exportConfig = () => {
    const dataStr = JSON.stringify(config, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `unified-rules-config-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleFileImport = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setError(null);
      const fileContent = await file.text();
      const importedConfig = JSON.parse(fileContent);

      // Call import endpoint
      const response = await fetch('/api/config/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: importedConfig })
      });

      const data = await response.json();
      if (data.success) {
        // Reload the config from the backend after import
        await loadConfig();
        // Reload available rules after import
        await loadAvailableRules();
        // Switch to elements tab to show imported data
        setActiveTab('elements');
        // Reset expanded state to show summary
        setExpandedElement(null);
        
        // Show success message with import summary from the newly loaded config
        setTimeout(() => {
          if (config) {
            const elementCount = Object.keys(config?.ifc_element_mappings || {}).length;
            const attributeCount = Object.values(config?.ifc_element_mappings || {}).reduce((sum, el) => sum + (el.attributes?.length || 0), 0);
            const mappingCount = (config?.rule_mappings || []).length;
            setSuccess(`Configuration imported successfully: ${elementCount} element types, ${attributeCount} attributes, ${mappingCount} mappings`);
            setTimeout(() => setSuccess(null), 4000);
          }
        }, 100);
      } else {
        setError(data.error || 'Failed to import configuration');
        setTimeout(() => setError(null), 3000);
      }
    } catch (e) {
      setError(`Error importing file: ${e.message}`);
      setTimeout(() => setError(null), 3000);
    } finally {
      // Reset file input
      event.target.value = '';
    }
  };

  const checkMappings = async () => {
    // Use the graph passed from App component
    if (!graph || !graph.elements) {
      setError('No IFC data loaded. Please load an IFC file first.');
      setTimeout(() => setError(null), 3000);
      return;
    }

    try {
      setCheckingMappings(true);
      const response = await fetch('/api/config/check-mappings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph })
      });
      const data = await response.json();
      
      if (data.success) {
        setMappingCheckResults(data);
        setShowMappingCheckModal(true);
        setSuccess('Mapping check completed');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Failed to check mappings');
        setTimeout(() => setError(null), 3000);
      }
    } catch (e) {
      setError(`Error: ${e.message}`);
      setTimeout(() => setError(null), 3000);
    } finally {
      setCheckingMappings(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <div style={{ fontSize: '1.1rem', color: '#666' }}>Loading configuration...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ margin: 0, marginBottom: '0.5rem', color: '#1f2937' }}>
          ⚙️ Rule Config
        </h2>
        <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
          Manage IFC attribute mappings and rule configurations
        </p>
      </div>

      {/* Status Messages */}
      {error && (
        <div style={{
          padding: '1rem',
          marginBottom: '1rem',
          backgroundColor: '#fee2e2',
          border: '1px solid #fca5a5',
          borderRadius: '0.375rem',
          color: '#991b1b',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div style={{
          padding: '1rem',
          marginBottom: '1rem',
          backgroundColor: '#d1fae5',
          border: '1px solid #6ee7b7',
          borderRadius: '0.375rem',
          color: '#065f46',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <CheckCircle size={20} />
          <span>{success}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '0.75rem',
        marginBottom: '2rem'
      }}>
        <button
          onClick={(e) => document.getElementById('import-file-input').click()}
          style={{
            padding: '0.75rem',
            backgroundColor: '#f59e0b',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem'
          }}
        >
          <Upload size={18} />
          Import
          <input
            id="import-file-input"
            type="file"
            accept=".json"
            onChange={handleFileImport}
            style={{ display: 'none' }}
          />
        </button>

        <button
          onClick={exportConfig}
          style={{
            padding: '0.75rem',
            backgroundColor: '#8b5cf6',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem'
          }}
        >
          <Download size={18} />
          Export
        </button>

        <button
          onClick={validateConfig}
          style={{
            padding: '0.75rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem'
          }}
        >
          <CheckCircle size={18} />
          Validate
        </button>

        <button
          onClick={saveConfig}
          disabled={saving}
          style={{
            padding: '0.75rem',
            backgroundColor: '#06b6d4',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: saving ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            opacity: saving ? 0.6 : 1
          }}
        >
          <Save size={18} />
          Save Configuration
        </button>

        <button
          onClick={checkMappings}
          disabled={checkingMappings}
          style={{
            padding: '0.75rem',
            backgroundColor: '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: checkingMappings ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            opacity: checkingMappings ? 0.6 : 1
          }}
        >
          <BarChart3 size={18} />
          Check Mappings
        </button>
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: '1px solid #e5e7eb', marginBottom: '1.5rem', display: 'flex', gap: '1rem' }}>
        <button
          onClick={() => setActiveTab('elements')}
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: activeTab === 'elements' ? '#3b82f6' : 'transparent',
            color: activeTab === 'elements' ? 'white' : '#666',
            border: 'none',
            cursor: 'pointer',
            borderBottom: activeTab === 'elements' ? '2px solid #3b82f6' : 'none'
          }}
        >
          IFC Elements & Attributes
        </button>
        <button
          onClick={() => setActiveTab('mappings')}
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: activeTab === 'mappings' ? '#3b82f6' : 'transparent',
            color: activeTab === 'mappings' ? 'white' : '#666',
            border: 'none',
            cursor: 'pointer',
            borderBottom: activeTab === 'mappings' ? '2px solid #3b82f6' : 'none'
          }}
        >
          Rule Mappings
        </button>
      </div>

      {/* IFC Elements Tab */}
      {activeTab === 'elements' && (
        <div>
          <div style={{ marginBottom: '1.5rem' }}>
            <button
              onClick={() => setShowAddAttribute(!showAddAttribute)}
              style={{
                padding: '0.75rem 1rem',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Plus size={18} />
              Add Attribute
            </button>
          </div>

          {/* Add Attribute Form */}
          {showAddAttribute && (
            <div style={{
              padding: '1.5rem',
              backgroundColor: '#f3f4f6',
              borderRadius: '0.375rem',
              marginBottom: '2rem',
              border: '1px solid #e5e7eb'
            }}>
              <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Add New Attribute</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Element Type
                  </label>
                  <select
                    value={selectedElement || ''}
                    onChange={(e) => setSelectedElement(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontFamily: 'inherit'
                    }}
                  >
                    <option value="">Select Element Type</option>
                    {config?.ifc_element_mappings && Object.keys(config.ifc_element_mappings).map(et => (
                      <option key={et} value={et}>{et}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Attribute Name
                  </label>
                  <input
                    type="text"
                    value={newAttribute.name}
                    onChange={(e) => setNewAttribute({ ...newAttribute, name: e.target.value })}
                    placeholder="e.g., width_mm"
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Source
                  </label>
                  <select
                    value={newAttribute.source}
                    onChange={(e) => setNewAttribute({ ...newAttribute, source: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontFamily: 'inherit'
                    }}
                  >
                    <option value="qto">QTO (Quantity)</option>
                    <option value="pset">PSet (Property)</option>
                    <option value="element">Element</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Unit
                  </label>
                  <input
                    type="text"
                    value={newAttribute.unit}
                    onChange={(e) => setNewAttribute({ ...newAttribute, unit: e.target.value })}
                    placeholder="e.g., mm"
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={newAttribute.required}
                      onChange={(e) => setNewAttribute({ ...newAttribute, required: e.target.checked })}
                    />
                    <span>Required</span>
                  </label>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  onClick={addAttribute}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer'
                  }}
                >
                  Add Attribute
                </button>
                <button
                  onClick={() => setShowAddAttribute(false)}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#e5e7eb',
                    color: '#1f2937',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Elements List */}
          {config?.ifc_element_mappings && Object.entries(config.ifc_element_mappings).map(([elementType, elementConfig]) => (
            <div key={elementType} style={{
              marginBottom: '1.5rem',
              border: '1px solid #e5e7eb',
              borderRadius: '0.375rem',
              overflow: 'hidden'
            }}>
              <button
                onClick={() => setExpandedElement(expandedElement === elementType ? null : elementType)}
                style={{
                  width: '100%',
                  padding: '1rem',
                  backgroundColor: '#f9fafb',
                  border: 'none',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontWeight: '600'
                }}
              >
                <span>{elementType} ({elementConfig.attributes?.length || 0} attributes)</span>
                {expandedElement === elementType ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>

              {expandedElement === elementType && (
                <div style={{ padding: '1rem' }}>
                  {elementConfig.attributes?.map((attr) => (
                    <div key={attr.name} style={{
                      padding: '0.75rem',
                      marginBottom: '0.75rem',
                      backgroundColor: '#f3f4f6',
                      borderRadius: '0.375rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div>
                        <strong style={{ display: 'block', marginBottom: '0.25rem' }}>{attr.name}</strong>
                        <small style={{ color: '#666' }}>
                          Source: {attr.source} | Unit: {attr.unit} | Required: {attr.required ? 'Yes' : 'No'}
                        </small>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          onClick={() => startEditAttribute(elementType, attr)}
                          style={{
                            padding: '0.5rem',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.375rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                        >
                          <Edit2 size={16} />
                        </button>
                        <button
                          onClick={() => deleteAttribute(elementType, attr.name)}
                          style={{
                            padding: '0.5rem',
                            backgroundColor: '#ef4444',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.375rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem'
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Edit Attribute Modal */}
      {editingAttribute && editAttributeData && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '2rem',
            borderRadius: '0.5rem',
            maxWidth: '500px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Edit Attribute</h3>
            
            <div style={{ display: 'grid', gap: '1rem', marginBottom: '1.5rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                  Attribute Name
                </label>
                <input
                  type="text"
                  value={editAttributeData.name}
                  onChange={(e) => setEditAttributeData({ ...editAttributeData, name: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                  Source
                </label>
                <select
                  value={editAttributeData.source}
                  onChange={(e) => setEditAttributeData({ ...editAttributeData, source: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem',
                    fontFamily: 'inherit'
                  }}
                >
                  <option value="qto">QTO (Quantity)</option>
                  <option value="pset">PSet (Property)</option>
                  <option value="element">Element</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                  Unit
                </label>
                <input
                  type="text"
                  value={editAttributeData.unit || ''}
                  onChange={(e) => setEditAttributeData({ ...editAttributeData, unit: e.target.value })}
                  placeholder="e.g., mm"
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.375rem'
                  }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="checkbox"
                  id="edit-required"
                  checked={editAttributeData.required || false}
                  onChange={(e) => setEditAttributeData({ ...editAttributeData, required: e.target.checked })}
                />
                <label htmlFor="edit-required" style={{ cursor: 'pointer' }}>Required</label>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={cancelEditAttribute}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                onClick={saveEditAttribute}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer'
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rule Mappings Tab */}
      {activeTab === 'mappings' && (
        <div>
          {rulesLoadError && (
            <div style={{
              padding: '1rem',
              marginBottom: '1rem',
              backgroundColor: '#fee2e2',
              border: '1px solid #fca5a5',
              borderRadius: '0.375rem',
              color: '#991b1b',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem'
            }}>
              <AlertCircle size={20} />
              <span>{rulesLoadError}</span>
            </div>
          )}

          <div style={{ marginBottom: '1.5rem' }}>
            <button
              onClick={() => setShowAddMapping(!showAddMapping)}
              style={{
                padding: '0.75rem 1rem',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Plus size={18} />
              Add Rule Mapping
            </button>
          </div>

          {/* Add Rule Mapping Form */}
          {showAddMapping && (
            <div style={{
              padding: '1.5rem',
              backgroundColor: '#f3f4f6',
              borderRadius: '0.375rem',
              marginBottom: '2rem',
              border: '1px solid #e5e7eb'
            }}>
              <h3 style={{ marginTop: 0, marginBottom: '1rem' }}>Add New Rule Mapping</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Mapping ID (Auto-generated)
                  </label>
                  <input
                    type="text"
                    value={newMapping.mapping_id}
                    readOnly
                    placeholder="Will be generated from Rule ID"
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      backgroundColor: '#f0f0f0',
                      color: '#666',
                      cursor: 'not-allowed'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Element Type
                  </label>
                  <select
                    value={newMapping.element_type}
                    onChange={(e) => setNewMapping({ ...newMapping, element_type: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      border: '1px solid #d1d5db',
                      borderRadius: '0.375rem',
                      fontFamily: 'inherit'
                    }}
                  >
                    {config?.ifc_element_mappings && Object.keys(config.ifc_element_mappings).map(et => (
                      <option key={et} value={et}>{et}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', fontSize: '0.9rem' }}>
                    Rule ID
                  </label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <select
                      value={newMapping.rule_reference.rule_id}
                      onChange={(e) => {
                        const selectedRuleId = e.target.value;
                        setNewMapping({
                          ...newMapping,
                          mapping_id: generateMappingId(selectedRuleId),
                          rule_reference: { ...newMapping.rule_reference, rule_id: selectedRuleId }
                        });
                      }}
                      style={{
                        flex: 1,
                        padding: '0.5rem',
                        border: '1px solid #d1d5db',
                        borderRadius: '0.375rem',
                        fontFamily: 'inherit'
                      }}
                    >
                      <option value="">Select a Rule ID</option>
                      {availableRules.map(rule => (
                        <option key={rule.id} value={rule.id}>
                          {rule.id} - {rule.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={loadAvailableRules}
                      title="Refresh available rules"
                      style={{
                        padding: '0.5rem 0.75rem',
                        backgroundColor: '#6366f1',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.375rem',
                        cursor: 'pointer',
                        fontSize: '0.85rem'
                      }}
                    >
                      ↻
                    </button>
                  </div>
                  {newMapping.rule_reference.rule_id && availableRules.find(r => r.id === newMapping.rule_reference.rule_id) && (
                    <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.85rem', color: '#666' }}>
                      {availableRules.find(r => r.id === newMapping.rule_reference.rule_id)?.description}
                    </p>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <button
                  onClick={addRuleMapping}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer'
                  }}
                >
                  Add Mapping
                </button>
                <button
                  onClick={() => setShowAddMapping(false)}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#e5e7eb',
                    color: '#1f2937',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Rule Mappings List */}
          {config?.rule_mappings && config.rule_mappings.map((mapping) => (
            <div key={mapping.mapping_id} style={{
              marginBottom: '1.5rem',
              border: '1px solid #e5e7eb',
              borderRadius: '0.375rem',
              overflow: 'hidden'
            }}>
              <button
                onClick={() => setExpandedMapping(expandedMapping === mapping.mapping_id ? null : mapping.mapping_id)}
                style={{
                  width: '100%',
                  padding: '1rem',
                  backgroundColor: mapping.enabled ? '#f0f9ff' : '#f3f4f6',
                  border: 'none',
                  textAlign: 'left',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderLeft: `4px solid ${mapping.enabled ? '#3b82f6' : '#d1d5db'}`
                }}
              >
                <div>
                  <strong>{mapping.mapping_id}</strong>
                  <small style={{ display: 'block', color: '#666', marginTop: '0.25rem' }}>
                    {mapping.element_type} → {mapping.rule_reference?.rule_id}
                  </small>
                </div>
                {expandedMapping === mapping.mapping_id ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </button>

              {expandedMapping === mapping.mapping_id && (
                <div style={{ padding: '1rem', backgroundColor: '#f9fafb', borderTop: '1px solid #e5e7eb' }}>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={mapping.enabled}
                        onChange={(e) => {
                          const updated = { ...mapping, enabled: e.target.checked };
                          setConfig({
                            ...config,
                            rule_mappings: config.rule_mappings.map(m =>
                              m.mapping_id === mapping.mapping_id ? updated : m
                            )
                          });
                        }}
                      />
                      <span>Enabled</span>
                    </label>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '1rem' }}>
                    <strong>Details:</strong>
                    <pre style={{
                      backgroundColor: 'white',
                      padding: '0.75rem',
                      borderRadius: '0.375rem',
                      overflow: 'auto',
                      border: '1px solid #e5e7eb'
                    }}>
                      {JSON.stringify({
                        rule_id: mapping.rule_reference?.rule_id,
                        format: mapping.rule_reference?.format,
                        operator: mapping.attribute_extraction?.operator
                      }, null, 2)}
                    </pre>
                  </div>

                  <button
                    onClick={() => deleteRuleMapping(mapping.mapping_id)}
                    style={{
                      padding: '0.5rem 1rem',
                      backgroundColor: '#ef4444',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <Trash2 size={16} />
                    Delete Mapping
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Mapping Check Modal */}
      {showMappingCheckModal && mappingCheckResults && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: '0.5rem',
            padding: '2rem',
            maxWidth: '700px',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 20px 25px rgba(0, 0, 0, 0.15)',
            fontFamily: 'system-ui, -apple-system, sans-serif'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0, color: '#1f2937', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <BarChart3 size={24} />
                Mapping Coverage Analysis
              </h3>
              <button
                onClick={() => setShowMappingCheckModal(false)}
                style={{
                  backgroundColor: 'transparent',
                  border: 'none',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  color: '#666'
                }}
              >
                ×
              </button>
            </div>

            {/* Summary Section */}
            <div style={{
              backgroundColor: '#f3f4f6',
              padding: '1.5rem',
              borderRadius: '0.375rem',
              marginBottom: '1.5rem'
            }}>
              <h4 style={{ margin: '0 0 1rem 0', color: '#374151' }}>Summary</h4>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Total IFC Elements</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#3b82f6' }}>
                    {mappingCheckResults.summary.total_elements}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Elements with Mappings</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#10b981' }}>
                    {mappingCheckResults.summary.mapped_elements}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Active Mappings</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#8b5cf6' }}>
                    {mappingCheckResults.summary.total_mappings}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.25rem' }}>Coverage</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#f59e0b' }}>
                    {mappingCheckResults.summary.coverage_percentage}%
                  </div>
                </div>
              </div>
            </div>

            {/* Elements by Type */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ margin: '0 0 1rem 0', color: '#374151' }}>Elements by Type</h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '1rem'
              }}>
                {Object.entries(mappingCheckResults.summary.elements_by_type).map(([type, count]) => (
                  <div key={type} style={{
                    padding: '1rem',
                    backgroundColor: '#f9fafb',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.375rem',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '0.875rem', color: '#666', marginBottom: '0.5rem', textTransform: 'capitalize' }}>
                      {type}
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#1f2937' }}>
                      {count}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Mapping Details */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h4 style={{ margin: '0 0 1rem 0', color: '#374151' }}>Mapping Details</h4>
              <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                {Object.entries(mappingCheckResults.mappings).map(([mappingId, mapping]) => (
                  <div key={mappingId} style={{
                    padding: '1rem',
                    marginBottom: '0.75rem',
                    backgroundColor: mapping.elements_in_ifc > 0 ? '#dbeafe' : '#f3f4f6',
                    border: `1px solid ${mapping.elements_in_ifc > 0 ? '#93c5fd' : '#e5e7eb'}`,
                    borderRadius: '0.375rem'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <div>
                        <div style={{ fontWeight: 'bold', color: '#1f2937' }}>{mapping.mapping_id}</div>
                        <div style={{ fontSize: '0.875rem', color: '#666' }}>Rule: {mapping.rule_id}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: mapping.elements_in_ifc > 0 ? '#3b82f6' : '#9ca3af' }}>
                          {mapping.elements_in_ifc}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#666' }}>
                          {mapping.element_type}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Close Button */}
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                onClick={() => setShowMappingCheckModal(false)}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '500'
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedConfigurationView;
