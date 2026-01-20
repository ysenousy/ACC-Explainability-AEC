import React, { useState, useEffect } from 'react';
import reasoningService from '../services/reasoningService';
import './AIAssistantView.css';

function AIAssistantView({ currentGraph, complianceResults, rulesList }) {
  // State management
  const [availableElements, setAvailableElements] = useState([]);
  const [availableFailures, setAvailableFailures] = useState([]);
  const [availableRules, setAvailableRules] = useState([]);
  
  const [selectedElement, setSelectedElement] = useState(null);
  const [selectedFailure, setSelectedFailure] = useState(null);
  const [selectedRule, setSelectedRule] = useState(null);
  
  const [aiResult, setAiResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSteps, setExpandedSteps] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);

  // Load available data from system on component mount or when data changes
  useEffect(() => {
    console.log('AIAssistantView received props:', {
      hasCurrentGraph: !!currentGraph,
      hasElements: !!currentGraph?.elements,
      elementCount: currentGraph?.elements ? Object.keys(currentGraph.elements).length : 0,
      hasComplianceResults: !!complianceResults,
      complianceResultsType: typeof complianceResults,
      complianceResultsIsArray: Array.isArray(complianceResults),
      complianceResultsKeys: complianceResults ? Object.keys(complianceResults) : 'N/A',
      hasResults: complianceResults?.results ? `${complianceResults.results.length} items` : 'N/A',
      hasRulesList: !!rulesList,
      ruleCount: Array.isArray(rulesList) ? rulesList.length : 0
    });
    loadAvailableData();
  }, [currentGraph, complianceResults, rulesList]);

  const loadAvailableData = async () => {
    try {
      console.log('Loading available data...');
      
      // Load elements from current IFC model
      try {
        if (currentGraph && currentGraph.elements) {
          console.log('Loading elements from graph:', currentGraph.elements);
          
          // The elements object contains arrays of different types: spaces, doors, windows, etc.
          const allElements = [];
          const elementsObj = currentGraph.elements;
          
          // Iterate through all element type categories
          for (const [typeKey, typeArray] of Object.entries(elementsObj)) {
            if (Array.isArray(typeArray)) {
              console.log(`Found ${typeArray.length} ${typeKey}`);
              allElements.push(...typeArray.map(el => ({ ...el, element_type: typeKey })));
            }
          }
          
          console.log('Total elements extracted:', allElements.length);
          
          // Debug: Log first element to see structure
          if (allElements.length > 0) {
            console.log('FIRST ELEMENT STRUCTURE:', allElements[0]);
          }
          
          // Extract elements with proper field mapping
          const elements = allElements.map((el, idx) => {
            try {
              // Try to get a good ID
              const id = el.id || el.GlobalId || el.element_id || `elem_${idx}`;
              
              // Get name - try different field names
              let name = el.name || el.Name || 'Unnamed';
              
              // Get type/classification
              const type = el.element_type || el.ifc_type || el.ifc_class || el.type || 'Element';
              
              return { id, name, type, element: el };
            } catch (mapErr) {
              console.error(`Error mapping element ${idx}:`, mapErr);
              return { id: `elem_${idx}`, name: 'Error', type: el.element_type || 'Element', element: el };
            }
          }).slice(0, 100);
          
          console.log('Extracted elements count:', elements.length);
          if (elements.length > 0) {
            console.log('Sample extracted element:', elements[0]);
          }
          setAvailableElements(elements);
        } else {
          console.log('No currentGraph or elements. currentGraph exists:', !!currentGraph);
          setAvailableElements([]);
        }
      } catch (elemErr) {
        console.error('Error loading elements:', elemErr);
        setAvailableElements([]);
      }

      // Load failures from compliance results
      try {
        console.log('Loading failures. complianceResults structure:', complianceResults);
        
        // complianceResults is an object with structure: { summary, rules, results, total_checks, ... }
        // We need to extract the 'results' array
        let failuresArray = [];
        
        if (complianceResults) {
          if (Array.isArray(complianceResults)) {
            // Direct array (legacy structure)
            failuresArray = complianceResults;
            console.log('complianceResults is already an array:', failuresArray.length);
          } else if (typeof complianceResults === 'object' && complianceResults.results) {
            // Object with results property (current structure from /api/rules/check-compliance)
            failuresArray = complianceResults.results;
            console.log('complianceResults is object with results array:', failuresArray.length);
          } else {
            console.log('complianceResults structure not recognized:', Object.keys(complianceResults || {}));
          }
        }
        
        console.log('Found complianceResults. Failures array length:', failuresArray.length);
        
        // Debug: Log first result to see structure
        if (failuresArray.length > 0) {
          console.log('FIRST COMPLIANCE RESULT:', JSON.stringify(failuresArray[0], null, 2));
        }
        
        // Extract failures - filter for failed checks
        const failures = failuresArray
          .filter(r => {
            // Handle different possible structures for "passed" field
            const isPassed = r.passed === true || r.passed === 'true' || r.status === 'passed';
            return !isPassed;  // Keep only failures
          })
          .map((r, idx) => {
            try {
              const id = r.id || r.rule_id || `fail_${idx}`;
              
              // Try to build a good description
              let description = r.explanation || r.message || r.rule_name || `Failure ${idx}`;
              
              // Add more detail if available
              if (r.actual_value !== undefined && r.required_value !== undefined) {
                description += ` (got: ${r.actual_value}, expected: ${r.required_value})`;
              }
              
              const severity = r.severity || 'WARNING';
              
              return {
                id,
                description,
                severity,
                actual_value: r.actual_value,
                required_value: r.required_value,
                unit: r.unit,
                original: r
              };
            } catch (mapErr) {
              console.error(`Error mapping failure ${idx}:`, mapErr);
              return {
                id: `fail_${idx}`,
                description: 'Error parsing failure',
                severity: 'ERROR',
                original: r
              };
            }
          })
          .slice(0, 100);
        
        console.log('Extracted failures count:', failures.length, 'out of', failuresArray.length);
        if (failures.length > 0) {
          console.log('Sample extracted failure:', failures[0]);
        }
        setAvailableFailures(failures);
      } catch (failErr) {
        console.error('Error loading failures:', failErr);
        setAvailableFailures([]);
      }

      // Load rules from rules list
      if (rulesList && Array.isArray(rulesList)) {
        console.log('Found rulesList:', rulesList.length);
        if (rulesList.length > 0) {
          console.log('Sample rule:', JSON.stringify(rulesList[0], null, 2));
        }
        
        const rules = rulesList
          .map(r => ({
            id: r.id || `rule_${Math.random()}`,
            name: r.name || r.id || 'Unknown rule',
            description: r.description || '',
            original: r
          }))
          .slice(0, 100);
        
        console.log('Set rules:', rules.length);
        setAvailableRules(rules);
      } else {
        console.log('No rulesList or not an array:', typeof rulesList);
        setAvailableRules([]);
      }
    } catch (err) {
      console.error('Error loading available data:', err);
      setError('Failed to load data from system');
      // No fallback - keep empty to show data is unavailable
      setAvailableElements([]);
      setAvailableFailures([]);
      setAvailableRules([]);
    }
  };

  const handleExplainWithAI = async () => {
    // Validation
    if (!selectedElement || !selectedFailure || !selectedRule) {
      setError('Please select element, failure, and rule');
      return;
    }

    setLoading(true);
    setError(null);
    setAiResult(null);

    try {
      const payloadToSend = {
        element: selectedElement,
        failure: selectedFailure,
        rule: selectedRule
      };
      
      console.log('=== EXPLAIN WITH AI ===');
      console.log('Sending payload:', JSON.stringify(payloadToSend, null, 2));
      console.log('Element keys:', Object.keys(selectedElement));
      console.log('Failure keys:', Object.keys(selectedFailure));
      console.log('Rule keys:', Object.keys(selectedRule));
      
      const result = await reasoningService.explainWithAI(payloadToSend);

      console.log('AI response:', result);
      
      if (result.success) {
        setAiResult(result);
        setExpandedSteps(false);
      } else {
        setError(result.error || 'AI explanation failed');
      }
    } catch (err) {
      console.error('Error in handleExplainWithAI:', err);
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setSelectedElement(null);
    setSelectedFailure(null);
    setSelectedRule(null);
    setAiResult(null);
    setError(null);
    setExpandedSteps(false);
  };

  return (
    <div className="ai-assistant-view">
      
      {/* Header */}
      <div className="ai-header">
        <h2>🤖 AI Assistant</h2>
        <p>Get AI-powered explanations using the TRM model with confidence scores and reasoning traces</p>
        <small style={{color: '#6b7280', marginTop: '8px', display: 'block'}}>
          📊 <strong>Data Sources:</strong> Elements from loaded IFC model • Failures from compliance checks • Rules from system configuration
        </small>
      </div>

      {/* Input Section */}
      <div className="ai-inputs-section">
        <h3>Select Test Case</h3>
        
        {/* Setup Instructions */}
        {availableElements.length === 0 && availableFailures.length === 0 && availableRules.length === 0 && (
          <div style={{
            fontSize: '0.9rem',
            color: '#1f2937',
            marginBottom: '1.5rem',
            padding: '1rem',
            backgroundColor: '#fef3c7',
            border: '1px solid #f59e0b',
            borderRadius: '0.5rem'
          }}>
            <strong>📋 Setup Guide:</strong>
            <ol style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.5rem' }}>
              <li><strong>Step 1:</strong> Load an IFC file (Data Layer → Upload)</li>
              <li><strong>Step 2:</strong> Run compliance check (Rule Check → Check Compliance)</li>
              <li><strong>Step 3:</strong> Select rules (Rules Layer → Select Rules)</li>
              <li><strong>Step 4:</strong> Return here to use AI Assistant</li>
            </ol>
          </div>
        )}
        
        {/* Data Status */}
        {(availableElements.length > 0 || availableFailures.length > 0 || availableRules.length > 0) && (
          <div style={{
            fontSize: '0.9rem',
            color: '#047857',
            marginBottom: '1rem',
            padding: '0.75rem',
            backgroundColor: '#ecfdf5',
            borderRadius: '0.375rem',
            borderLeft: '3px solid #10b981'
          }}>
            <strong>✓ Data Ready:</strong>
            <ul style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.5rem' }}>
              {availableElements.length > 0 && <li>Elements: {availableElements.length} loaded</li>}
              {availableFailures.length > 0 && <li>Failures: {availableFailures.length} loaded</li>}
              {availableRules.length > 0 && <li>Rules: {availableRules.length} loaded</li>}
            </ul>
          </div>
        )}
        
        <div className="ai-inputs">
          
          {/* Element Selector */}
          <div className="input-group">
            <label htmlFor="element-select">Element:</label>
            <select
              id="element-select"
              value={selectedElement?.id || ''}
              onChange={(e) => {
                const elem = availableElements.find(el => el.id === e.target.value);
                setSelectedElement(elem || null);
              }}
            >
              <option value="">-- Select an element --</option>
              {availableElements.map(elem => (
                <option key={elem.id} value={elem.id}>
                  {elem.name} ({elem.type})
                </option>
              ))}
            </select>
          </div>

          {/* Failure Selector */}
          <div className="input-group">
            <label htmlFor="failure-select">Failure:</label>
            <select
              id="failure-select"
              value={selectedFailure?.id || ''}
              onChange={(e) => {
                const fail = availableFailures.find(f => f.id === e.target.value);
                setSelectedFailure(fail || null);
              }}
            >
              <option value="">-- Select a failure --</option>
              {availableFailures.map(fail => (
                <option key={fail.id} value={fail.id}>
                  {fail.description}
                </option>
              ))}
            </select>
          </div>

          {/* Rule Selector */}
          <div className="input-group">
            <label htmlFor="rule-select">Rule:</label>
            <select
              id="rule-select"
              value={selectedRule?.id || ''}
              onChange={(e) => {
                const rule = availableRules.find(r => r.id === e.target.value);
                setSelectedRule(rule || null);
              }}
            >
              <option value="">-- Select a rule --</option>
              {availableRules.map(rule => (
                <option key={rule.id} value={rule.id}>
                  {rule.name}
                </option>
              ))}
            </select>
          </div>

        </div>
      </div>

      {/* Action Buttons */}
      <div className="ai-actions">
        <button
          className="btn-try-ai"
          onClick={handleExplainWithAI}
          disabled={loading || !selectedElement || !selectedFailure || !selectedRule}
        >
          {loading ? (
            <>⏳ Analyzing...</>
          ) : (
            <>🚀 Explain with AI</>
          )}
        </button>
        <button
          className="btn-clear"
          onClick={handleClear}
          disabled={!selectedElement && !selectedFailure && !selectedRule && !aiResult}
        >
          Clear
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
        </div>
      )}

      {/* Results Section */}
      {aiResult && (
        <div className="ai-result-section">
          
          {/* Prediction and Confidence */}
          <div className="result-header">
            <div className={`prediction-badge ${aiResult.prediction.toLowerCase()}`}>
              {aiResult.prediction}
            </div>
            <div className="confidence-display">
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{ width: `${aiResult.confidence * 100}%` }}
                ></div>
              </div>
              <span className="confidence-text">
                {Math.round(aiResult.confidence * 100)}% Confident
              </span>
            </div>
          </div>

          {/* AI Explanation */}
          <div className="explanation-box">
            <h4>📋 AI Analysis:</h4>
            <p className="explanation-text">
              {aiResult.explanation}
            </p>
          </div>

          {/* Reasoning Steps - Collapsible */}
          <details
            className="reasoning-steps"
            open={expandedSteps}
            onChange={(e) => setExpandedSteps(e.target.open)}
          >
            <summary>
              📊 View {aiResult.steps_taken} Reasoning Steps
              {aiResult.converged && <span className="converged-badge">Early Stopped</span>}
            </summary>
            <div className="steps-container">
              <ol className="steps-list">
                {aiResult.reasoning_steps.map((step, idx) => (
                  <li
                    key={idx}
                    className={step.includes('CONVERGED') ? 'converged' : ''}
                  >
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          </details>

          {/* Model Info */}
          <div className="model-info">
            <small>
              Model: <strong>{aiResult.model_version}</strong> |
              Steps: <strong>{aiResult.steps_taken}/16</strong>
            </small>
          </div>

        </div>
      )}

      {/* No Results Yet */}
      {!aiResult && !loading && !error && (
        <div className="no-results">
          <p>Select element, failure, and rule, then click "Explain with AI" to get started</p>
        </div>
      )}

    </div>
  );
}

export default AIAssistantView;
