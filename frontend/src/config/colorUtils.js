/**
 * Color utilities for consistent color handling across the application
 */

import { ELEMENT_COLORS, hexToThree, threeToHex } from './colorConfig';

/**
 * Create a CSS class for an element type with its color
 * @param {string} elementType - The element type
 * @param {string} property - CSS property to set (default: 'backgroundColor')
 * @returns {Object} Style object for React
 */
export const getElementTypeStyle = (elementType, property = 'backgroundColor') => {
  const color = ELEMENT_COLORS[elementType];
  if (!color) {
    console.warn(`Unknown element type: ${elementType}`);
    return { [property]: '#888888' };
  }
  return { [property]: color.hex };
};

/**
 * Create a badge style for element types
 * @param {string} elementType - The element type
 * @returns {Object} Style object with background, text color, and other badge styles
 */
export const getElementBadgeStyle = (elementType) => {
  const color = ELEMENT_COLORS[elementType];
  if (!color) {
    return { backgroundColor: '#888888', color: '#ffffff' };
  }
  
  return {
    backgroundColor: color.hex,
    color: getContrastingTextColor(color.hex),
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '600',
    whiteSpace: 'nowrap'
  };
};

/**
 * Get text color that contrasts well with the given background
 * @param {string} hexColor - Background color in hex format
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

/**
 * Get all element types with their current colors
 * @returns {Array} Array of objects with type, label, hex, and three color values
 */
export const getElementTypesWithColors = () => {
  return Object.entries(ELEMENT_COLORS).map(([type, colorData]) => ({
    type,
    label: colorData.label,
    hex: colorData.hex,
    three: colorData.three,
    description: colorData.description
  }));
};

/**
 * Create a color swatch component style
 * @param {string} elementType - The element type
 * @returns {Object} Style object for a color swatch
 */
export const getColorSwatchStyle = (elementType) => {
  const color = ELEMENT_COLORS[elementType];
  if (!color) {
    return {
      width: '24px',
      height: '24px',
      backgroundColor: '#888888',
      borderRadius: '4px',
      border: '1px solid rgba(0, 0, 0, 0.1)'
    };
  }
  
  return {
    width: '24px',
    height: '24px',
    backgroundColor: color.hex,
    borderRadius: '4px',
    border: '1px solid rgba(0, 0, 0, 0.1)'
  };
};

/**
 * Validate if an element type has a defined color
 * @param {string} elementType - The element type to validate
 * @returns {boolean} True if color is defined
 */
export const isValidElementType = (elementType) => {
  return elementType in ELEMENT_COLORS;
};

/**
 * Get a list of all valid element types
 * @returns {Array} Array of element type strings
 */
export const getValidElementTypes = () => {
  return Object.keys(ELEMENT_COLORS);
};

export default {
  getElementTypeStyle,
  getElementBadgeStyle,
  getContrastingTextColor,
  getElementTypesWithColors,
  getColorSwatchStyle,
  isValidElementType,
  getValidElementTypes
};
