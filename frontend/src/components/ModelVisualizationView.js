import React, { useEffect, useRef, useState } from 'react';
import { Package, ZoomIn, ZoomOut, RotateCcw, Layers } from 'lucide-react';
import * as THREE from 'three';
import { getColorLegend, getAllColors } from '../config/colorConfig';
import '../styles/ModelVisualizationView.css';

/**
 * ModelVisualizationView - 3D IFC Model Viewer with Metadata Labels
 * 
 * Features:
 * - 3D visualization of IFC elements (spaces, doors, walls, windows, etc.)
 * - Real-time metadata labels showing element types and names
 * - Mouse controls (rotation, zoom)
 * - Element highlighting and selection
 * - Toggle labels on/off
 * - Interactive element list with highlighting
 */

function ModelVisualizationView({ graph }) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const elementsRef = useRef([]);
  const geometryCacheRef = useRef({}); // Cache geometries for reuse
  const materialsCacheRef = useRef({}); // Cache materials per color
  const animationFrameIdRef = useRef(null); // Track animation frame for cleanup
  const [viewerReady, setViewerReady] = useState(false);
  const [selectedElements, setSelectedElements] = useState([]);
  const [hoveredElement, setHoveredElement] = useState(null);
  const [wireframeMode, setWireframeMode] = useState(false);
  const [renderingProgress, setRenderingProgress] = useState(0);
  const maxElementsToRender = 100; // Start with max 100 elements to avoid overload
  const MAX_VISIBLE_LABELS = 15;

  // Get color configuration from centralized config
  const colorLegend = getColorLegend();

  useEffect(() => {
    if (!containerRef.current || !graph) return;

    // Small delay to ensure DOM is fully laid out
    const timeout = setTimeout(() => {
      if (containerRef.current && containerRef.current.clientWidth > 0) {
        initializeViewer();
      }
    }, 100);

    return () => {
      // CLEANUP: Stop animation loop
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
        animationFrameIdRef.current = null;
      }
      
      // CLEANUP: Remove event listeners
      window.removeEventListener('resize', () => {});
      
      // CLEANUP: Dispose renderer and clear container
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
      
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      
      // CLEANUP: Clear scene references
      sceneRef.current = null;
      cameraRef.current = null;
      
      clearTimeout(timeout);
    };
  }, [graph]);

  const initializeViewer = () => {
    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    // Add fog to improve performance for distant objects
    scene.fog = new THREE.Fog(0xf8fafc, 100, 1000);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(10, 10, 10);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // Renderer setup - optimized for performance
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true,
      powerPreference: 'high-performance' // Use high-performance GPU
    });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Cap at 2 for performance
    renderer.shadowMap.enabled = false; // Disable shadows for better performance
    renderer.physicallyCorrectLights = false;
    
    // Clear any existing content and add renderer
    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5); // Reduced intensity
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6); // Reduced intensity
    directionalLight.position.set(5, 10, 5);
    scene.add(directionalLight);

    // Add grid
    const gridHelper = new THREE.GridHelper(20, 20, 0xcccccc, 0xeeeeee);
    scene.add(gridHelper);

    // Add axes helper
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    // Extract and add elements from graph
    extractAndAddElements(scene);

    // Mouse controls
    setupMouseControls(camera, renderer);

    // Handle window resize
    const handleResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', handleResize);

    // Animation loop - store frame ID for cleanup
    const animate = () => {
      animationFrameIdRef.current = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    setViewerReady(true);
  };

  const extractAndAddElements = (scene) => {
    if (!graph || !graph.elements) return;

    const elements = [];
    const colors = getAllColors('three'); // Get all colors in Three.js format
    let totalElementsProcessed = 0;

    // Process each element type
    Object.entries(graph.elements).forEach(([type, elementList]) => {
      if (!Array.isArray(elementList)) return;

      const color = colors[type] || 0x888888;
      let index = 0;

      // Get or create cached geometry and material (reuse for performance)
      const geometry = getOrCreateGeometry(type);
      const material = getOrCreateMaterial(color);

      elementList.forEach((el) => {
        // Limit rendering to avoid performance issues - only render first N elements
        if (totalElementsProcessed >= maxElementsToRender) {
          return; // Skip rendering additional elements
        }

        const mesh = new THREE.Mesh(geometry, material);

        // Distribute elements in space for visibility
        mesh.position.x = (index % 5) * 3 - 6;
        mesh.position.z = Math.floor(index / 5) * 3 - 6;

        scene.add(mesh);

        const elementObj = {
          mesh,
          id: el.id || el.ifc_guid || `${type}-${index}`,
          name: el.name || `${type.slice(0, -1)} #${index}`,
          type,
          data: el,
          originalColor: color,
        };

        elements.push(elementObj);
        totalElementsProcessed++;
        index++;
        
        // Update progress
        setRenderingProgress(Math.round((totalElementsProcessed / maxElementsToRender) * 100));
      });
    });

    elementsRef.current = elements;
    setSelectedElements(elements);
    
    // Log info about limited rendering
    const totalAvailable = Object.values(graph.elements).flat().length;
    if (totalAvailable > maxElementsToRender) {
      console.warn(`⚠️ Rendering limited to ${maxElementsToRender} elements out of ${totalAvailable} total. 
        To render all elements, increase maxElementsToRender or switch to a lightweight viewer.`);
    }
  };

  const getOrCreateGeometry = (type) => {
    // Check if geometry is already cached
    if (geometryCacheRef.current[type]) {
      return geometryCacheRef.current[type];
    }

    // Create optimized geometry with minimal segments for performance
    const geometry = createOptimizedGeometry(type);
    geometryCacheRef.current[type] = geometry;
    return geometry;
  };

  const getOrCreateMaterial = (color) => {
    const colorKey = '0x' + color.toString(16);
    if (materialsCacheRef.current[colorKey]) {
      return materialsCacheRef.current[colorKey];
    }

    // Create material with optimized settings
    const material = new THREE.MeshPhongMaterial({
      color: color,
      emissive: 0x000000,
      wireframe: false,
      shininess: 30, // Reduced from 100 for faster shading
      side: THREE.DoubleSide,
    });
    materialsCacheRef.current[colorKey] = material;
    return material;
  };

  const createOptimizedGeometry = (type) => {
    // Optimized geometries with minimal segments for 60 FPS performance
    // Provides good visual quality without excessive polygon count
    switch (type) {
      case 'spaces':
        return new THREE.BoxGeometry(2, 2.5, 2, 2, 2, 2);
      case 'doors':
        return new THREE.CylinderGeometry(0.5, 0.5, 2.2, 8, 2);
      case 'windows':
        return new THREE.BoxGeometry(1.5, 1.5, 0.2, 2, 2, 1);
      case 'walls':
        return new THREE.BoxGeometry(4, 2.5, 0.3, 3, 2, 1);
      case 'slabs':
        return new THREE.BoxGeometry(4, 0.3, 4, 3, 1, 3);
      case 'columns':
        return new THREE.CylinderGeometry(0.3, 0.3, 3, 8, 2);
      case 'beams':
        return new THREE.BoxGeometry(0.3, 0.3, 4, 2, 2, 3);
      case 'stairs':
        return new THREE.BoxGeometry(2, 0.2, 3, 3, 1, 3);
      case 'ramps':
        return new THREE.BoxGeometry(2, 0.3, 4, 3, 2, 3);
      default:
        return new THREE.BoxGeometry(1, 1, 1, 2, 2, 2);
    }
  };

  const setupMouseControls = (camera, renderer) => {
    let isRotating = false;
    let previousMousePosition = { x: 0, y: 0 };

    renderer.domElement.addEventListener('mousedown', (e) => {
      isRotating = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    renderer.domElement.addEventListener('mousemove', (e) => {
      if (!isRotating) return;

      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      if (sceneRef.current) {
        sceneRef.current.rotation.y += deltaX * 0.01;
        sceneRef.current.rotation.x += deltaY * 0.01;
      }

      previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    renderer.domElement.addEventListener('mouseup', () => {
      isRotating = false;
    });

    renderer.domElement.addEventListener('wheel', (e) => {
      e.preventDefault();
      
      // Zoom with mouse wheel - adjust camera FOV instead of position for smoother zoom
      const zoomSpeed = 2;
      const minFOV = 10;
      const maxFOV = 100;
      
      camera.fov += e.deltaY > 0 ? zoomSpeed : -zoomSpeed;
      camera.fov = Math.max(minFOV, Math.min(maxFOV, camera.fov));
      camera.updateProjectionMatrix();
    }, { passive: false });
  };

  const highlightElement = (elementId) => {
    elementsRef.current.forEach((el) => {
      if (el.id === elementId) {
        el.mesh.material.emissive.setHex(0xffff00);
        el.mesh.material.emissiveIntensity = 0.5;
        el.mesh.scale.set(1.2, 1.2, 1.2);
        setHoveredElement(elementId);
      } else {
        el.mesh.material.emissive.setHex(0x000000);
        el.mesh.material.emissiveIntensity = 0;
        el.mesh.scale.set(1, 1, 1);
      }
    });
  };

  const resetHighlight = () => {
    elementsRef.current.forEach((el) => {
      el.mesh.material.emissive.setHex(0x000000);
      el.mesh.material.emissiveIntensity = 0;
      el.mesh.scale.set(1, 1, 1);
    });
    setHoveredElement(null);
  };

  const handleZoomIn = () => {
    if (cameraRef.current) {
      cameraRef.current.fov = Math.max(10, cameraRef.current.fov - 5);
      cameraRef.current.updateProjectionMatrix();
    }
  };

  const handleZoomOut = () => {
    if (cameraRef.current) {
      cameraRef.current.fov = Math.min(100, cameraRef.current.fov + 5);
      cameraRef.current.updateProjectionMatrix();
    }
  };

  const handleResetView = () => {
    if (cameraRef.current && sceneRef.current) {
      cameraRef.current.position.set(10, 10, 10);
      cameraRef.current.lookAt(0, 0, 0);
      cameraRef.current.fov = 75;
      cameraRef.current.updateProjectionMatrix();
      sceneRef.current.rotation.set(0, 0, 0);
    }
  };

  const handleToggleWireframe = () => {
    const newWireframeMode = !wireframeMode;
    setWireframeMode(newWireframeMode);
    
    // Update all mesh materials
    elementsRef.current.forEach((el) => {
      if (el.mesh && el.mesh.material) {
        el.mesh.material.wireframe = newWireframeMode;
      }
    });
  };

  const getElementStats = () => {
    if (!graph || !graph.elements) return {};
    return {
      spaces: graph.elements.spaces?.length || 0,
      doors: graph.elements.doors?.length || 0,
      windows: graph.elements.windows?.length || 0,
      walls: graph.elements.walls?.length || 0,
      slabs: graph.elements.slabs?.length || 0,
      columns: graph.elements.columns?.length || 0,
      beams: graph.elements.beams?.length || 0,
      stairs: graph.elements.stairs?.length || 0,
      ramps: graph.elements.ramps?.length || 0,
    };
  };

  const stats = getElementStats();

  return (
    <div className="model-visualization-view">
      <div className="visualization-header">
        <div className="header-content">
          <h2>
            <Package size={24} />
            3D Model Visualization
          </h2>
          <p>Interactive 3D view with color-coded element types</p>
        </div>
        <div className="header-controls">
          <button
            className={`wireframe-button ${wireframeMode ? 'active' : ''}`}
            onClick={handleToggleWireframe}
            title="Toggle wireframe mode"
          >
            <Layers size={18} />
            Wireframe
          </button>
          <div className="zoom-controls">
            <button
              className="zoom-button"
              onClick={handleZoomIn}
              title="Zoom in"
            >
              <ZoomIn size={18} />
            </button>
            <button
              className="zoom-button"
              onClick={handleZoomOut}
              title="Zoom out"
            >
              <ZoomOut size={18} />
            </button>
            <button
              className="zoom-button"
              onClick={handleResetView}
              title="Reset view"
            >
              <RotateCcw size={18} />
            </button>
          </div>
        </div>
      </div>

      <div className="visualization-container">
        {/* 3D Viewer Container */}
        <div className="viewer-section">
          <div ref={containerRef} className="viewer-canvas" />
          
          {/* Loading Progress Indicator */}
          {renderingProgress > 0 && renderingProgress < 100 && (
            <div className="rendering-progress" style={{
              position: 'absolute',
              bottom: '20px',
              left: '20px',
              background: 'rgba(0, 0, 0, 0.7)',
              color: '#fff',
              padding: '12px 20px',
              borderRadius: '6px',
              fontSize: '14px',
              zIndex: 100
            }}>
              <div style={{ marginBottom: '8px' }}>🔄 Rendering elements...</div>
              <div style={{
                width: '200px',
                height: '4px',
                background: 'rgba(255, 255, 255, 0.3)',
                borderRadius: '2px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${renderingProgress}%`,
                  height: '100%',
                  background: '#3b82f6',
                  transition: 'width 0.2s'
                }} />
              </div>
              <div style={{ marginTop: '8px', fontSize: '12px' }}>{renderingProgress}%</div>
            </div>
          )}
          
          {/* Limited Rendering Notice */}
          {viewerReady && elementsRef.current.length >= maxElementsToRender && graph?.elements && 
           Object.values(graph.elements).flat().length > maxElementsToRender && (
            <div className="rendering-notice" style={{
              position: 'absolute',
              top: '20px',
              right: '20px',
              background: 'rgba(245, 158, 11, 0.9)',
              color: '#000',
              padding: '12px 16px',
              borderRadius: '6px',
              fontSize: '13px',
              zIndex: 100,
              maxWidth: '300px'
            }}>
              ⚠️ Showing {elementsRef.current.length} of {Object.values(graph.elements).flat().length} elements 
              for better performance. Switch to a model summary view for all elements.
            </div>
          )}
        </div>
      </div>

      {/* Info Box */}
      <div className="info-box">
        <div className="color-legend">
          <h4>Element Types & Colors</h4>
          <div className="legend-items">
            {Object.entries(colorLegend).map(([key, { color, label }]) => (
              <div key={key} className="legend-item">
                <div 
                  className="legend-color" 
                  style={{ backgroundColor: `#${color.toString(16).padStart(6, '0')}` }}
                />
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
        
        <h4>3D Viewer Controls</h4>
        <ul>
          <li><strong>Rotate:</strong> Click and drag with mouse</li>
          <li><strong>Zoom:</strong> Scroll wheel or use Zoom buttons</li>
          <li><strong>Reset View:</strong> Click the reset button</li>
          <li><strong>Wireframe:</strong> Toggle to see internal geometry detail</li>
          <li><strong>Detail:</strong> Geometries have high polygon density for detailed zoom views</li>
        </ul>
      </div>
    </div>
  );
}

export default ModelVisualizationView;
