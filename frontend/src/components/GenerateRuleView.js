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
    setGenerationStatus({ type: 'success', message: `Strategies updated: ${strategies.join(', ')}` });
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
          <div className="info-section">
            <h3>Extract Rules from IFC</h3>
            <p>
              Configure and apply extraction strategies to automatically generate compliance rules from your IFC data.
            </p>
          </div>

          {/* Selected Strategies Display */}
          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ marginBottom: '1rem', fontWeight: '600', fontSize: '0.95rem' }}>
              Available Strategies ({selectedStrategies.length})
            </h4>
            {selectedStrategies.length === 0 && (
              <div style={{ padding: '1rem', backgroundColor: '#fef3c7', color: '#92400e', borderRadius: '0.5rem', border: '1px solid #fcd34d' }}>
                <strong>No extraction strategies available</strong> for this IFC file. The data may not contain properties that can be extracted using the available strategies.
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
              {strategyDetails.map(strategy => {
                const strategyInfo = strategiesData?.[strategy.id];
                const isSelected = selectedStrategies.includes(strategy.id);
                const Icon = strategy.icon;
                
                if (!strategyInfo?.available) {
                  return null;
                }

                return (
                  <div
                    key={strategy.id}
                    style={{
                      padding: '1rem',
                      border: `2px solid ${isSelected ? strategy.color : '#e5e7eb'}`,
                      borderRadius: '0.5rem',
                      backgroundColor: isSelected ? `${strategy.color}12` : '#f9fafb',
                      opacity: isSelected ? 1 : 0.6,
                      transition: 'all 0.2s',
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedStrategies(s => s.filter(st => st !== strategy.id));
                      } else {
                        setSelectedStrategies(s => [...s, strategy.id]);
                      }
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                      <Icon size={20} color={strategy.color} />
                      <span style={{ fontWeight: '600', fontSize: '0.95rem' }}>
                        {strategy.badge} {strategy.title}
                      </span>
                      <span style={{ marginLeft: 'auto', fontWeight: '700', fontSize: '1.1rem', color: strategy.color }}>
                        {strategyInfo?.count || 0}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: '#666', margin: '0 0 0.5rem 0' }}>
                      {strategy.description}
                    </p>
                    {isSelected && (
                      <span style={{ fontSize: '0.7rem', backgroundColor: strategy.color, color: 'white', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', display: 'inline-block' }}>
                        Selected
                      </span>
                    )}
                    {strategyInfo?.sample_rules && strategyInfo.sample_rules.length > 0 && (
                      <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #e5e7eb' }}>
                        <strong>Example rules:</strong>
                        {strategyInfo.sample_rules.map((rule, idx) => (
                          <div key={idx} style={{ marginTop: '0.25rem' }}>• {rule.name}</div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

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

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
            <button
              onClick={() => setShowExtractionSettings(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                backgroundColor: '#8b5cf6',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.9rem',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.target.style.backgroundColor = '#7c3aed'}
              onMouseLeave={(e) => e.target.style.backgroundColor = '#8b5cf6'}
            >
              <Zap size={18} />
              Configure Strategies
            </button>

            <button
              onClick={handleGenerateRules}
              disabled={isGenerating || selectedStrategies.length === 0}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                backgroundColor: selectedStrategies.length === 0 ? '#d1d5db' : '#06b6d4',
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: selectedStrategies.length === 0 ? 'not-allowed' : 'pointer',
                fontWeight: '600',
                fontSize: '0.9rem',
                transition: 'background-color 0.2s',
                opacity: isGenerating ? 0.7 : 1
              }}
              onMouseEnter={(e) => selectedStrategies.length > 0 && !isGenerating && (e.target.style.backgroundColor = '#0891b2')}
              onMouseLeave={(e) => selectedStrategies.length > 0 && !isGenerating && (e.target.style.backgroundColor = '#06b6d4')}
              title={selectedStrategies.length === 0 ? 'Select at least one strategy' : 'Generate rules from IFC using selected strategies'}
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
