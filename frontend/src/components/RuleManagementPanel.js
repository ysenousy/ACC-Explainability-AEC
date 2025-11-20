import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Save, AlertCircle, CheckCircle, Download, Upload } from 'lucide-react';
import EnhancedAddRuleForm from './EnhancedAddRuleForm';

function RuleManagementPanel({ isOpen, onClose, onRulesUpdated, extractedRules }) {
  const [customRules, setCustomRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [showImportStatus, setShowImportStatus] = useState(null);

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

  const handleSaveEnhancedRule = async (rule) => {
    setLoading(true);
    try {
      const response = await fetch('/api/rules/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule: rule })
      });
      const data = await response.json();
      if (data.success) {
        setCustomRules(data.custom_rules);
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

          {/* Right: Add Rule */}
          <div>
            <h3>Add Rule</h3>
            {showAddForm ? (
              <EnhancedAddRuleForm
                onSave={handleSaveEnhancedRule}
                onCancel={() => setShowAddForm(false)}
              />
            ) : (
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
