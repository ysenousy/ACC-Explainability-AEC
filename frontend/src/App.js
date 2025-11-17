import React, { useState } from 'react';
import { FileUp, Settings, Home, BarChart3 } from 'lucide-react';
import PreviewTab from './components/PreviewTab';
import ElementsTab from './components/ElementsTab';
import RulesTab from './components/RulesTab';
import FileUploadModal from './components/FileUploadModal';
import PreviewConfirmationModal from './components/PreviewConfirmationModal';
import Sidebar from './components/Sidebar';
import DataLayerView from './components/DataLayerView';
import ElementsView from './components/ElementsView';
import RuleLayerView from './components/RuleLayerView';
import ReasoningView from './components/ReasoningView';
import ResultsView from './components/ResultsView';
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

        // Stage 2: Fetch preview only
        const form = new FormData();
        form.append('file', filePath);
        form.append('include_rules', 'false'); // Don't build graph yet

        const res = await fetch('/api/ifc/upload', {
          method: 'POST',
          body: form,
        });

        if (!res.ok) throw new Error('Failed to upload IFC file');
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Upload failed');

        setCurrentPreview(data.preview);
        setCurrentSummary(data.summary);
        setShowUploadModal(false);
      } else {
        // Legacy path string fallback
        setPreviewFileName(filePath);
        setPreviewFile(filePath);

        const previewRes = await fetch('/api/ifc/preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ifc_path: filePath }),
        });

        if (!previewRes.ok) throw new Error('Failed to load preview');
        const previewData = await previewRes.json();
        if (!previewData.success) throw new Error(previewData.error);

        setCurrentPreview(previewData.preview);
        setShowUploadModal(false);

        // For path strings, also fetch summary
        const graphRes = await fetch('/api/ifc/graph', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ifc_path: filePath, include_rules: false }),
        });

        if (!graphRes.ok) throw new Error('Failed to build graph');
        const graphData = await graphRes.json();
        if (!graphData.success) throw new Error(graphData.error);

        setCurrentSummary(graphData.summary);
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
        setActiveLayer('data-layer'); // Start with Data Layer
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
        setActiveLayer('data-layer');
      }

      // Clear preview state after graph is built
      setCurrentPreview(null);
      setCurrentSummary(null);
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

  return (
    <div className="App">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <Home size={28} className="logo" />
            <h1>IFC Explorer</h1>
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
            />

            {/* Main Content Area */}
            <div className="main-content-area">
              {/* Render Layer Views */}
              {activeLayer === 'data-layer' && <DataLayerView graph={currentGraph} />}
              {activeLayer === 'elements' && <ElementsView graph={currentGraph} />}
              {activeLayer === 'rule-layer' && <RuleLayerView graph={currentGraph} />}
              {activeLayer === 'reasoning' && <ReasoningView graph={currentGraph} />}
              {activeLayer === 'results' && <ResultsView graph={currentGraph} />}
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
