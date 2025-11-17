import React, { useState } from 'react';
import { Play, Filter } from 'lucide-react';

function RulesTab({ graph }) {
  const [includeManifest, setIncludeManifest] = useState(true);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [summary, setSummary] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterSeverity, setFilterSeverity] = useState('all');

  const manifest = graph?.meta?.rules_manifest;
  const numRules = manifest?.rules?.length || 0;

  const handleEvaluateRules = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/rules/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph,
          include_manifest: includeManifest,
          include_builtin: true,
        }),
      });

      if (!res.ok) throw new Error('Failed to evaluate rules');
      const data = await res.json();

      if (!data.success) throw new Error(data.error);
      setResults(data.results);
      setSummary(data.summary);
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  let filteredResults = results || [];

  if (filterStatus !== 'all') {
    filteredResults = filteredResults.filter((r) => r.status === filterStatus);
  }

  if (filterSeverity !== 'all') {
    filteredResults = filteredResults.filter((r) => r.severity === filterSeverity);
  }

  return (
    <div className="rules-tab">
      {/* Manifest Info */}
      {manifest && (
        <div className="card">
          <div className="card-title">Extracted Rules Manifest</div>
          <p>
            This IFC file has <strong>{numRules}</strong> extracted rules ready for
            evaluation.
          </p>
        </div>
      )}

      {/* Evaluation Controls */}
      <div className="card">
        <div className="card-title">Rule Evaluation</div>
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={includeManifest}
              onChange={(e) => setIncludeManifest(e.target.checked)}
            />
            Include Manifest Rules
          </label>
        </div>
        <button className="btn btn-success" onClick={handleEvaluateRules} disabled={loading}>
          <Play size={18} />
          {loading ? 'Evaluating...' : 'Evaluate Rules'}
        </button>
      </div>

      {/* Results Summary */}
      {summary && (
        <div className="grid">
          <div className="stat-card">
            <div className="stat-card-label">Total Results</div>
            <div className="stat-card-value">{summary.total}</div>
          </div>
          <div className="stat-card" style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}>
            <div className="stat-card-label">Passed</div>
            <div className="stat-card-value">{summary.passed}</div>
          </div>
          <div className="stat-card" style={{ background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)' }}>
            <div className="stat-card-label">Failed</div>
            <div className="stat-card-value">{summary.failed}</div>
          </div>
        </div>
      )}

      {/* Results Filters */}
      {results && (
        <div style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label>Filter Status</label>
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                <option value="all">All</option>
                <option value="PASS">PASS</option>
                <option value="FAIL">FAIL</option>
              </select>
            </div>
            <div className="form-group">
              <label>Filter Severity</label>
              <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)}>
                <option value="all">All</option>
                <option value="ERROR">ERROR</option>
                <option value="WARNING">WARNING</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Results Table */}
      {results && (
        <div>
          <div style={{ marginBottom: '1rem', color: '#666' }}>
            Showing <strong>{filteredResults.length}</strong> result(s)
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Target ID</th>
                  <th>Status</th>
                  <th>Severity</th>
                  <th>Message</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {filteredResults.slice(0, 100).map((result, idx) => (
                  <tr key={idx}>
                    <td style={{ fontSize: '0.85rem', fontFamily: 'monospace' }}>
                      {result.rule_id}
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{result.target_id}</td>
                    <td>
                      <span
                        className={`badge badge-${result.status === 'PASS' ? 'success' : 'error'}`}
                      >
                        {result.status}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge badge-${result.severity === 'ERROR' ? 'error' : 'warning'}`}
                      >
                        {result.severity}
                      </span>
                    </td>
                    <td>{result.details?.message || '—'}</td>
                    <td>{result.details?.confidence || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredResults.length > 100 && (
            <p style={{ marginTop: '1rem', color: '#999' }}>
              Showing first 100 of {filteredResults.length} results
            </p>
          )}
        </div>
      )}

      {!results && !loading && (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#999' }}>
          <p>Click "Evaluate Rules" to run the rule engine</p>
        </div>
      )}
    </div>
  );
}

export default RulesTab;
