import React, { useState, useEffect, useRef } from 'react';
import { X, ChevronDown, ChevronRight, AlertCircle, AlertTriangle, Info, Upload, Edit2, Save, XCircle, Trash2, Download } from 'lucide-react';

function RuleCatalogueModal({ isOpen, onClose, onConfirmRules, refreshTrigger }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRules, setExpandedRules] = useState({});
  const [importLoading, setImportLoading] = useState(false);
  const [importMessage, setImportMessage] = useState(null);
  const [importMessageType, setImportMessageType] = useState(null);
  const [editingRuleId, setEditingRuleId] = useState(null);
  const [editFormData, setEditFormData] = useState({});
  const [deletingRuleId, setDeletingRuleId] = useState(null);
  const [appendMode, setAppendMode] = useState(false);
  const [selectedRuleIds, setSelectedRuleIds] = useState(new Set());
  const fileInputRef = useRef(null);
  const appendFileInputRef = useRef(null);

  // Fetch rules catalogue on mount or when modal opens or when rules are refreshed
  useEffect(() => {
    if (!isOpen) return;

    const fetchRules = async () => {
      setLoading(true);
      setError(null);
      setSelectedRuleIds(new Set()); // Reset selection when modal opens
      setEditingRuleId(null); // Cancel any editing in progress
      setSearchTerm(''); // Clear search
      try {
        const response = await fetch('/api/rules/catalogue');
        const data = await response.json();
        if (data.success) {
          setRules(data.rules || []);
        } else {
          setError(data.error || 'Failed to fetch rules');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchRules();
  }, [isOpen, refreshTrigger]);

  const toggleExpanded = (ruleId) => {
    setExpandedRules(prev => ({
      ...prev,
      [ruleId]: !prev[ruleId]
    }));
  };

  const handleImportCatalogue = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportLoading(true);
    setImportMessage(null);
    setAppendMode(false);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('mode', 'replace'); // Fresh import replaces current rules
      
      const response = await fetch('/api/rules/import-catalogue', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      if (data.success) {
        setImportMessage(`✓ Successfully imported ${data.status?.added || 0} rules`);
        setImportMessageType('success');
        const catalogueResponse = await fetch('/api/rules/catalogue');
        const catalogueData = await catalogueResponse.json();
        if (catalogueData.success) {
          setRules(catalogueData.rules || []);
          
          // Trigger mapping sync after catalogue change
          try {
            const syncResponse = await fetch('/api/rules/sync/on-catalogue-update', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                action: 'batch',
                description: 'Imported catalogue'
              })
            });
            
            if (syncResponse.ok) {
              console.log('Mappings synced after import');
            }
          } catch (syncErr) {
            console.warn('Sync error (non-critical):', syncErr.message);
          }
        }
        setTimeout(() => setImportMessage(null), 3000);
      } else {
        setImportMessage(`✗ Import failed: ${data.error}`);
        setImportMessageType('error');
        setTimeout(() => setImportMessage(null), 5000);
      }
    } catch (err) {
      setImportMessage(`✗ Error: ${err.message}`);
      setImportMessageType('error');
      setTimeout(() => setImportMessage(null), 5000);
    } finally {
      setImportLoading(false);
      event.target.value = '';
    }
  };

  const handleAppendCatalogue = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setImportLoading(true);
    setImportMessage(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('mode', 'append'); // Append adds to existing rules
      
      const response = await fetch('/api/rules/import-catalogue', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      if (data.success) {
        setImportMessage(`✓ Successfully appended ${data.status?.added || 0} rules`);
        setImportMessageType('success');
        const catalogueResponse = await fetch('/api/rules/catalogue');
        const catalogueData = await catalogueResponse.json();
        if (catalogueData.success) {
          setRules(catalogueData.rules || []);
          
          // Trigger mapping sync after catalogue change
          try {
            const syncResponse = await fetch('/api/rules/sync/on-catalogue-update', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                action: 'batch',
                description: 'Appended rules to catalogue'
              })
            });
            
            if (syncResponse.ok) {
              console.log('Mappings synced after append');
            }
          } catch (syncErr) {
            console.warn('Sync error (non-critical):', syncErr.message);
          }
        }
        setTimeout(() => setImportMessage(null), 3000);
      } else {
        setImportMessage(`✗ Append failed: ${data.error}`);
        setImportMessageType('error');
        setTimeout(() => setImportMessage(null), 5000);
      }
    } catch (err) {
      setImportMessage(`✗ Error: ${err.message}`);
      setImportMessageType('error');
      setTimeout(() => setImportMessage(null), 5000);
    } finally {
      setImportLoading(false);
      event.target.value = '';
    }
  };

  const handleSaveRules = async () => {
    try {
      const dataStr = JSON.stringify({ rules: rules, version: 1 }, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `rules-catalogue-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setImportMessage('✓ Rules exported successfully');
      setImportMessageType('success');
      setTimeout(() => setImportMessage(null), 3000);
    } catch (err) {
      setImportMessage(`✗ Error saving rules: ${err.message}`);
      setImportMessageType('error');
      setTimeout(() => setImportMessage(null), 5000);
    }
  };

  const startEditingRule = (rule) => {
    setEditingRuleId(rule.id);
    const ruleData = JSON.parse(JSON.stringify(rule));
    
    // Normalize: flatten nested provenance.section to code_reference
    if (ruleData.provenance?.section && !ruleData.code_reference) {
      ruleData.code_reference = ruleData.provenance.section;
    }
    
    setEditFormData(ruleData);
  };

  const cancelEditing = () => {
    setEditingRuleId(null);
    setEditFormData({});
  };

  const saveEditedRule = async () => {
    try {
      const params = editFormData.parameters;
      if (typeof params === 'string') {
        JSON.parse(params); // Validate JSON
      }
      
      // Normalize: move code_reference back to provenance.section if it exists
      const dataToSave = JSON.parse(JSON.stringify(editFormData));
      if (dataToSave.code_reference) {
        if (!dataToSave.provenance) {
          dataToSave.provenance = {};
        }
        dataToSave.provenance.section = dataToSave.code_reference;
        delete dataToSave.code_reference;
      }
      
      const response = await fetch('/api/rules/update', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dataToSave),
      });
      
      const data = await response.json();
      if (data.success) {
        setRules(data.rules || []);
        setEditingRuleId(null);
        setEditFormData({});
        
        // Trigger mapping sync after catalogue change
        try {
          const syncResponse = await fetch('/api/rules/sync/on-catalogue-update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              action: 'modify',
              rule_id: editFormData.id
            })
          });
          
          if (syncResponse.ok) {
            console.log('Mappings synced after rule update');
          }
        } catch (syncErr) {
          console.warn('Sync error (non-critical):', syncErr.message);
        }
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (err) {
      alert(`Error saving rule: ${err.message}`);
    }
  };

  const deleteRule = async (ruleId) => {
    if (!window.confirm('Are you sure you want to delete this rule?')) {
      return;
    }
    
    setDeletingRuleId(ruleId);
    try {
      // Delete directly from catalogue by filtering out the rule
      const updatedRules = rules.filter(r => r.id !== ruleId);
      
      // Immediately update the UI
      setRules(updatedRules);
      
      // Save the updated catalogue as a new version
      const response = await fetch('/api/rules/save-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rules: updatedRules,
          description: `Deleted rule: ${ruleId}`
        })
      });
      
      const data = await response.json();
      if (data.success) {
        setImportMessage(`✓ Rule deleted and saved (version ${data.version_id})`);
        setImportMessageType('success');
        setTimeout(() => setImportMessage(null), 3000);
      } else {
        // If save failed, revert the UI
        setRules(rules);
        alert(`Error saving deletion: ${data.error}`);
      }
    } catch (err) {
      // If error, revert the UI
      setRules(rules);
      alert(`Error deleting rule: ${err.message}`);
    } finally {
      setDeletingRuleId(null);
    }
  };

  const filteredRules = rules.filter(rule =>
    rule.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rule.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    rule.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getSeverityIcon = (severity) => {
    // Handle case where severity is an object instead of string
    const severityStr = typeof severity === 'string' ? severity : 'info';
    switch (severityStr.toLowerCase()) {
      case 'error':
        return <AlertCircle size={16} className="severity-error" />;
      case 'warning':
        return <AlertTriangle size={16} className="severity-warning" />;
      default:
        return <Info size={16} className="severity-info" />;
    }
  };

  const getSeverityColor = (severity) => {
    // Handle case where severity is an object instead of string
    const severityStr = typeof severity === 'string' ? severity : 'info';
    switch (severityStr.toLowerCase()) {
      case 'error':
        return '#dc2626';
      case 'warning':
        return '#f59e0b';
      default:
        return '#3b82f6';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '900px', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
        {/* Header */}
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <h2 style={{ margin: 0 }}>Rules Catalogue</h2>
            <span style={{
              backgroundColor: '#e0f2fe',
              color: '#0369a1',
              padding: '0.25rem 0.75rem',
              borderRadius: '9999px',
              fontSize: '0.875rem',
              fontWeight: '600'
            }}>
              {rules.length} {rules.length === 1 ? 'rule' : 'rules'}
            </span>
          </div>
          <button onClick={onClose} className="close-button">
            <X size={24} />
          </button>
        </div>

        {/* Search */}
        <div style={{ padding: '1rem', borderBottom: '1px solid #e5e7eb', backgroundColor: '#f9fafb' }}>
          <input
            type="text"
            placeholder="Search rules by name, ID, or description..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem 0.75rem',
              border: '1px solid #d1d5db',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
            }}
          />
          <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input
              type="checkbox"
              id="selectAllCheckbox"
              checked={filteredRules.length > 0 && selectedRuleIds.size === filteredRules.length}
              indeterminate={selectedRuleIds.size > 0 && selectedRuleIds.size < filteredRules.length}
              onChange={() => {
                if (selectedRuleIds.size === filteredRules.length) {
                  setSelectedRuleIds(new Set());
                } else {
                  const allIds = new Set(filteredRules.map(r => r.id));
                  setSelectedRuleIds(allIds);
                }
              }}
              style={{
                cursor: 'pointer',
                width: '1rem',
                height: '1rem'
              }}
            />
            <label htmlFor="selectAllCheckbox" style={{ cursor: 'pointer', fontSize: '0.875rem', fontWeight: '500', color: '#374151' }}>
              Select All
            </label>
          </div>
          {importMessage && (
            <div style={{
              marginTop: '0.5rem',
              padding: '0.5rem 0.75rem',
              backgroundColor: importMessageType === 'success' ? '#dcfce7' : '#fee2e2',
              color: importMessageType === 'success' ? '#166534' : '#991b1b',
              borderRadius: '0.375rem',
              fontSize: '0.875rem'
            }}>
              {importMessage}
            </div>
          )}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
              Loading rules...
            </div>
          )}

          {error && (
            <div style={{
              padding: '1rem',
              backgroundColor: '#fee2e2',
              color: '#991b1b',
              borderRadius: '0.375rem',
              marginBottom: '1rem'
            }}>
              Error: {error}
            </div>
          )}

          {!loading && filteredRules.length === 0 && (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
              {searchTerm ? 'No rules match your search' : 'No rules available'}
            </div>
          )}

          {!loading && filteredRules.map((rule) => (
            <div
              key={rule.id}
              style={{
                marginBottom: '1rem',
                border: '1px solid #e5e7eb',
                borderRadius: '0.375rem',
                overflow: 'hidden'
              }}
            >
              {/* Rule Header - Expandable */}
              <div
                style={{
                  width: '100%',
                  padding: '1rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  backgroundColor: '#f3f4f6',
                  border: 'none',
                  textAlign: 'left',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#e5e7eb'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#f3f4f6'}
              >
                <input
                  type="checkbox"
                  checked={selectedRuleIds.has(rule.id)}
                  onChange={() => {
                    const newSelected = new Set(selectedRuleIds);
                    if (newSelected.has(rule.id)) {
                      newSelected.delete(rule.id);
                    } else {
                      newSelected.add(rule.id);
                    }
                    setSelectedRuleIds(newSelected);
                  }}
                  style={{
                    cursor: 'pointer',
                    width: '1rem',
                    height: '1rem'
                  }}
                />
                <div
                  onClick={() => toggleExpanded(rule.id)}
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                    cursor: 'pointer'
                  }}
                >
                  {expandedRules[rule.id] ? (
                    <ChevronDown size={18} />
                  ) : (
                    <ChevronRight size={18} />
                  )}
                  <span>
                    <strong>{rule.name || rule.id}</strong>
                    {rule.severity && (
                      <span style={{
                        marginLeft: '0.75rem',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#fff',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        color: getSeverityColor(rule.severity),
                        border: `1px solid ${getSeverityColor(rule.severity)}`
                      }}>
                        {getSeverityIcon(rule.severity)}
                        {typeof rule.severity === 'string' ? rule.severity.toUpperCase() : 'INFO'}
                      </span>
                    )}
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteRule(rule.id);
                  }}
                  disabled={deletingRuleId === rule.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem',
                    padding: '0.5rem 0.75rem',
                    backgroundColor: '#ef4444',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: deletingRuleId === rule.id ? 'not-allowed' : 'pointer',
                    fontSize: '0.75rem',
                    fontWeight: '500',
                    opacity: deletingRuleId === rule.id ? 0.5 : 1,
                    transition: 'background-color 0.2s',
                    marginLeft: 'auto'
                  }}
                  onMouseEnter={(e) => !deletingRuleId && (e.target.style.backgroundColor = '#dc2626')}
                  onMouseLeave={(e) => !deletingRuleId && (e.target.style.backgroundColor = '#ef4444')}
                >
                  <Trash2 size={14} /> Delete
                </button>
              </div>

              {/* Rule Details - Expandable */}
              {expandedRules[rule.id] && (
                <div style={{
                  padding: '1rem',
                  backgroundColor: '#fafafa',
                  borderTop: '1px solid #e5e7eb'
                }}>
                  {/* Edit Form */}
                  {editingRuleId === rule.id ? (
                    <div style={{
                      backgroundColor: '#fff',
                      padding: '1rem',
                      borderRadius: '0.375rem',
                      border: '1px solid #e5e7eb',
                      marginBottom: '1rem'
                    }}>
                      <h4 style={{ marginTop: 0, marginBottom: '0.75rem' }}>Edit Rule</h4>
                      
                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.25rem' }}>Name</label>
                        <input
                          type="text"
                          value={editFormData.name || ''}
                          onChange={(e) => setEditFormData({...editFormData, name: e.target.value})}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>

                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.25rem' }}>Description</label>
                        <textarea
                          value={editFormData.description || ''}
                          onChange={(e) => setEditFormData({...editFormData, description: e.target.value})}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            boxSizing: 'border-box',
                            minHeight: '60px',
                            fontFamily: 'inherit'
                          }}
                        />
                      </div>

                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.25rem' }}>Severity</label>
                        <select
                          value={editFormData.severity || ''}
                          onChange={(e) => setEditFormData({...editFormData, severity: e.target.value})}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            boxSizing: 'border-box'
                          }}
                        >
                          <option value="ERROR">ERROR</option>
                          <option value="WARNING">WARNING</option>
                          <option value="INFO">INFO</option>
                        </select>
                      </div>

                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.25rem' }}>Code Reference</label>
                        <input
                          type="text"
                          value={editFormData.code_reference || ''}
                          onChange={(e) => setEditFormData({...editFormData, code_reference: e.target.value})}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            boxSizing: 'border-box'
                          }}
                        />
                      </div>

                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.875rem', fontWeight: '500', gap: '0.5rem' }}>
                          <input
                            type="checkbox"
                            checked={editFormData.enabled !== false}
                            onChange={(e) => setEditFormData({...editFormData, enabled: e.target.checked})}
                            style={{ cursor: 'pointer' }}
                          />
                          Enabled
                        </label>
                      </div>

                      <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.25rem' }}>Parameters (JSON)</label>
                        <textarea
                          value={typeof editFormData.parameters === 'string' ? editFormData.parameters : JSON.stringify(editFormData.parameters || {})}
                          onChange={(e) => setEditFormData({...editFormData, parameters: e.target.value})}
                          style={{
                            width: '100%',
                            padding: '0.5rem',
                            border: '1px solid #d1d5db',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                            boxSizing: 'border-box',
                            minHeight: '80px',
                            fontFamily: 'monospace'
                          }}
                        />
                      </div>

                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                        <button
                          onClick={saveEditedRule}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.5rem 1rem',
                            backgroundColor: '#10b981',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '0.375rem',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: '500'
                          }}
                        >
                          <Save size={16} /> Save
                        </button>
                        <button
                          onClick={cancelEditing}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.25rem',
                            padding: '0.5rem 1rem',
                            backgroundColor: '#ef4444',
                            color: '#fff',
                            border: 'none',
                            borderRadius: '0.375rem',
                            cursor: 'pointer',
                            fontSize: '0.875rem',
                            fontWeight: '500'
                          }}
                        >
                          <XCircle size={16} /> Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                  {/* Edit Button */}
                  <button
                    onClick={() => startEditingRule(rule)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      padding: '0.5rem 1rem',
                      backgroundColor: '#3b82f6',
                      color: '#fff',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: 'pointer',
                      fontSize: '0.875rem',
                      fontWeight: '500',
                      marginBottom: '1rem'
                    }}
                  >
                    <Edit2 size={16} /> Edit Rule
                  </button>
                  
                  {rule.description && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <p style={{ color: '#4b5563', fontSize: '0.875rem', lineHeight: '1.5' }}>
                        {rule.description}
                      </p>
                    </div>
                  )}

                  {rule.code_reference && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <strong style={{ fontSize: '0.75rem', color: '#6b7280' }}>Code Reference:</strong>
                      <p style={{ fontSize: '0.875rem', color: '#4b5563', margin: '0.25rem 0 0 0' }}>
                        {rule.code_reference}
                      </p>
                    </div>
                  )}

                  {rule.parameters && Object.keys(rule.parameters).length > 0 && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <strong style={{ fontSize: '0.75rem', color: '#6b7280' }}>Parameters:</strong>
                      <div style={{
                        marginTop: '0.5rem',
                        padding: '0.5rem',
                        backgroundColor: '#fff',
                        borderRadius: '0.25rem',
                        border: '1px solid #e5e7eb'
                      }}>
                        <table style={{
                          width: '100%',
                          fontSize: '0.75rem',
                          borderCollapse: 'collapse'
                        }}>
                          <tbody>
                            {Object.entries(rule.parameters).map(([key, val]) => (
                              <tr key={key}>
                                <td style={{
                                  padding: '0.25rem 0.5rem',
                                  fontWeight: '500',
                                  color: '#374151',
                                  borderBottom: '1px solid #e5e7eb'
                                }}>
                                  {key}
                                </td>
                                <td style={{
                                  padding: '0.25rem 0.5rem',
                                  color: '#6b7280',
                                  borderBottom: '1px solid #e5e7eb',
                                  textAlign: 'right'
                                }}>
                                  {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem',
          borderTop: '1px solid #e5e7eb',
          display: 'flex',
          justifyContent: 'flex-end',
          gap: '0.75rem',
          backgroundColor: '#f9fafb'
        }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleImportCatalogue}
            style={{ display: 'none' }}
          />
          <input
            ref={appendFileInputRef}
            type="file"
            accept=".json"
            onChange={handleAppendCatalogue}
            style={{ display: 'none' }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importLoading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1.25rem',
              backgroundColor: '#06b6d4',
              color: '#fff',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: importLoading ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              opacity: importLoading ? 0.5 : 1,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => !importLoading && (e.target.style.backgroundColor = '#0891b2')}
            onMouseLeave={(e) => !importLoading && (e.target.style.backgroundColor = '#06b6d4')}
            title="Import rules (replaces current)"
          >
            <Upload size={16} /> Import
          </button>

          <button
            onClick={() => appendFileInputRef.current?.click()}
            disabled={importLoading || rules.length === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1.25rem',
              backgroundColor: rules.length === 0 ? '#9ca3af' : '#8b5cf6',
              color: '#fff',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: (importLoading || rules.length === 0) ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              opacity: (importLoading || rules.length === 0) ? 0.5 : 1,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => rules.length > 0 && !importLoading && (e.target.style.backgroundColor = '#7c3aed')}
            onMouseLeave={(e) => rules.length > 0 && !importLoading && (e.target.style.backgroundColor = '#8b5cf6')}
            title={rules.length === 0 ? 'Import rules first to append' : 'Append more rules to existing'}
          >
            <Upload size={16} /> Append
          </button>

          <button
            onClick={handleSaveRules}
            disabled={rules.length === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1.25rem',
              backgroundColor: rules.length === 0 ? '#9ca3af' : '#10b981',
              color: '#fff',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: rules.length === 0 ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              opacity: rules.length === 0 ? 0.5 : 1,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => rules.length > 0 && (e.target.style.backgroundColor = '#059669')}
            onMouseLeave={(e) => rules.length > 0 && (e.target.style.backgroundColor = '#10b981')}
            title={rules.length === 0 ? 'Add rules first to save' : 'Save rules to JSON file'}
          >
            <Download size={16} /> Save
          </button>

          <button
            onClick={() => {
              const selectedRules = rules.filter(r => selectedRuleIds.has(r.id));
              if (onConfirmRules) {
                onConfirmRules(selectedRules);
              }
              onClose();
            }}
            disabled={selectedRuleIds.size === 0}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1.25rem',
              backgroundColor: selectedRuleIds.size === 0 ? '#9ca3af' : '#6366f1',
              color: '#fff',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: selectedRuleIds.size === 0 ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              opacity: selectedRuleIds.size === 0 ? 0.5 : 1,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => selectedRuleIds.size > 0 && (e.target.style.backgroundColor = '#4f46e5')}
            onMouseLeave={(e) => selectedRuleIds.size > 0 && (e.target.style.backgroundColor = '#6366f1')}
            title={selectedRuleIds.size === 0 ? 'Select rules to confirm' : `Confirm ${selectedRuleIds.size} selected rule(s)`}
          >
            Confirm ({selectedRuleIds.size})
          </button>

          <button
            onClick={onClose}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1.25rem',
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

export default RuleCatalogueModal;
