import React, { useState, useEffect } from 'react';
import { Zap, CheckCircle2, TrendingUp, AlertCircle, Download, FileJson } from 'lucide-react';
import RuleExtractionSettings from './RuleExtractionSettings';

function GenerateRuleView({ graph }) {
  const [showExtractionSettings, setShowExtractionSettings] = useState(false);
  const [selectedStrategies, setSelectedStrategies] = useState(['pset', 'statistical', 'metadata']);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(true);
  const [generationStatus, setGenerationStatus] = useState(null);
  const [strategiesData, setStrategiesData] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  const [generatedRules, setGeneratedRules] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [strategiesConfigured, setStrategiesConfigured] = useState(false);

  // Analyze available strategies on component mount or when graph changes
  useEffect(() => {
    if (!graph) {
      setIsAnalyzing(false);
      return;
    }

    const analyzeStrategies = async () => {
      setIsAnalyzing(true);
      setAnalysisError(null);
      try {
        const response = await fetch('/api/rules/analyze-strategies', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ graph })
        });

        if (!response.ok) throw new Error('Failed to analyze strategies');
        const data = await response.json();

        if (data.success) {
          setStrategiesData(data.strategies);
          // Auto-select only strategies that have available data
          const available = Object.keys(data.strategies).filter(
            key => data.strategies[key].available
          );
          if (available.length > 0) {
            setSelectedStrategies(available);
          }
        } else {
          setAnalysisError(data.error);
        }
      } catch (error) {
        setAnalysisError(error.message);
      } finally {
        setIsAnalyzing(false);
      }
    };

    analyzeStrategies();
  }, [graph]);

  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const handleApplyStrategies = (strategies) => {
    setSelectedStrategies(strategies);
    setShowExtractionSettings(false);
    setStrategiesConfigured(true);
    setGenerationStatus({ type: 'success', message: `Strategies configured: ${strategies.join(', ')}` });
    setTimeout(() => setGenerationStatus(null), 3000);
  };

  const handleGenerateRules = async () => {
    setIsGenerating(true);
    setGenerationStatus(null);
    setGeneratedRules(null);

    try {
      // Call backend to generate rules with selected strategies
      const response = await fetch('/api/rules/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          graph: graph,
          strategies: selectedStrategies
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to generate rules');
      }

      setGeneratedRules(data.rules || []);
      setGenerationStatus({
        type: 'success',
        message: `Rules generated successfully! ${data.rules_count || 0} rules created.`
      });
      setTimeout(() => setGenerationStatus(null), 5000);
    } catch (error) {
      console.error('Generation error:', error);
      setGenerationStatus({
        type: 'error',
        message: `Error: ${error.message}`
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSaveRules = () => {
    if (!generatedRules || generatedRules.length === 0) return;

    const dataStr = JSON.stringify({ rules: generatedRules }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `generated-rules-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setIsSaving(true);
    setTimeout(() => setIsSaving(false), 1500);
  };

  const strategyDetails = [
    {
      id: 'pset',
      title: 'Property Set Heuristic',
      icon: CheckCircle2,
      description: 'Extract rules from IFC property sets and element attributes',
      color: '#3b82f6',
      badge: '🟠'
    },
    {
      id: 'statistical',
      title: 'Statistical Baseline',
      icon: TrendingUp,
      description: 'Generate 10th percentile baselines from element measurements',
      color: '#10b981',
      badge: '🟡'
    },
    {
      id: 'metadata',
      title: 'Data Completeness',
      icon: AlertCircle,
      description: 'Detect missing or incomplete data in IFC elements',
      color: '#ef4444',
      badge: '🔵'
    }
  ];

  // Show loading state while analyzing
  if (isAnalyzing) {
    return (
      <div className="layer-view">
        <div className="layer-header">
          <Zap size={24} />
          <h2>Generate Rules</h2>
        </div>
        <div className="layer-content">
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <div style={{ animation: 'spin 1s linear infinite', fontSize: '2rem', marginBottom: '1rem' }}>⟳</div>
            <p style={{ color: '#666' }}>Analyzing IFC data for available extraction strategies...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error if analysis failed
  if (analysisError) {
    return (
      <div className="layer-view">
        <div className="layer-header">
          <Zap size={24} />
          <h2>Generate Rules</h2>
        </div>
        <div className="layer-content">
          <div style={{ padding: '1.5rem', backgroundColor: '#fee2e2', color: '#991b1b', borderRadius: '0.5rem', border: '1px solid #fca5a5' }}>
            <strong>Error analyzing strategies:</strong> {analysisError}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="layer-view">
        <div className="layer-header">
          <Zap size={24} />
          <h2>Generate Rules</h2>
        </div>

        <div className="layer-content">
          <div style={{ 
            padding: '0.75rem 1rem', 
            marginBottom: '1.5rem', 
            backgroundColor: '#fef3c7', 
            border: '1px solid #d97706', 
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            color: '#92400e'
          }}>
            <strong>⚙️ Generated Rules:</strong> This section extracts and generates rules from your IFC data using various strategies. Generated rules can be saved and imported into the Regulatory Rules catalogue. Use the "Regulatory Rules" section in the main menu to manage your compliance catalogue.
          </div>
          <div className="info-section">
            <h3>Extract Rules from IFC</h3>
            <p>
              Configure and apply extraction strategies to automatically generate compliance rules from your IFC data.
            </p>
          </div>

          {/* Strategies Configuration Required Prompt - MAIN ENTRY POINT */}
          {!strategiesConfigured && !isAnalyzing && (
            <div style={{
              padding: '1.5rem',
              marginBottom: '1.5rem',
              borderRadius: '0.5rem',
              backgroundColor: '#fef3c7',
              border: '2px solid #d97706',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '1.1rem', fontWeight: '600', color: '#92400e', marginBottom: '0.75rem' }}>
                📋 Configure Extraction Strategies
              </div>
              <p style={{ color: '#92400e', marginBottom: '1rem', fontSize: '0.9rem' }}>
                Before generating rules, please select which extraction strategies to use for analyzing your IFC data.
              </p>
              <button
                onClick={() => setShowExtractionSettings(true)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.75rem 1.5rem',
                  backgroundColor: '#d97706',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '0.9rem',
                  transition: 'background-color 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.backgroundColor = '#b45309'}
                onMouseLeave={(e) => e.target.style.backgroundColor = '#d97706'}
              >
                <Zap size={18} />
                Configure Strategies
              </button>
            </div>
          )}

          {/* Strategies Configured - Show Summary and Generate Button */}
          {strategiesConfigured && (
            <>
              <div style={{
                padding: '1rem',
                marginBottom: '1.5rem',
                borderRadius: '0.5rem',
                backgroundColor: '#dbeafe',
                color: '#1e40af',
                border: '1px solid #bfdbfe',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div>
                  <strong>✓ Strategies Configured</strong>
                  <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
                    Selected: {selectedStrategies.map(s => {
                      const names = { pset: 'Property Set', statistical: 'Statistical', metadata: 'Data Completeness' };
                      return names[s] || s;
                    }).join(', ')}
                  </div>
                </div>
                <button
                  onClick={() => setShowExtractionSettings(true)}
                  style={{
                    padding: '0.5rem 0.75rem',
                    backgroundColor: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    fontWeight: '600',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
                >
                  Change Strategies
                </button>
              </div>

              {/* Action Buttons - Only Show When Configured */}
              <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
                <button
                  onClick={handleGenerateRules}
                  disabled={isGenerating}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1.5rem',
                    backgroundColor: '#06b6d4',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: isGenerating ? 'not-allowed' : 'pointer',
                    fontWeight: '600',
                    fontSize: '0.9rem',
                    transition: 'background-color 0.2s',
                    opacity: isGenerating ? 0.7 : 1
                  }}
                  onMouseEnter={(e) => !isGenerating && (e.target.style.backgroundColor = '#0891b2')}
                  onMouseLeave={(e) => !isGenerating && (e.target.style.backgroundColor = '#06b6d4')}
                  title="Generate rules from IFC using selected strategies"
                >
                  {isGenerating ? (
                    <>
                      <div style={{ animation: 'spin 1s linear infinite' }}>⟳</div>
                      Generating...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 size={18} />
                      Generate Rules
                    </>
                  )}
                </button>
              </div>
            </>
          )}

          {/* Status Message */}
          {generationStatus && (
            <div
              style={{
                padding: '1rem',
                marginBottom: '1.5rem',
                borderRadius: '0.5rem',
                backgroundColor: generationStatus.type === 'success' ? '#dcfce7' : '#fee2e2',
                color: generationStatus.type === 'success' ? '#166534' : '#991b1b',
                border: `1px solid ${generationStatus.type === 'success' ? '#86efac' : '#fca5a5'}`
              }}
            >
              {generationStatus.message}
            </div>
          )}

          {/* Generated Rules Display */}
          {generatedRules && generatedRules.length > 0 && (
            <div style={{ marginBottom: '2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h4 style={{ margin: 0, fontWeight: '600', fontSize: '0.95rem' }}>
                  Generated Rules ({generatedRules.length})
                </h4>
                <button
                  onClick={handleSaveRules}
                  disabled={isSaving}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.5rem 1rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontWeight: '600',
                    fontSize: '0.85rem',
                    transition: 'background-color 0.2s',
                    opacity: isSaving ? 0.7 : 1
                  }}
                  onMouseEnter={(e) => !isSaving && (e.target.style.backgroundColor = '#059669')}
                  onMouseLeave={(e) => !isSaving && (e.target.style.backgroundColor = '#10b981')}
                >
                  {isSaving ? (
                    <>
                      <div style={{ animation: 'spin 1s linear infinite' }}>⟳</div>
                      Saved!
                    </>
                  ) : (
                    <>
                      <Download size={16} />
                      Save as JSON
                    </>
                  )}
                </button>
              </div>
              <div style={{ maxHeight: '400px', overflowY: 'auto', border: '1px solid #e5e7eb', borderRadius: '0.5rem', backgroundColor: '#f9fafb' }}>
                {generatedRules.map((rule, idx) => {
                  // Determine rule type by ID prefix
                  let badgeColor = '#9ca3af';
                  let badgeText = '◯';
                  if (rule.id.startsWith('IFC_PARAM_')) {
                    badgeColor = '#3b82f6';
                    badgeText = '🟠';
                  } else if (rule.id.startsWith('STAT_')) {
                    badgeColor = '#10b981';
                    badgeText = '🟡';
                  } else if (rule.id.startsWith('METADATA_')) {
                    badgeColor = '#ef4444';
                    badgeText = '🔵';
                  }

                  return (
                    <div
                      key={idx}
                      style={{
                        padding: '1rem',
                        borderBottom: idx < generatedRules.length - 1 ? '1px solid #e5e7eb' : 'none',
                        backgroundColor: idx % 2 === 0 ? '#f9fafb' : '#ffffff'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '1rem', marginTop: '0.125rem' }}>{badgeText}</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: '600', fontSize: '0.9rem', color: '#1f2937', marginBottom: '0.25rem' }}>
                            {rule.name}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#6b7280', fontFamily: 'monospace' }}>
                            ID: {rule.id}
                          </div>
                        </div>
                        <span style={{ fontSize: '0.7rem', backgroundColor: badgeColor, color: 'white', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', whiteSpace: 'nowrap' }}>
                          {rule.target_type}
                        </span>
                      </div>
                      {rule.parameters && Object.keys(rule.parameters).length > 0 && (
                        <div style={{ fontSize: '0.8rem', color: '#666', marginLeft: '1.5rem', marginTop: '0.5rem' }}>
                          <strong>Parameters:</strong>
                          {Object.entries(rule.parameters).map(([key, val]) => (
                            <div key={key} style={{ marginTop: '0.25rem', paddingLeft: '0.5rem' }}>
                              • {key}: {typeof val === 'object' ? JSON.stringify(val) : val}
                            </div>
                          ))}
                        </div>
                      )}
                      {rule.severity && (
                        <div style={{ fontSize: '0.75rem', color: '#666', marginLeft: '1.5rem', marginTop: '0.25rem' }}>
                          Severity: <strong>{rule.severity}</strong>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Strategy Information */}
          <div style={{ padding: '1.5rem', backgroundColor: '#f0f9ff', borderRadius: '0.5rem', border: '1px solid #bfdbfe' }}>
            <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: '600', color: '#1e40af' }}>
              ℹ️ How It Works
            </h4>
            <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.875rem', color: '#1e40af', lineHeight: '1.6' }}>
              <li><strong>Property Set Heuristic:</strong> Scans IFC property sets for rule parameters and creates rules based on actual element attributes.</li>
              <li><strong>Statistical Baseline:</strong> Analyzes all elements of the same type and generates 10th percentile baseline rules for compliance checking.</li>
              <li><strong>Data Completeness:</strong> Identifies missing or incomplete data in IFC elements and generates quality assurance rules.</li>
              <li>Select one or more strategies, then click "Generate Rules" to extract rules and add them to your catalogue.</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Extraction Settings Modal */}
      <RuleExtractionSettings
        isOpen={showExtractionSettings}
        onClose={() => setShowExtractionSettings(false)}
        onApply={handleApplyStrategies}
      />
    </>
  );
}

export default GenerateRuleView;
