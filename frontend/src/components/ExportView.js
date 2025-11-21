import React, { useState, useCallback } from 'react';
import { Download, Copy, CheckCircle, Eye, ChevronDown, ChevronRight, Network } from 'lucide-react';
import ReactFlow, { 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState,
  MarkerType 
} from 'reactflow';
import 'reactflow/dist/style.css';

function ExportView({ graph }) {
  const [copied, setCopied] = useState(false);
  const [showVisualization, setShowVisualization] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState(new Set(['root']));
  const [showNodeGraph, setShowNodeGraph] = useState(false);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const handleDownloadJSON = () => {
    const jsonString = JSON.stringify(graph, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    // Extract filename from source_file path
    const sourceFile = graph.source_file || graph.building_id || 'graph';
    const fileName = sourceFile.split('\\').pop().split('/').pop().replace('.ifc', '') || 'graph';
    link.download = `${fileName}_dataLayer.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyToClipboard = () => {
    const jsonString = JSON.stringify(graph, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const toggleNode = (nodePath) => {
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodePath)) {
      newExpanded.delete(nodePath);
    } else {
      newExpanded.add(nodePath);
    }
    setExpandedNodes(newExpanded);
  };

  // Calculate hierarchical positions using tree algorithm
  const calculateTreePositions = (nodes, edges) => {
    const nodeWidth = 140;
    const nodeHeight = 70;
    const horizontalSpacing = 180;
    const verticalSpacing = 150;

    // Build adjacency map for parent-child relationships
    const children = {};
    edges.forEach(edge => {
      if (!children[edge.source]) children[edge.source] = [];
      children[edge.source].push(edge.target);
    });

    // Calculate subtree widths using post-order traversal
    const subtreeWidths = {};
    const calculateWidth = (nodeId) => {
      const childList = children[nodeId] || [];
      if (childList.length === 0) {
        subtreeWidths[nodeId] = nodeWidth + 20;
        return nodeWidth + 20;
      }
      const totalWidth = childList.reduce((sum, child) => sum + calculateWidth(child), 0);
      subtreeWidths[nodeId] = Math.max(totalWidth, nodeWidth + 20);
      return subtreeWidths[nodeId];
    };

    // Calculate positions using in-order traversal
    const positions = {};
    let xOffset = 0;

    const calculatePositions = (nodeId, depth) => {
      const childList = children[nodeId] || [];
      
      if (childList.length === 0) {
        positions[nodeId] = {
          x: xOffset,
          y: depth * verticalSpacing
        };
        xOffset += nodeWidth + 20;
      } else {
        const startX = xOffset;
        childList.forEach(child => calculatePositions(child, depth + 1));
        const endX = xOffset;
        positions[nodeId] = {
          x: (startX + endX) / 2 - nodeWidth / 2,
          y: depth * verticalSpacing
        };
      }
    };

    // Start from root
    const rootId = nodes.find(n => n.data.label === 'Graph Root')?.id;
    if (rootId) {
      calculateWidth(rootId);
      calculatePositions(rootId, 0);
    }

    // Center the entire tree
    const xPositions = Object.values(positions).map(p => p.x);
    const minX = Math.min(...xPositions);
    const maxX = Math.max(...xPositions);
    const centerOffset = (maxX - minX) / 2 + minX;

    // Update node positions
    return nodes.map(node => ({
      ...node,
      position: {
        x: (positions[node.id]?.x || 0) - centerOffset,
        y: positions[node.id]?.y || 0
      }
    }));
  };

  const generateNodeGraph = useCallback(() => {
    if (!graph) return;

    const generatedNodes = [];
    const generatedEdges = [];
    let nodeId = 0;

    // Create root node
    const rootNodeId = `node-root`;
    generatedNodes.push({
      id: rootNodeId,
      data: { label: 'Graph Root' },
      position: { x: 0, y: 0 },
      style: {
        background: '#667eea',
        color: '#fff',
        border: '2px solid #5568d3',
        borderRadius: '8px',
        padding: '10px 15px',
        fontSize: '12px',
        fontWeight: '600',
        textAlign: 'center',
        width: '120px'
      }
    });

    // Process main properties
    const mainProps = Object.entries(graph);
    const mainPropertyNodes = {};
    
    mainProps.forEach(([key, value]) => {
      const childNodeId = `node-${nodeId++}`;
      const isArray = Array.isArray(value);
      const count = isArray ? value.length : (typeof value === 'object' && value !== null ? Object.keys(value).length : 1);
      const preview = isArray ? `[${count}]` : (typeof value === 'object' ? `{${count}}` : String(value).substring(0, 20));
      
      mainPropertyNodes[key] = childNodeId;
      
      generatedNodes.push({
        id: childNodeId,
        data: { label: `${key}\n${preview}` },
        position: { x: 0, y: 0 }, // Will be updated by tree algorithm
        style: {
          background: typeof value === 'object' ? '#8b5cf6' : '#3b82f6',
          color: '#fff',
          border: '2px solid ' + (typeof value === 'object' ? '#7c3aed' : '#2563eb'),
          borderRadius: '8px',
          padding: '10px',
          fontSize: '11px',
          textAlign: 'center',
          width: '140px',
          minHeight: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }
      });
      
      // Create edge from root to main property
      generatedEdges.push({
        id: `edge-root-${childNodeId}`,
        source: rootNodeId,
        target: childNodeId,
        markerEnd: { type: MarkerType.ArrowClosed },
        style: { stroke: '#999', strokeWidth: 2 }
      });

      // Process nested elements if it's an object with elements
      if (key === 'elements' && typeof value === 'object' && value !== null) {
        Object.entries(value).forEach(([elemType, elemData]) => {
          const elemCount = Array.isArray(elemData) ? elemData.length : 1;
          const elemNodeId = `node-${nodeId++}`;
          
          generatedNodes.push({
            id: elemNodeId,
            data: { label: `${elemType}\n${elemCount} items` },
            position: { x: 0, y: 0 }, // Will be updated by tree algorithm
            style: {
              background: '#10b981',
              color: '#fff',
              border: '2px solid #059669',
              borderRadius: '6px',
              padding: '8px',
              fontSize: '10px',
              textAlign: 'center',
              width: '120px',
              minHeight: '50px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }
          });
          
          generatedEdges.push({
            id: `edge-elem-${elemNodeId}`,
            source: childNodeId,
            target: elemNodeId,
            markerEnd: { type: MarkerType.ArrowClosed },
            style: { stroke: '#999', strokeWidth: 1.5 }
          });
        });
      }
    });

    // Apply hierarchical tree positioning
    const positionedNodes = calculateTreePositions(generatedNodes, generatedEdges);

    setNodes(positionedNodes);
    setEdges(generatedEdges);
  }, [graph, setNodes, setEdges]);

  const handleShowNodeGraph = () => {
    if (!showNodeGraph) {
      generateNodeGraph();
    }
    setShowNodeGraph(!showNodeGraph);
  };

  const renderTreeNode = (value, key, path = 'root', depth = 0) => {
    const nodePath = `${path}.${key}`;
    const isExpanded = expandedNodes.has(nodePath);
    const isContainer = typeof value === 'object' && value !== null;
    const isArray = Array.isArray(value);
    const childCount = isArray ? value.length : (isContainer ? Object.keys(value).length : 0);

    const getValuePreview = () => {
      if (value === null) return 'null';
      if (typeof value === 'string') return `"${value.substring(0, 50)}${value.length > 50 ? '...' : ''}"`;
      if (typeof value === 'boolean') return value ? 'true' : 'false';
      if (typeof value === 'number') return value.toString();
      return '';
    };

    return (
      <div key={nodePath} style={{ marginLeft: `${depth * 20}px` }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '4px 8px',
            borderRadius: '4px',
            cursor: isContainer ? 'pointer' : 'default',
            backgroundColor: depth % 2 === 0 ? 'transparent' : '#f9f9f9',
            fontSize: '0.9rem',
            fontFamily: 'monospace'
          }}
          onClick={() => isContainer && toggleNode(nodePath)}
        >
          {isContainer ? (
            <span style={{ color: '#666', marginRight: '6px', width: '20px' }}>
              {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            </span>
          ) : (
            <span style={{ width: '26px' }} />
          )}
          <span style={{ color: '#8b5cf6', fontWeight: '600' }}>{key}</span>
          <span style={{ color: '#999', margin: '0 8px' }}>:</span>
          {!isContainer && <span style={{ color: '#059669' }}>{getValuePreview()}</span>}
          {isContainer && (
            <span style={{ color: '#999', marginLeft: '8px' }}>
              {isArray ? `[${childCount}]` : `{${childCount}}`}
            </span>
          )}
        </div>
        {isExpanded && isContainer && (
          <div>
            {isArray ? (
              value.map((item, index) => renderTreeNode(item, `[${index}]`, nodePath, depth + 1))
            ) : (
              Object.entries(value).map(([k, v]) => renderTreeNode(v, k, nodePath, depth + 1))
            )}
          </div>
        )}
      </div>
    );
  };

  // Early return if no graph loaded (after all hooks)
  if (!graph) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>No IFC file loaded</p>
      </div>
    );
  }

  const jsonString = JSON.stringify(graph, null, 2);
  const fileSizeKB = (new Blob([jsonString]).size / 1024).toFixed(2);

  return (
    <div className="layer-view">
      <div className="layer-header">
        <Download size={24} />
        <h2>Export Data Layer</h2>
      </div>

      <div className="layer-content">
        {/* Export Info */}
        <div className="info-section">
          <h3>JSON Graph Export</h3>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Export the extracted IFC data as a structured JSON graph for use in the Rule Layer or external processing.
          </p>
          <table className="info-table">
            <tbody>
              <tr>
                <td><strong>Source File:</strong></td>
                <td style={{ wordBreak: 'break-all' }}>{graph.source_file || 'Unknown'}</td>
              </tr>
              <tr>
                <td><strong>File Size:</strong></td>
                <td>{fileSizeKB} KB</td>
              </tr>
              <tr>
                <td><strong>Generated:</strong></td>
                <td>{new Date(graph.generated_at).toLocaleString()}</td>
              </tr>
              <tr>
                <td><strong>Elements:</strong></td>
                <td>
                  {Object.entries(graph.elements || {})
                    .map(([type, items]) => `${type}: ${Array.isArray(items) ? items.length : 0}`)
                    .join(', ')}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Export Actions */}
        <div className="info-section">
          <h3>Export Options</h3>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <button
              onClick={handleDownloadJSON}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Download size={18} />
              Download JSON
            </button>
            <button
              onClick={handleCopyToClipboard}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                background: copied ? '#10b981' : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              {copied ? (
                <>
                  <CheckCircle size={18} />
                  Copied!
                </>
              ) : (
                <>
                  <Copy size={18} />
                  Copy to Clipboard
                </>
              )}
            </button>
            <button
              onClick={() => setShowVisualization(!showVisualization)}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                background: showVisualization ? '#f59e0b' : '#8b5cf6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Eye size={18} />
              {showVisualization ? 'Hide' : 'Visualize'} Graph
            </button>
            <button
              onClick={handleShowNodeGraph}
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '1rem',
                background: showNodeGraph ? '#06b6d4' : '#14b8a6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}
            >
              <Network size={18} />
              {showNodeGraph ? 'Hide' : 'Show'} Node Graph
            </button>
          </div>
        </div>

        {/* JSON Tree Visualization */}
        {showVisualization && (
          <div className="info-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3>JSON Structure Visualization</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  onClick={() => setExpandedNodes(new Set(Object.keys(graph)))}
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    background: '#e5e7eb',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  Expand All
                </button>
                <button
                  onClick={() => setExpandedNodes(new Set(['root']))}
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.9rem',
                    background: '#e5e7eb',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontWeight: '500'
                  }}
                >
                  Collapse All
                </button>
              </div>
            </div>
            <div
              style={{
                background: '#f5f5f5',
                padding: '1rem',
                borderRadius: '6px',
                overflow: 'auto',
                maxHeight: '500px',
                fontSize: '0.85rem',
                lineHeight: '1.6',
                border: '1px solid #ddd',
                fontFamily: 'monospace'
              }}
            >
              {Object.entries(graph).map(([key, value]) => renderTreeNode(value, key, 'root', 0))}
            </div>
          </div>
        )}

        {/* Interactive Node Graph */}
        {showNodeGraph && (
          <div className="info-section">
            <h3>Interactive Node Graph</h3>
            <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.9rem' }}>
              Drag nodes to rearrange, zoom with mouse wheel, pan by dragging background
            </p>
            <div
              style={{
                width: '100%',
                height: '500px',
                border: '2px solid #ddd',
                borderRadius: '6px',
                overflow: 'hidden',
                background: '#fafafa'
              }}
            >
              <ReactFlow nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}>
                <Background />
                <Controls />
              </ReactFlow>
            </div>
          </div>
        )}

        {/* JSON Preview */}
        <div className="info-section">
          <h3>JSON Preview</h3>
          <pre
            style={{
              background: '#f5f5f5',
              padding: '1rem',
              borderRadius: '6px',
              overflow: 'auto',
              maxHeight: '400px',
              fontSize: '0.85rem',
              lineHeight: '1.5',
              border: '1px solid #ddd'
            }}
          >
            {jsonString}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default ExportView;
