import React, { useState, useEffect } from 'react';
import { BarChart2, RefreshCw, AlertTriangle } from 'lucide-react';

function RulesAnalysisPanel({ ifcPath }) {
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rulesLoaded, setRulesLoaded] = useState(null); // null = checking, false = not loaded, true = loaded
  const [checkingRules, setCheckingRules] = useState(true); // Start as true (checking)

  // Check if rules are loaded on component mount
  useEffect(() => {
    checkRulesStatus();
  }, []);

  const checkRulesStatus = async () => {
    setCheckingRules(true);
    try {
      const response = await fetch('/api/rules/check-status');
      const data = await response.json();
      setRulesLoaded(data.rules_loaded || false);
    } catch (err) {
      console.error('Error checking rules status:', err);
      setRulesLoaded(false);
    } finally {
      setCheckingRules(false);
    }
  };

  const fetchAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/ifc/analyze-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ifc_path: ifcPath })
      });
      const data = await response.json();
      if (data.success) {
        setAnalysis(data.analysis);
      } else {
        setError(data.error || 'Failed to analyze rules');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rules-analysis-panel" style={{ padding: '2rem', maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <BarChart2 size={24} />
        <h2 style={{ margin: 0 }}>Rules Analysis</h2>
        <button
          onClick={fetchAnalysis}
          disabled={loading || !ifcPath || rulesLoaded === false || rulesLoaded === null || checkingRules}
          style={{
            marginLeft: 'auto',
            padding: '0.5rem 1rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: (rulesLoaded === false || rulesLoaded === null || checkingRules) ? 'not-allowed' : loading ? 'not-allowed' : 'pointer',
            fontWeight: '500',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            opacity: (loading || rulesLoaded === false || rulesLoaded === null || checkingRules) ? 0.6 : 1
          }}
        >
          <RefreshCw size={16} />
          {checkingRules ? 'Checking rules...' : loading ? 'Analyzing...' : 'Analyze Rules'}
        </button>
      </div>

      {/* Show warning if rules not loaded or still checking */}
      {(checkingRules || rulesLoaded === false || rulesLoaded === null) && (
        <div style={{
          padding: '1rem',
          textAlign: 'center',
          backgroundColor: '#fef3c7',
          borderRadius: '0.5rem',
          border: '2px solid #f59e0b',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1rem',
          marginBottom: '1rem'
        }}>
          <AlertTriangle size={48} style={{ color: '#f59e0b' }} />
          <div>
            <h3 style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '1.1rem' }}>
              Rules Import Required
            </h3>
            <p style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '0.95rem' }}>
              You must import regulatory rules before analyzing rules.
            </p>
            <p style={{ margin: '0.5rem 0', color: '#92400e', fontSize: '0.85rem' }}>
              Go to the Rule Management Panel and import rules to continue.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div style={{ color: '#dc2626', marginBottom: '1rem' }}>Error: {error}</div>
      )}

      {analysis && rulesLoaded && (
        <div style={{ background: '#f9fafb', borderRadius: 8, padding: 24, boxShadow: '0 1px 4px #0001' }}>
          <h3>Element Types Present</h3>
          <ul style={{ marginBottom: 16 }}>
            {Object.entries(analysis.element_types_present || {}).map(([type, count]) => (
              <li key={type}><strong>{type}</strong>: {count}</li>
            ))}
          </ul>

          <h3>Applicable Hardcoded Rules</h3>
          <ul style={{ marginBottom: 16 }}>
            {(analysis.applicable_rules || []).map((ruleId) => (
              <li key={ruleId}>{ruleId}</li>
            ))}
          </ul>

          <h3>Extracted Rules from IFC</h3>
          {(analysis.extracted_rules && analysis.extracted_rules.length > 0) ? (
            <ul style={{ marginBottom: 16 }}>
              {analysis.extracted_rules.map((rule, idx) => (
                <li key={rule.id || idx}>
                  <strong>{rule.name || rule.id}</strong> (target: {rule.target_type})<br />
                  <span style={{ fontSize: '0.9em', color: '#6b7280' }}>{rule.description || ''}</span>
                  <pre style={{ background: '#f3f4f6', padding: 8, borderRadius: 4, fontSize: '0.85em', marginTop: 4 }}>{JSON.stringify(rule, null, 2)}</pre>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{ color: '#6b7280', marginBottom: 16 }}>No extracted rules found in this IFC.</div>
          )}

          <h3>Element Types with No Rules</h3>
          {(analysis.unapplied_rules && analysis.unapplied_rules.length > 0) ? (
            <ul>
              {analysis.unapplied_rules.map((type) => (
                <li key={type}><strong>{type}</strong></li>
              ))}
            </ul>
          ) : (
            <div style={{ color: '#6b7280' }}>All present element types have at least one rule.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default RulesAnalysisPanel;
