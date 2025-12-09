/**
 * TRM Model Management Dashboard
 * 
 * React component for viewing and managing model versions, training history,
 * and comparing different versions.
 */

import React, { useState, useEffect } from 'react';
import { Brain, BarChart3, ArrowUpRight, Clock, TrendingUp, Info, Zap, Database, Network, BookOpen, Trash2 } from 'lucide-react';
import '../styles/TRMDashboard.css';

const TRMDashboard = () => {
  const [versions, setVersions] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [bestVersion, setBestVersion] = useState(null);
  const [bestVersionData, setBestVersionData] = useState(null);
  const [trainingHistory, setTrainingHistory] = useState([]);
  const [comparison, setComparison] = useState(null);
  const [selectedForComparison, setSelectedForComparison] = useState([]);
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [activeTab, setActiveTab] = useState('versions');
  const [complianceReport, setComplianceReport] = useState(null);
  const [showModelInfo, setShowModelInfo] = useState(false);
  const [modelInfo, setModelInfo] = useState(null);

  // Fetch versions on mount
  useEffect(() => {
    fetchVersions();
    fetchBestVersion();
    fetchModelInfo();
  }, []);

  const fetchModelInfo = async () => {
    try {
      const response = await fetch('/api/trm/models');
      const data = await response.json();
      setModelInfo(data);
    } catch (error) {
      console.error('Error fetching model info:', error);
    }
  };

  const fetchVersions = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/trm/versions');
      const data = await response.json();
      setVersions(data.versions);
    } catch (error) {
      console.error('Error fetching versions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBestVersion = async () => {
    try {
      const response = await fetch('/api/trm/versions/best');
      const data = await response.json();
      if (data.version) {
        setBestVersion(data.version.version_id);
        setBestVersionData(data.version);
      }
    } catch (error) {
      console.error('Error fetching best version:', error);
    }
  };

  const fetchVersionDetail = async (versionId) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/trm/versions/${versionId}`);
      const data = await response.json();
      setSelectedVersion(data.version);
      setTrainingHistory(data.training_history);
    } catch (error) {
      console.error('Error fetching version detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectForComparison = (versionId) => {
    if (selectedForComparison.includes(versionId)) {
      setSelectedForComparison(selectedForComparison.filter(id => id !== versionId));
    } else {
      setSelectedForComparison([...selectedForComparison, versionId]);
    }
  };

  const compareSelected = async () => {
    if (selectedForComparison.length < 2) {
      alert('Please select at least 2 versions to compare');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/trm/versions/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_ids: selectedForComparison })
      });
      const data = await response.json();
      setComparison(data);
      setActiveTab('comparison');
    } catch (error) {
      console.error('Error comparing versions:', error);
    } finally {
      setLoading(false);
    }
  };

  const markBestVersion = async (versionId) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/trm/versions/${versionId}/mark-best`, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.success) {
        setBestVersion(versionId);
        fetchVersions();
      }
    } catch (error) {
      console.error('Error marking best version:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteVersion = async (versionId) => {
    if (!window.confirm(`Are you sure you want to delete version ${versionId}? This action cannot be undone.`)) {
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`/api/trm/versions/${versionId}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (data.success) {
        fetchVersions();
        // If deleted version was selected, clear selection
        if (selectedVersion?.version_id === versionId) {
          setSelectedVersion(null);
        }
      } else {
        alert('Failed to delete version: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error deleting version:', error);
      alert('Error deleting version: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // Load compliance data from session storage
  const loadComplianceData = () => {
    const stored = sessionStorage.getItem('lastComplianceResults');
    if (stored) {
      try {
        const data = JSON.parse(stored);
        setComplianceReport(data);
        return data;
      } catch (err) {
        console.error('Error parsing compliance data:', err);
        return null;
      }
    }
    return null;
  };

  // Check dataset stats before training
  const checkDatasetStats = async () => {
    try {
      const response = await fetch('/api/trm/dataset/stats');
      const data = await response.json();
      console.log('Dataset stats:', data);
      return data;
    } catch (err) {
      console.error('Error fetching dataset stats:', err);
      return null;
    }
  };

  // Train TRM Model using compliance data
  const trainModel = async () => {
    // Get compliance data from session or memory
    const data = complianceReport || loadComplianceData();
    
    if (!data || !data.results || data.results.length === 0) {
      alert('❌ No compliance data available.\n\nPlease:\n1. Load an IFC file\n2. Import regulatory rules\n3. Generate compliance report\n4. Then come back here to train the model');
      return;
    }

    setTraining(true);
    try {
      // Step 0: Check dataset before adding new samples
      console.log('Step 0: Checking dataset stats...');
      const statsBeforeTraining = await checkDatasetStats();
      console.log('Stats before training:', statsBeforeTraining);

      // SKIP adding samples if dataset already has data - just train on existing data
      if (statsBeforeTraining?.total_samples && statsBeforeTraining.total_samples > 0) {
        console.log(`⏭️ Skipping sample addition - ${statsBeforeTraining.total_samples} samples already in dataset`);
      } else {
        // Only add samples if dataset is empty
        console.log('Step 1: Adding compliance data as training samples...');
        const samples = data.results.map(result => ({
          compliance_result: {
            element_guid: result.element_id || result.element_guid || 'unknown',
            element_data: {
              type: result.element_type || 'unknown',
              ifc_file: result.ifc_file || 'unknown',
              ...result.properties
            },
            rule_data: {
              id: result.rule_id || 'unknown',
              name: result.rule_name || 'Unknown Rule',
              severity: result.severity || 'INFO',
              description: result.explanation || ''
            },
            compliance_result: {
              passed: result.passed ? true : false
            },
            rule_id: result.rule_id || 'unknown'
          },
          ifc_file: result.ifc_file || 'unknown'
        }));

        let addedCount = 0;
        for (const sample of samples) {
          try {
            const response = await fetch('/api/trm/add-sample', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(sample)
            });
            if (response.ok) {
              addedCount++;
            }
          } catch (err) {
            console.warn('Failed to add sample:', err);
          }
        }
        console.log(`✅ Added ${addedCount}/${samples.length} training samples`);
      }

      // Step 2: Train the model with fast settings
      console.log('Step 2: Training TRM model (fast mode - 10 epochs)...');
      const trainResponse = await fetch('/api/trm/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epochs: 10,  // Reduced from 30 for speed
          learning_rate: 0.001,
          batch_size: 16,  // Increased from 4 for speed
          resume: false
        })
      });

      const trainData = await trainResponse.json();
      console.log('Train response status:', trainResponse.status);
      console.log('Train response data:', trainData);
      
      if (!trainData.success) {
        throw new Error(trainData.error || 'Training failed');
      }

      console.log('✅ Training completed:', trainData);
      
      // Refresh versions list to show new version
      await fetchVersions();
      await fetchBestVersion();
      
      alert(`✅ Model Training Completed!\n\nVersion: ${trainData.metrics?.version_id || 'v1.0'}\nEpochs: ${trainData.epochs_trained}\nBest Loss: ${trainData.best_loss?.toFixed(4) || 'N/A'}`);
    } catch (err) {
      console.error('Error training model:', err);
      alert('❌ Failed to train model:\n' + err.message);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="trm-dashboard">
      {/* Enhanced Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <Brain size={32} color="#8b5cf6" />
            <h1 style={{ margin: 0 }}>TRM Model Management</h1>
          </div>
          <p style={{ color: '#6b7280', margin: 0, fontSize: '0.95rem' }}>
            Manage, train, and compare model versions
          </p>
        </div>
        <button
          onClick={trainModel}
          disabled={training || loading}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: training || loading ? '#d1d5db' : '#8b5cf6',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: training || loading ? 'not-allowed' : 'pointer',
            fontWeight: '600',
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            boxShadow: '0 4px 12px rgba(139, 92, 246, 0.4)',
            transition: 'all 0.3s ease'
          }}
          onMouseEnter={(e) => !training && !loading && (e.target.style.transform = 'translateY(-2px)')}
          onMouseLeave={(e) => (e.target.style.transform = 'translateY(0)')}
          title="Train model using compliance data from reasoning layer"
        >
          <span style={{ fontSize: '1.2rem' }}>🧠</span>
          {training ? 'Training...' : 'Train Model'}
        </button>
      </div>

      {/* Stats Cards */}
      {versions.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '1.5rem'
        }}>
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '12px',
            boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
            borderLeft: '4px solid #8b5cf6'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>Total Versions</p>
                <p style={{ color: '#1f2937', fontSize: '2rem', fontWeight: '700', margin: 0 }}>{versions.length}</p>
              </div>
              <TrendingUp size={24} color="#8b5cf6" />
            </div>
          </div>

          {bestVersion && bestVersionData && (
            <>
              <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '12px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                borderLeft: '4px solid #10b981'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>Best Accuracy</p>
                    <p style={{ color: '#10b981', fontSize: '2rem', fontWeight: '700', margin: 0 }}>
                      {(bestVersionData.performance_metrics?.best_val_accuracy * 100).toFixed(1)}%
                    </p>
                  </div>
                  <ArrowUpRight size={24} color="#10b981" />
                </div>
              </div>

              <div style={{
                background: 'white',
                padding: '1.5rem',
                borderRadius: '12px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                borderLeft: '4px solid #f59e0b'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <p style={{ color: '#6b7280', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>Best Loss</p>
                    <p style={{ color: '#f59e0b', fontSize: '2rem', fontWeight: '700', margin: 0 }}>
                      {bestVersionData.performance_metrics?.best_val_loss?.toFixed(3)}
                    </p>
                  </div>
                  <BarChart3 size={24} color="#f59e0b" />
                </div>
              </div>
            </>
          )}
        </div>
      )}
      
      <div className="tabs">
        <button 
          className={activeTab === 'versions' ? 'active' : ''} 
          onClick={() => setActiveTab('versions')}
        >
          Versions
        </button>
        <button 
          className={activeTab === 'detail' ? 'active' : ''} 
          onClick={() => setActiveTab('detail')}
        >
          Version Detail
        </button>
        <button 
          className={activeTab === 'comparison' ? 'active' : ''} 
          onClick={() => setActiveTab('comparison')}
        >
          Comparison
        </button>
        <button 
          className={activeTab === 'about' ? 'active' : ''} 
          onClick={() => setActiveTab('about')}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <Info size={18} />
          How It Works
        </button>
      </div>

      {/* Versions Tab */}
      {activeTab === 'versions' && (
        <div className="versions-tab">
          <h2>Model Versions</h2>
          <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
            View and manage different versions of your TRM model. Each version represents a trained model with specific performance metrics and configurations.
          </p>

          {loading ? (
            <p>Loading...</p>
          ) : (
            <div className="workflow-section">
              <h3>Available Versions</h3>
              <div className="workflow-steps">
                {versions.map((version, index) => (
                  <div key={version.version_id} className="step">
                    <div className="step-number">{index + 1}</div>
                    <div className="step-content">
                      <h4>{version.version_id}</h4>
                      <p style={{ fontSize: '0.8rem', color: '#6b7280', margin: '0.25rem 0' }}>
                        {new Date(version.created_at).toLocaleDateString()}
                      </p>
                      <p style={{ fontSize: '0.75rem', color: '#4b5563', margin: '0.5rem 0 0 0' }}>
                        Accuracy: {(version.performance_metrics?.best_val_accuracy * 100).toFixed(1)}%
                      </p>
                      <button 
                        onClick={() => {
                          fetchVersionDetail(version.version_id);
                          setActiveTab('detail');
                        }}
                        style={{
                          marginTop: '0.5rem',
                          padding: '0.5rem 1rem',
                          background: '#8b5cf6',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          fontWeight: '600'
                        }}
                      >
                        View Detail
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {selectedForComparison.length > 1 && (
            <div className="compare-action">
              <button onClick={compareSelected} className="btn-primary">
                Compare {selectedForComparison.length} Versions
              </button>
            </div>
          )}
        </div>
      )}

      {/* Detail Tab */}
      {activeTab === 'detail' && selectedVersion && (
        <div className="versions-tab">
          <h2>Version Details: {selectedVersion.version_id}</h2>
          <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
            In-depth information about this model version including configuration, performance metrics, and training history.
          </p>
          
          {/* Performance Metrics Cards */}
          <div className="workflow-section">
            <h3>Performance Metrics</h3>
            <div className="workflow-steps">
              <div className="step">
                <div style={{ color: '#6b7280', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>Accuracy</div>
                <div style={{ color: '#10b981', fontSize: '2rem', fontWeight: '700', margin: 0 }}>
                  {(selectedVersion.performance_metrics?.best_val_accuracy * 100).toFixed(2)}%
                </div>
              </div>
              <div className="step">
                <div style={{ color: '#6b7280', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>Loss</div>
                <div style={{ color: '#f59e0b', fontSize: '2rem', fontWeight: '700', margin: 0 }}>
                  {selectedVersion.performance_metrics?.best_val_loss?.toFixed(4)}
                </div>
              </div>
              <div className="step">
                <div style={{ color: '#6b7280', fontSize: '0.875rem', margin: '0 0 0.5rem 0' }}>Training Time</div>
                <div style={{ color: '#3b82f6', fontSize: '2rem', fontWeight: '700', margin: 0 }}>
                  {(selectedVersion.training_duration_seconds / 60).toFixed(1)}m
                </div>
              </div>
            </div>
          </div>
          
          <div className="workflow-section">
            <h3>Training Configuration</h3>
            <pre style={{ background: 'white', padding: '1rem', borderRadius: '6px', overflowX: 'auto', border: '1px solid #e5e7eb' }}>
              {JSON.stringify(selectedVersion.training_config, null, 2)}
            </pre>
          </div>
          
          <div className="workflow-section">
            <h3>Training History</h3>
            {trainingHistory.length > 0 ? (
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Epoch</th>
                    <th>Train Loss</th>
                    <th>Val Loss</th>
                    <th>Val Accuracy</th>
                  </tr>
                </thead>
                <tbody>
                  {trainingHistory.map((entry, idx) => (
                    <tr key={idx}>
                      <td>{entry.epoch}</td>
                      <td>{entry.train_loss?.toFixed(4)}</td>
                      <td>{entry.val_loss?.toFixed(4)}</td>
                      <td>
                        {entry.val_accuracy 
                          ? (entry.val_accuracy * 100).toFixed(2) + '%'
                          : '-'
                        }
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No training history available</p>
            )}
          </div>
        </div>
      )}

      {/* Comparison Tab */}
      {activeTab === 'comparison' && comparison && (
        <div className="versions-tab">
          <h2>Version Comparison</h2>
          <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
            Side-by-side comparison of selected model versions and their performance metrics.
          </p>
          
          <div className="workflow-section">
            <h3>Versions</h3>
            <div style={{ overflowX: 'auto', background: 'white', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Created</th>
                    <th>Accuracy</th>
                    <th>Loss</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.versions.map(v => (
                    <tr key={v.id}>
                      <td>{v.id}</td>
                      <td>{new Date(v.created_at).toLocaleDateString()}</td>
                      <td>{(v.best_val_accuracy * 100).toFixed(2)}%</td>
                      <td>{v.best_val_loss?.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          
          {Object.keys(comparison.metric_differences).length > 0 && (
            <div className="workflow-section">
              <h3>Metric Differences</h3>
              <pre style={{ background: 'white', padding: '1rem', borderRadius: '6px', overflowX: 'auto', border: '1px solid #e5e7eb' }}>
                {JSON.stringify(comparison.metric_differences, null, 2)}
              </pre>
            </div>
          )}
          
          {Object.keys(comparison.config_differences).length > 0 && (
            <div className="workflow-section">
              <h3>Config Differences</h3>
              <pre style={{ background: 'white', padding: '1rem', borderRadius: '6px', overflowX: 'auto', border: '1px solid #e5e7eb' }}>
                {JSON.stringify(comparison.config_differences, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* About Tab - How It Works */}
      {activeTab === 'about' && (
        <div className="about-tab">
          <h2>How the TRM Model Works</h2>
          <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
            The Tiny Recursive Reasoner (TRM) is a neural network trained to learn compliance patterns and predict building code violations.
          </p>

          {/* Workflow */}
          <div className="workflow-section">
            <h3>Workflow Steps</h3>
            <div className="workflow-steps">
              <div className="step">
                <div className="step-number">1</div>
                <div className="step-content">
                  <h4>Load IFC Model</h4>
                  <p>Import building information from design files</p>
                </div>
              </div>

              <div className="step">
                <div className="step-number">2</div>
                <div className="step-content">
                  <h4>Extract Data</h4>
                  <p>Extract building elements and properties</p>
                </div>
              </div>

              <div className="step">
                <div className="step-number">3</div>
                <div className="step-content">
                  <h4>Check Compliance</h4>
                  <p>Apply regulatory rules (Pass/Fail)</p>
                </div>
              </div>

              <div className="step">
                <div className="step-number">4</div>
                <div className="step-content">
                  <h4>Generate Report</h4>
                  <p>Summarize results and violations</p>
                </div>
              </div>

              <div className="step">
                <div className="step-number">5</div>
                <div className="step-content">
                  <h4>Train Model</h4>
                  <p>Feed compliance data to TRM</p>
                </div>
              </div>

              <div className="step">
                <div className="step-number">6</div>
                <div className="step-content">
                  <h4>Predict Issues</h4>
                  <p>Model predicts violations early</p>
                </div>
              </div>
            </div>
          </div>

          {/* Info Grid */}
          <div className="info-grid">
            <div className="info-card">
              <h4>Model Architecture</h4>
              <p><strong>Type:</strong> TinyComplianceNetwork</p>
              <p><strong>Layers:</strong> 3-4 dense layers</p>
              <p><strong>Input:</strong> 320-dimensional features</p>
              <p><strong>Output:</strong> Pass/Fail classification</p>
            </div>

            <div className="info-card">
              <h4>Training Data</h4>
              <p><strong>Source:</strong> Compliance reports</p>
              <p><strong>Features:</strong> Element properties</p>
              <p><strong>Labels:</strong> Pass=1, Fail=0</p>
              <p><strong>Split:</strong> 80/10/10 train/val/test</p>
            </div>

            <div className="info-card">
              <h4>Training Config</h4>
              <p><strong>Optimizer:</strong> Adam</p>
              <p><strong>Loss:</strong> Binary Cross-Entropy</p>
              <p><strong>Learning Rate:</strong> 0.001</p>
              <p><strong>Epochs:</strong> 10-30</p>
            </div>

            <div className="info-card">
              <h4>Performance</h4>
              <p><strong>Accuracy:</strong> Correct predictions %</p>
              <p><strong>Validation Loss:</strong> Prediction error</p>
              <p><strong>Training Time:</strong> ~1-2 minutes</p>
              {bestVersionData && (
                <p style={{ marginTop: '0.5rem', fontWeight: '600', color: '#10b981' }}>
                  Best: {(bestVersionData.performance_metrics?.best_val_accuracy * 100).toFixed(1)}%
                </p>
              )}
            </div>
          </div>

          {/* Model Info */}
          {modelInfo && (
            <div className="model-info-section">
              <h3>Current Model</h3>
              <div className="info-table">
                <div className="info-row">
                  <span className="label">Type:</span>
                  <span className="value">{modelInfo.model_type}</span>
                </div>
                <div className="info-row">
                  <span className="label">Parameters:</span>
                  <span className="value">{modelInfo.parameters?.toLocaleString()}</span>
                </div>
                <div className="info-row">
                  <span className="label">Device:</span>
                  <span className="value">{modelInfo.device}</span>
                </div>
                <div className="info-row">
                  <span className="label">Status:</span>
                  <span className="value">{modelInfo.trained ? '✓ Trained' : '✗ Not trained'}</span>
                </div>
              </div>
            </div>
          )}

          {/* Use Cases */}
          <div className="use-cases-section">
            <h3>Use Cases</h3>
            <ul className="use-cases-list">
              <li>Early detection of compliance violations</li>
              <li>Guide architects toward compliant designs</li>
              <li>Pre-screen elements before rule checking</li>
              <li>Assist building inspectors in verification</li>
              <li>Learn from compliance patterns over time</li>
            </ul>
          </div>

          {/* Technical */}
          <div className="technical-section">
            <h3>Technical Details</h3>
            <div className="technical-content">
              <div className="tech-item">
                <h4>Feature Extraction</h4>
                <p>320-dimensional vectors from:</p>
                <ul>
                  <li>Element properties (type, dimensions)</li>
                  <li>Rule context (requirements)</li>
                  <li>Spatial relationships</li>
                  <li>Semantic context</li>
                </ul>
              </div>
              <div className="tech-item">
                <h4>Learning Process</h4>
                <p>Supervised learning pipeline:</p>
                <ul>
                  <li>Input: Element features</li>
                  <li>Target: Compliance status</li>
                  <li>Optimization: Minimize error</li>
                  <li>Validation: Monitor accuracy</li>
                </ul>
              </div>
              <div className="tech-item">
                <h4>Version Control</h4>
                <p>Each training creates:</p>
                <ul>
                  <li>Model weights checkpoint</li>
                  <li>Performance metrics</li>
                  <li>Training configuration</li>
                  <li>Dataset information</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      <style jsx>{`
        .trm-dashboard {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        }

        h1 {
          color: #333;
          margin-bottom: 20px;
        }

        .tabs {
          display: flex;
          gap: 10px;
          margin-bottom: 20px;
          border-bottom: 2px solid #eee;
        }

        .tabs button {
          padding: 10px 20px;
          border: none;
          background: none;
          cursor: pointer;
          color: #666;
          font-size: 16px;
          border-bottom: 3px solid transparent;
          transition: all 0.2s;
        }

        .tabs button.active {
          color: #0066cc;
          border-bottom-color: #0066cc;
        }

        .versions-list {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
        }

        .version-card {
          border: 1px solid #ddd;
          border-radius: 8px;
          padding: 20px;
          background: #f9f9f9;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .version-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .version-header h3 {
          margin: 0;
          color: #0066cc;
        }

        .badge-best {
          background: #28a745;
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: bold;
        }

        .version-date {
          color: #999;
          font-size: 14px;
          margin: 5px 0;
        }

        .metrics {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin: 15px 0;
          padding: 10px;
          background: white;
          border-radius: 4px;
        }

        .metric {
          display: flex;
          justify-content: space-between;
          font-size: 14px;
        }

        .metric .label {
          color: #666;
        }

        .metric .value {
          font-weight: bold;
          color: #333;
        }

        .actions {
          display: flex;
          gap: 10px;
          margin-top: 15px;
        }

        .actions button {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 4px;
          background: white;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s;
        }

        .actions button:hover {
          background: #0066cc;
          color: white;
          border-color: #0066cc;
        }

        .compare-action {
          text-align: center;
          margin-top: 20px;
          padding: 20px;
          background: #f0f0f0;
          border-radius: 8px;
        }

        .btn-primary {
          background: #0066cc;
          color: white;
          padding: 10px 20px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 16px;
        }

        .btn-primary:hover {
          background: #0052a3;
        }

        .section {
          margin: 20px 0;
          padding: 15px;
          border: 1px solid #ddd;
          border-radius: 8px;
          background: #f9f9f9;
        }

        .section h3 {
          margin-top: 0;
          color: #333;
        }

        .history-table, .comparison-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 10px;
        }

        .history-table th, .comparison-table th {
          background: #f0f0f0;
          padding: 10px;
          text-align: left;
          font-weight: bold;
          border-bottom: 2px solid #ddd;
        }

        .history-table td, .comparison-table td {
          padding: 10px;
          border-bottom: 1px solid #eee;
        }

        pre {
          background: white;
          padding: 10px;
          border-radius: 4px;
          overflow-x: auto;
          border: 1px solid #ddd;
        }
      `}</style>
    </div>
  );
};

export default TRMDashboard;
