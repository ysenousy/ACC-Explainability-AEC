/**
 * Centralized Color Configuration for ACC Explainability
 * This module provides consistent color schemes across the entire application
 */

export const ELEMENT_COLORS = {
  spaces: {
    hex: '#3b82f6',      // Blue
    rgb: 'rgb(59, 130, 246)',
    three: 0x3b82f6,     // Three.js format
    label: 'Spaces',
    description: 'Interior spaces and rooms'
  },
  walls: {
    hex: '#22c55e',      // Green
    rgb: 'rgb(34, 197, 94)',
    three: 0x22c55e,
    label: 'Walls',
    description: 'Wall elements'
  },
  doors: {
    hex: '#ef4444',      // Red
    rgb: 'rgb(239, 68, 68)',
    three: 0xef4444,
    label: 'Doors',
    description: 'Door openings'
  },
  windows: {
    hex: '#06b6d4',      // Cyan
    rgb: 'rgb(6, 182, 212)',
    three: 0x06b6d4,
    label: 'Windows',
    description: 'Window openings'
  },
  slabs: {
    hex: '#f59e0b',      // Amber
    rgb: 'rgb(245, 158, 11)',
    three: 0xf59e0b,
    label: 'Slabs',
    description: 'Floor and ceiling slabs'
  },
  columns: {
    hex: '#8b5cf6',      // Purple
    rgb: 'rgb(139, 92, 246)',
    three: 0x8b5cf6,
    label: 'Columns',
    description: 'Structural columns'
  },
  beams: {
    hex: '#ec4899',      // Pink
    rgb: 'rgb(236, 72, 153)',
    three: 0xec4899,
    label: 'Beams',
    description: 'Structural beams'
  },
  stairs: {
    hex: '#a855f7',      // Violet
    rgb: 'rgb(168, 85, 247)',
    three: 0xa855f7,
    label: 'Stairs',
    description: 'Staircase elements'
  },
  ramps: {
    hex: '#14b8a6',      // Teal
    rgb: 'rgb(20, 184, 166)',
    three: 0x14b8a6,
    label: 'Ramps',
    description: 'Ramp elements'
  }
};

/**
 * Get color by element type in specified format
 * @param {string} elementType - The element type (e.g., 'walls', 'doors')
 * @param {string} format - Color format: 'hex', 'rgb', or 'three' (default: 'three')
 * @returns {string|number} Color in requested format
 */
export const getColor = (elementType, format = 'three') => {
  const color = ELEMENT_COLORS[elementType];
  if (!color) {
    console.warn(`Unknown element type: ${elementType}`);
    return format === 'three' ? 0x888888 : '#888888';
  }
  return color[format];
};

/**
 * Get all colors as an object mapped by type
 * @param {string} format - Color format: 'hex', 'rgb', or 'three' (default: 'three')
 * @returns {Object} Object with element types as keys and colors in requested format
 */
export const getAllColors = (format = 'three') => {
  const result = {};
  Object.entries(ELEMENT_COLORS).forEach(([type, colorData]) => {
    result[type] = colorData[format];
  });
  return result;
};

/**
 * Get color legend for UI display
 * @returns {Object} Object with element types mapped to {color, label, description}
 */
export const getColorLegend = () => {
  const legend = {};
  Object.entries(ELEMENT_COLORS).forEach(([type, colorData]) => {
    legend[type] = {
      color: colorData.three,      // For Three.js rendering
      label: colorData.label,       // For UI display
      hex: colorData.hex,           // For CSS styling
      description: colorData.description
    };
  });
  return legend;
};

/**
 * Convert hex color to Three.js format (number)
 * @param {string} hex - Hex color string (e.g., '#ff0000')
 * @returns {number} Three.js format color
 */
export const hexToThree = (hex) => {
  return parseInt(hex.replace('#', ''), 16);
};

/**
 * Convert Three.js color to hex format
 * @param {number} threeColor - Three.js format color
 * @returns {string} Hex color string (e.g., '#ff0000')
 */
export const threeToHex = (threeColor) => {
  return `#${threeColor.toString(16).padStart(6, '0')}`;
};

/**
 * Get a contrasting text color (black or white) for a background color
 * @param {string} hexColor - Hex color string
 * @returns {string} '#000000' or '#ffffff'
 */
export const getContrastingTextColor = (hexColor) => {
  const hex = hexColor.replace('#', '');
  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);
  const brightness = (r * 299 + g * 587 + b * 114) / 1000;
  return brightness > 128 ? '#000000' : '#ffffff';
};

export default ELEMENT_COLORS;
