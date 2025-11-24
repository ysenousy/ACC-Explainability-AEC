import React, { useState } from 'react';
import { AlertCircle } from 'lucide-react';

function ResultsView({ graph }) {
  // All hooks at the top
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');

  // Early return for empty graph
  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const handleEvaluate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/rules/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ graph, include_manifest: true, include_builtin: true }),
      });

      if (!res.ok) throw new Error('Failed to evaluate rules');
      const data = await res.json();

      if (!data.success) throw new Error(data.error || 'Evaluation failed');
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const filteredResults =
    results?.results?.filter((r) => {
      const statusMatch = statusFilter === 'all' || r.status === statusFilter;
      const severityMatch = severityFilter === 'all' || r.severity === severityFilter;
      return statusMatch && severityMatch;
    }) || [];

  return (
    <div className="layer-view">
      <div className="layer-header">
        <AlertCircle size={24} />
        <h2>Results</h2>
      </div>

      <div className="layer-content">
        <div style={{ 
          padding: '0.75rem', 
          backgroundColor: '#eff6ff', 
          borderLeft: '4px solid #0066cc',
          borderRadius: '4px',
          marginBottom: '1rem',
          fontSize: '0.9rem',
          color: '#0066cc'
        }}>
          <strong>Regulatory Compliance Rules</strong> - Evaluating against ADA, IBC, and other building codes
        </div>
        
        <button onClick={handleEvaluate} disabled={loading} className="btn btn-primary" style={{ marginBottom: '1rem' }}>
          {loading ? 'Evaluating...' : 'Evaluate Rules'}
        </button>

        {error && (
          <div style={{ padding: '0.75rem', backgroundColor: '#fee', color: '#c33', borderRadius: '4px', marginBottom: '1rem' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {results && (
          <>
            <div className="results-summary">
              <div className="summary-card">
                <span className="summary-label">Total</span>
                <span className="summary-value">{results.summary?.total || 0}</span>
              </div>
              <div className="summary-card pass">
                <span className="summary-label">Passed</span>
                <span className="summary-value">{results.summary?.passed || 0}</span>
              </div>
              <div className="summary-card fail">
                <span className="summary-label">Failed</span>
                <span className="summary-value">{results.summary?.failed || 0}</span>
              </div>
            </div>

            {/* Filters */}
            <div className="filters-row" style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="filter-select">
                <option value="all">All Status</option>
                <option value="PASS">Pass</option>
                <option value="FAIL">Fail</option>
              </select>
              <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} className="filter-select">
                <option value="all">All Severity</option>
                <option value="ERROR">Error</option>
                <option value="WARNING">Warning</option>
              </select>
            </div>

            {/* Results Table */}
            {filteredResults.length === 0 ? (
              <p style={{ color: '#999' }}>No results match the selected filters</p>
            ) : (
              <table className="results-table">
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Element</th>
                    <th>Status</th>
                    <th>Severity</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredResults.slice(0, 50).map((result, idx) => (
                    <tr key={idx} className={`result-row result-${(result.status || 'unknown').toLowerCase()}`}>
                      <td>{result.rule_id || '—'}</td>
                      <td>{result.element_id || '—'}</td>
                      <td>
                        <span className={`badge badge-${(result.status || 'unknown').toLowerCase()}`}>{result.status || 'Unknown'}</span>
                      </td>
                      <td>
                        <span className={`badge badge-${(result.severity || 'unknown').toLowerCase()}`}>{result.severity || '—'}</span>
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>{result.message || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {filteredResults.length > 50 && (
              <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#999' }}>
                Showing 50 of {filteredResults.length} results. (Pagination coming soon)
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default ResultsView;
