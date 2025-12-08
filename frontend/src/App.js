import React, { useState } from 'react';
import { FileUp, Settings, Home, BarChart3 } from 'lucide-react';
import ElementsTab from './components/ElementsTab';
import RulesTab from './components/RulesTab';
import FileUploadModal from './components/FileUploadModal';
import PreviewConfirmationModal from './components/PreviewConfirmationModal';
import Sidebar from './components/Sidebar';
import DataLayerView from './components/DataLayerView';
import ElementsView from './components/ElementsView';
import ModelVisualizationView from './components/ModelVisualizationView';
import ExportView from './components/ExportView';
import RuleLayerView from './components/RuleLayerView';
import CheckRulesView from './components/CheckRulesView';
import DataValidationView from './components/DataValidationView';
import RuleCheckView from './components/RuleCheckView';
import ReasoningView from './components/ReasoningView';
import ResultsView from './components/ResultsView';
import ComplianceReportView from './components/ComplianceReportView';
import UnifiedConfigurationView from './components/UnifiedConfigurationView';
import TRMDashboard from './components/TRMDashboard';
import './App.css';

function App() {
  const [activeLayer, setActiveLayer] = useState('data-layer');
  
  // Stage 1: No file loaded
  const [showUploadModal, setShowUploadModal] = useState(false);
  
  // Stage 2: Preview loaded (waiting for confirmation)
  const [currentPreview, setCurrentPreview] = useState(null);
  const [currentSummary, setCurrentSummary] = useState(null);
  const [previewFileName, setPreviewFileName] = useState(null);
  const [previewFile, setPreviewFile] = useState(null);
  const [sourceFilePath, setSourceFilePath] = useState(null);
  
  // Stage 3: Graph built (ready to explore)
  const [currentGraph, setCurrentGraph] = useState(null);
  
  // Loading states
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileSelected = async (filePath) => {
    setLoading(true);
    setError(null);

    // Support both File object (from file picker) and string path (legacy)
    const isFile = filePath instanceof File;
    
    try {
      if (isFile) {
        setPreviewFileName(filePath.name);
        setPreviewFile(filePath);
        setSourceFilePath(filePath.webkitRelativePath || filePath.name);

        // Stage 2: Fetch preview only using dedicated preview endpoint
        const form = new FormData();
        form.append('file', filePath);

        const res = await fetch('/api/ifc/preview', {
          method: 'POST',
          body: form,
        });

        if (!res.ok) throw new Error('Failed to load preview');
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Upload failed');

        setCurrentPreview(data.preview);
        setCurrentSummary(data.summary);
        setShowUploadModal(false);
      } else {
        // Legacy path string fallback
        setPreviewFileName(filePath);
        setPreviewFile(filePath);
        setSourceFilePath(filePath);

        const previewRes = await fetch('/api/ifc/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ifc_path: filePath }),
        });

        if (!previewRes.ok) throw new Error('Failed to load preview');
        const previewData = await previewRes.json();
        if (!previewData.success) throw new Error(previewData.error);

        setCurrentPreview(previewData.preview);
        setCurrentSummary(previewData.summary);
        setShowUploadModal(false);
      }
    } catch (err) {
      setError(err.message || String(err));
      setCurrentPreview(null);
      setCurrentSummary(null);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAndBuildGraph = async () => {
    setLoading(true);
    setError(null);

    try {
      const isFile = previewFile instanceof File;

      if (isFile) {
        // Stage 3: Build graph from File
        const form = new FormData();
        form.append('file', previewFile);
        form.append('include_rules', 'true');

        const res = await fetch('/api/ifc/upload', {
          method: 'POST',
          body: form,
        });

        if (!res.ok) throw new Error('Failed to upload IFC file');
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Upload failed');

        setCurrentGraph(data.graph);
        // Keep preview data for Model Preview tab
        if (data.preview && data.summary) {
          setCurrentPreview(data.preview);
          setCurrentSummary(data.summary);
        }
        // Add source file path to graph
        if (data.graph) {
          data.graph.source_file = sourceFilePath || data.graph.source_file;
        }
        setActiveLayer('data-layer'); // Start with Data Layer
        // Close modal after successful build
        setCurrentPreview(null);
      } else {
        // Stage 3: Build graph from path string
        const graphRes = await fetch('/api/ifc/graph', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ifc_path: previewFile, include_rules: true }),
        });

        if (!graphRes.ok) throw new Error('Failed to build graph');
        const graphData = await graphRes.json();
        if (!graphData.success) throw new Error(graphData.error);

        setCurrentGraph(graphData.graph);
        // Keep preview data for Model Preview tab
        if (graphData.preview && graphData.summary) {
          setCurrentPreview(graphData.preview);
          setCurrentSummary(graphData.summary);
        }
        // Add source file path to graph
        if (graphData.graph) {
          graphData.graph.source_file = sourceFilePath || graphData.graph.source_file;
        }
        setActiveLayer('data-layer');
        // Close modal after successful build
        setCurrentPreview(null);
      }
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCancelPreview = () => {
    setCurrentPreview(null);
    setCurrentSummary(null);
    setPreviewFileName(null);
    setPreviewFile(null);
  };

  const handlePreviewAgain = async () => {
    if (!previewFile) {
      setError('No preview file available');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', previewFile);
      form.append('include_rules', 'false');
      const response = await fetch('/api/ifc/preview', { method: 'POST', body: form });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.success) {
        setCurrentPreview(data.preview);
        setCurrentSummary(data.summary);
      } else {
        setError(data.error || 'Failed to load preview');
      }
    } catch (err) {
      console.error('Preview error:', err);
      setError(`Failed to fetch preview: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
              <img src="/ace-x-logo.png" alt="ACE-X" style={{ height: '60px', width: 'auto' }} />
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'white', fontWeight: '500', textAlign: 'center' }}>The AEC Compliance Explainability Framework</p>
            </div>
          </div>
          <div className="header-right">
            <button
              className="btn btn-primary"
              onClick={() => setShowUploadModal(true)}
            >
              <FileUp size={18} />
              Browse IFC
            </button>
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Preview Confirmation Modal (Stage 2) */}
      {currentPreview && currentSummary && (
        <PreviewConfirmationModal
          preview={currentPreview}
          summary={currentSummary}
          fileName={previewFileName}
          onConfirm={handleConfirmAndBuildGraph}
          onCancel={handleCancelPreview}
          loading={loading}
        />
      )}

      {/* Main Content */}
      <main className="main-content">
        {loading && !currentPreview && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Processing IFC file...</p>
          </div>
        )}

        {!currentGraph && !currentPreview && !loading && (
          <div className="empty-state">
            <FileUp size={64} />
            <h2>No IFC File Loaded</h2>
            <p>Click "Browse IFC" to select a file and get started</p>
          </div>
        )}

        {currentGraph && (
          <div className="app-layout">
            {/* Sidebar */}
            <Sidebar
              currentGraph={currentGraph}
              onLayerSelect={setActiveLayer}
              activeLayer={activeLayer}
              onPreviewIFC={handlePreviewAgain}
              hasPreviewFile={!!previewFile}
            />

            {/* Main Content Area */}
            <div className="main-content-area">
              {/* Render Layer Views */}
              {activeLayer === 'data-layer' && <DataLayerView graph={currentGraph} summary={currentSummary} />}
              {activeLayer === 'elements' && <ElementsView graph={currentGraph} />}
              {activeLayer === 'model-visualization' && <ModelVisualizationView graph={currentGraph} />}
              {activeLayer === 'export' && <ExportView graph={currentGraph} />}
              {activeLayer === 'validation' && <DataValidationView graph={currentGraph} />}
              {activeLayer === 'rule-check' && <RuleCheckView graph={currentGraph} />}
              {activeLayer === 'rule-layer' && <RuleLayerView graph={currentGraph} />}
              {activeLayer === 'rule-config' && <UnifiedConfigurationView graph={currentGraph} />}
              {(activeLayer === 'reasoning-why' || activeLayer === 'reasoning-impact' || activeLayer === 'reasoning-fix') && (
                <ReasoningView graph={currentGraph} activeTab={activeLayer.replace('reasoning-', '')} />
              )}
              {activeLayer === 'trm-model' && <TRMDashboard />}
              {activeLayer === 'results' && <ResultsView graph={currentGraph} />}
              {activeLayer === 'compliance-report' && <ComplianceReportView graph={currentGraph} />}
            </div>
          </div>
        )}
      </main>

      {/* File Upload Modal */}
      {showUploadModal && (
        <FileUploadModal
          onFileSelected={handleFileSelected}
          onClose={() => setShowUploadModal(false)}
        />
      )}
    </div>
  );
}

export default App;
