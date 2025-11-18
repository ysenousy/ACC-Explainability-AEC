import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Save, AlertCircle, CheckCircle, Download, Upload } from 'lucide-react';

function RuleManagementPanel({ isOpen, onClose, onRulesUpdated, extractedRules }) {
  const [customRules, setCustomRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showImportStatus, setShowImportStatus] = useState(null);
  const [newRule, setNewRule] = useState({
    id: '',
    name: '',
    description: '',
    target_type: 'door',
    severity: 'ERROR',
    code_reference: '',
  });

  // Fetch custom rules on mount
  useEffect(() => {
    if (isOpen) {
      fetchCustomRules();
    }
  }, [isOpen]);

  const fetchCustomRules = async () => {
    try {
      const response = await fetch('/api/rules/custom');
      const data = await response.json();
      if (data.success) {
        setCustomRules(data.custom_rules || []);
      }
    } catch (err) {
      setMessage('Failed to load custom rules');
      setMessageType('error');
    }
  };

  const handleAddRule = async () => {
    if (!newRule.id || !newRule.name) {
      setMessage('Rule ID and Name are required');
      setMessageType('error');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/rules/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule: newRule })
      });
      const data = await response.json();
      if (data.success) {
        setCustomRules(data.custom_rules);
        setNewRule({
          id: '',
          name: '',
          description: '',
          target_type: 'door',
          severity: 'ERROR',
          code_reference: '',
        });
        setShowAddForm(false);
        setMessage('Rule added successfully');
        setMessageType('success');
        setTimeout(() => setMessage(null), 2000);
      } else {
        setMessage(data.error || 'Failed to add rule');
        setMessageType('error');
      }
    } catch (err) {
      setMessage(err.message);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm(`Delete rule "${ruleId}"?`)) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/rules/delete/${ruleId}`, {
        method: 'DELETE',
      });
      const data = await response.json();
      if (data.success) {
        setCustomRules(data.custom_rules);
        setMessage('Rule deleted successfully');
        setMessageType('success');
        setTimeout(() => setMessage(null), 2000);
      } else {
        setMessage(data.error || 'Failed to delete rule');
        setMessageType('error');
      }
    } catch (err) {
      setMessage(err.message);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleAddFromExtracted = (extractedRule) => {
    setNewRule({
      id: extractedRule.id || `CUSTOM_${Date.now()}`,
      name: extractedRule.name || 'Extracted Rule',
      description: extractedRule.description || '',
      target_type: extractedRule.target_type || 'door',
      severity: extractedRule.severity || 'ERROR',
      code_reference: extractedRule.code_reference || '',
    });
    setShowAddForm(true);
  };

  const handleExportRules = async () => {
    try {
      const response = await fetch('/api/rules/export');
      const data = await response.json();
      if (data.success) {
        // Create JSON and download
        const jsonString = JSON.stringify(data.data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `rules-export-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        setMessage('Rules exported successfully');
        setMessageType('success');
        setTimeout(() => setMessage(null), 2000);
      } else {
        setMessage(data.error || 'Export failed');
        setMessageType('error');
      }
    } catch (err) {
      setMessage(err.message);
      setMessageType('error');
    }
  };

  const handleImportRules = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('merge', 'true');

      const response = await fetch('/api/rules/import', {
        method: 'POST',
        body: formData
      });
      const data = await response.json();
      
      if (data.success) {
        setShowImportStatus(data.status);
        fetchCustomRules();
        setMessage(`Import completed: ${data.status.added} added, ${data.status.skipped} skipped`);
        setMessageType('success');
        setTimeout(() => {
          setMessage(null);
          setShowImportStatus(null);
        }, 3000);
      } else {
        setMessage(data.error || 'Import failed');
        setMessageType('error');
      }
    } catch (err) {
      setMessage(err.message);
      setMessageType('error');
    } finally {
      setLoading(false);
      // Reset input
      event.target.value = '';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        {/* Header */}
        <div className="modal-header">
          <h2>Rule Management</h2>
          <button onClick={onClose} className="close-button">✕</button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', backgroundColor: 'white' }}>
          {/* Left: Custom Rules */}
          <div>
            <h3>Custom Rules ({customRules.length})</h3>
            {message && (
              <div style={{
                padding: '0.75rem 1rem',
                marginBottom: '1rem',
                borderRadius: '0.375rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                backgroundColor: messageType === 'success' ? '#dcfce7' : '#fee2e2',
                color: messageType === 'success' ? '#166534' : '#991b1b',
                fontSize: '0.875rem'
              }}>
                {messageType === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                {message}
              </div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '100%', overflowY: 'auto' }}>
              {customRules.length === 0 ? (
                <div style={{ color: '#6b7280', textAlign: 'center', padding: '2rem' }}>
                  No custom rules yet
                </div>
              ) : (
                customRules.map((rule) => (
                  <div key={rule.id} style={{
                    padding: '1rem',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '0.375rem',
                    border: '1px solid #e5e7eb',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                      <div>
                        <strong>{rule.name}</strong>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>{rule.id}</div>
                      </div>
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        disabled={loading}
                        style={{
                          padding: '0.25rem 0.5rem',
                          backgroundColor: '#dc2626',
                          color: 'white',
                          border: 'none',
                          borderRadius: '0.25rem',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          opacity: loading ? 0.6 : 1
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#4b5563' }}>
                      Target: <strong>{rule.target_type}</strong> | Severity: <strong>{rule.severity}</strong>
                    </div>
                    {rule.description && (
                      <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.5rem' }}>
                        {rule.description}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Right: Add Rule or From Extracted */}
          <div>
            <h3>Add Rule</h3>
            {showAddForm ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <input
                  type="text"
                  placeholder="Rule ID (unique)"
                  value={newRule.id}
                  onChange={(e) => setNewRule({ ...newRule, id: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                />
                <input
                  type="text"
                  placeholder="Rule Name"
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                />
                <textarea
                  placeholder="Description"
                  value={newRule.description}
                  onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db', minHeight: '80px' }}
                />
                <select
                  value={newRule.target_type}
                  onChange={(e) => setNewRule({ ...newRule, target_type: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                >
                  <option value="door">Door</option>
                  <option value="space">Space</option>
                  <option value="window">Window</option>
                  <option value="wall">Wall</option>
                  <option value="building">Building</option>
                </select>
                <select
                  value={newRule.severity}
                  onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                >
                  <option value="INFO">INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
                <input
                  type="text"
                  placeholder="Code Reference"
                  value={newRule.code_reference}
                  onChange={(e) => setNewRule({ ...newRule, code_reference: e.target.value })}
                  style={{ padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #d1d5db' }}
                />
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={handleAddRule}
                    disabled={loading}
                    style={{
                      flex: 1,
                      padding: '0.5rem 1rem',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: 'pointer',
                      fontWeight: '500',
                      opacity: loading ? 0.6 : 1
                    }}
                  >
                    <Save size={16} style={{ marginRight: '0.5rem' }} />
                    Save Rule
                  </button>
                  <button
                    onClick={() => setShowAddForm(false)}
                    style={{
                      flex: 1,
                      padding: '0.5rem 1rem',
                      backgroundColor: '#e5e7eb',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: 'pointer',
                      fontWeight: '500'
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <button
                  onClick={() => setShowAddForm(true)}
                  style={{
                    width: '100%',
                    padding: '0.75rem 1rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontWeight: '500',
                    marginBottom: '1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem'
                  }}
                >
                  <Plus size={18} />
                  Create New Rule
                </button>

                <h4>From IFC-Extracted Rules</h4>
                {extractedRules && extractedRules.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {extractedRules.map((rule, idx) => (
                      <div key={rule.id || idx} style={{
                        padding: '0.75rem',
                        backgroundColor: '#fef3c7',
                        borderRadius: '0.375rem',
                        border: '1px solid #fcd34d',
                      }}>
                        <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                          {rule.name || rule.id}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>
                          Target: {rule.target_type}
                        </div>
                        <button
                          onClick={() => handleAddFromExtracted(rule)}
                          disabled={loading}
                          style={{
                            padding: '0.25rem 0.75rem',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '0.25rem',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            opacity: loading ? 0.6 : 1
                          }}
                        >
                          <Plus size={12} style={{ marginRight: '0.25rem' }} />
                          Use This
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: '#6b7280', fontSize: '0.875rem' }}>
                    No extracted rules available. Upload and analyze an IFC first.
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              onClick={handleExportRules}
              disabled={loading || customRules.length === 0}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#8b5cf6',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontWeight: '500',
                fontSize: '0.875rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: loading || customRules.length === 0 ? 0.6 : 1
              }}
            >
              <Download size={16} />
              Export
            </button>
            
            <label style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#06b6d4',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              opacity: loading ? 0.6 : 1
            }}>
              <Upload size={16} />
              Import
              <input
                type="file"
                accept=".json"
                onChange={handleImportRules}
                disabled={loading}
                style={{ display: 'none' }}
              />
            </label>
          </div>

          <button
            onClick={onClose}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#e5e7eb',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500',
              fontSize: '0.875rem'
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default RuleManagementPanel;
