import React, { useState, useEffect } from 'react';
import { AlertCircle, BarChart3, Wrench, Loader } from 'lucide-react';
import WhyItFailed from './WhyItFailed';
import ImpactAssessment from './ImpactAssessment';
import HowToFix from './HowToFix';
import reasoningService from '../services/reasoningService';
import '../styles/ReasoningView.css';

/**
 * ReasoningView - Main Reasoning Layer Component
 * 
 * Provides three tabs for compliance failure analysis:
 * 1. Why It Failed - Explains failures with context
 * 2. Impact Assessment - Quantifies scope and severity
 * 3. How To Fix - Provides tiered recommendations
 */
function ReasoningView({ graph, complianceResults, activeTab: tabProp }) {
  const [activeTab, setActiveTab] = useState(tabProp || 'why');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Data from analysis
  const [failures, setFailures] = useState([]);
  const [impactMetrics, setImpactMetrics] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [summary, setSummary] = useState(null);
  const [hasComplianceData, setHasComplianceData] = useState(false);
  const [complianceData, setComplianceData] = useState(null); // Store actual compliance data

  // Update active tab when prop changes
  useEffect(() => {
    if (tabProp) {
      setActiveTab(tabProp);
    }
  }, [tabProp]);

  // Try to get compliance results from local storage or session
  const getComplianceResults = async () => {
    // Check if we have compliance results passed as prop
    if (complianceResults) {
      return complianceResults;
    }

    // Try to get from session storage (set after compliance check)
    const stored = sessionStorage.getItem('lastComplianceResults');
    if (stored) {
      try {
        // Cache expires after 24 hours
        const lastCheck = sessionStorage.getItem('lastComplianceCheckTime');
        const now = Date.now();
        if (lastCheck && (now - parseInt(lastCheck)) < 24 * 60 * 60 * 1000) {
          // Cache is fresh, use it
          return JSON.parse(stored);
        } else {
          // Cache is stale, clear it
          sessionStorage.removeItem('lastComplianceResults');
          sessionStorage.removeItem('lastComplianceCheckTime');
          console.log('[ReasoningView] Cache expired (>24 hours old), will fetch fresh data on next compliance check');
        }
      } catch (e) {
        console.error('Failed to parse stored compliance results:', e);
        sessionStorage.removeItem('lastComplianceResults');
      }
    }

    return null;
  };

  useEffect(() => {
    if (graph) {
      analyzeFailures();
    }
  }, [graph]);

  // Listen for storage changes when new compliance results are saved
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'lastComplianceResults' && e.newValue) {
        console.log('[ReasoningView] Compliance data updated in sessionStorage, re-analyzing...');
        analyzeFailures();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const analyzeFailures = async () => {
    setLoading(true);
    setError(null);

    try {
      const results = await getComplianceResults();

      if (!results || !results.results) {
        console.log('[ReasoningView] No compliance results found, checking if we need to run check');
        setHasComplianceData(false);
        setFailures([]);
        setLoading(false);
        return;
      }

      console.log('[ReasoningView] Retrieved compliance results with', {
        num_results: results.results?.length,
        has_total_elements: 'total_elements' in results,
        total_elements: results.total_elements,
        has_summary: 'summary' in results,
        summary_total_elements: results.summary?.total_elements
      });

      // Get failures from compliance results
      const failuresList = await reasoningService.getFailuresFromCompliance(results);
      
      if (!failuresList || failuresList.length === 0) {
        setFailures([]);
        setHasComplianceData(true);
        setLoading(false);
        return;
      }

      setFailures(failuresList);
      setHasComplianceData(true);
      setComplianceData(results); // Store the actual compliance data

      // Get impact analysis
      let totalElem = results.total_elements || results.summary?.total_elements || 0;
      
      // If backend didn't provide total_elements, estimate from unique elements in results
      if (totalElem === 0 && failuresList && failuresList.length > 0) {
        const uniqueElements = new Set(failuresList.map(f => f.element_id));
        totalElem = uniqueElements.size || 0;
        console.log('[ReasoningView] Backend returned 0 elements, estimated from failures:', {
          estimated_total: totalElem,
          unique_failed_elements: uniqueElements.size,
          total_failures: failuresList.length
        });
      }
      
      console.log('[ReasoningView] Final totalElements for impact analysis:', {
        from_backend: results.total_elements || results.summary?.total_elements,
        final_value: totalElem,
        method: totalElem > 0 ? 'from_backend' : 'estimated_from_failures'
      });
      const impact = await reasoningService.analyzeImpact(failuresList, totalElem);
      setImpactMetrics(impact);

      // Get recommendations
      const recs = await reasoningService.generateRecommendations(failuresList);
      setRecommendations(recs);

      // Get summary
      const summaryData = await reasoningService.getFailureSummary(failuresList);
      setSummary(summaryData);

    } catch (err) {
      console.error('Error analyzing failures:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!graph || !hasComplianceData) {
    return (
      <div className="reasoning-placeholder">
        <AlertCircle size={32} />
        <p>Run a compliance check first to see analysis results.</p>
        <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.5rem' }}>
          Go to "Check Compliance" or "Compliance Report" to generate compliance data.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="reasoning-loading">
        <Loader size={32} className="spinner" />
        <p>Analyzing compliance failures...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="reasoning-error">
        <AlertCircle size={32} />
        <h3>Analysis Error</h3>
        <p>{error}</p>
        <button onClick={analyzeFailures} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  if (failures.length === 0) {
    return (
      <div className="reasoning-success">
        <div className="success-icon">✓</div>
        <h3>All Systems Compliant</h3>
        <p>No compliance failures detected. Your model meets all selected regulatory standards.</p>
      </div>
    );
  }

  return (
    <div className="reasoning-view">
      {/* Tab Navigation */}
      <div className="reasoning-tabs-nav">
        <button
          className={`tab-button ${activeTab === 'why' ? 'active' : ''}`}
          onClick={() => setActiveTab('why')}
        >
          <AlertCircle size={18} />
          <span>Why It Failed</span>
          {summary && <span className="tab-badge">{summary.total_failures}</span>}
        </button>

        <button
          className={`tab-button ${activeTab === 'impact' ? 'active' : ''}`}
          onClick={() => setActiveTab('impact')}
        >
          <BarChart3 size={18} />
          <span>Impact Assessment</span>
        </button>

        <button
          className={`tab-button ${activeTab === 'fix' ? 'active' : ''}`}
          onClick={() => setActiveTab('fix')}
        >
          <Wrench size={18} />
          <span>How To Fix</span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="reasoning-tab-content">
        {activeTab === 'why' && (
          <WhyItFailed failures={failures} />
        )}

        {activeTab === 'impact' && (
          <ImpactAssessment 
            failures={failures}
            impactMetrics={impactMetrics}
            totalElements={(() => {
              // Use the stored compliance data from state, not the prop
              const te = (complianceData && (complianceData.total_elements || complianceData.summary?.total_elements)) || 0;
              console.log('[ReasoningView.ImpactAssessment] totalElements prop:', {
                passed_to_component: te,
                from_top_level: complianceData?.total_elements,
                from_summary: complianceData?.summary?.total_elements,
                complianceData_keys: complianceData ? Object.keys(complianceData).slice(0, 10) : 'null'
              });
              return te;
            })()}
          />
        )}

        {activeTab === 'fix' && (
          <HowToFix 
            recommendations={recommendations}
            failures={failures}
          />
        )}
      </div>
    </div>
  );
}

export default ReasoningView;
