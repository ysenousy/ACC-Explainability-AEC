import React, { useState } from 'react';
import { X, Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react';

function EnhancedAddRuleForm({ onSave, onCancel }) {
  const [expandedSections, setExpandedSections] = useState({
    basic: true,
    target: true,
    condition: true,
    explanation: true
  });

  const [formData, setFormData] = useState({
    // Basic
    id: '',
    name: '',
    severity: 'ERROR',
    code_reference: '',
    regulation: '',
    description: '',

    // Target
    ifc_class: 'IfcSpace',
    filters: [], // Array of {type, pset, property, operator, value}

    // Condition
    lhs: {
      source_type: 'qto', // 'qto', 'pset', 'attribute'
      qto_name: '',
      quantity: '',
      pset_name: '',
      property: '',
      attribute: '',
      unit: 'mm'
    },
    condition_operator: '>=', // >=, >, <=, <, =, !=
    rhs: {
      type: 'constant', // 'constant' or 'parameter'
      value: '',
      parameter: '',
      unit: 'mm'
    },

    // Explanation
    short_message: '',
    on_fail: '',
    on_pass: ''
  });

  const [newFilter, setNewFilter] = useState({
    type: 'property', // 'property' or 'attribute'
    pset: '',
    property: '',
    operator: '=',
    value: ''
  });

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleAddFilter = () => {
    if (!newFilter.pset || !newFilter.property || !newFilter.value) {
      alert('Please fill in all filter fields');
      return;
    }
    setFormData(prev => ({
      ...prev,
      filters: [...prev.filters, { ...newFilter }]
    }));
    setNewFilter({
      type: 'property',
      pset: '',
      property: '',
      operator: '=',
      value: ''
    });
  };

  const handleRemoveFilter = (index) => {
    setFormData(prev => ({
      ...prev,
      filters: prev.filters.filter((_, i) => i !== index)
    }));
  };

  const handleSaveRule = () => {
    // Validate required fields
    if (!formData.id || !formData.name || !formData.ifc_class) {
      alert('Rule ID, Name, and IFC Class are required');
      return;
    }

    if (!formData.lhs.qto_name && !formData.lhs.pset_name && !formData.lhs.attribute) {
      alert('LHS source is required');
      return;
    }

    if (!formData.rhs.value && !formData.rhs.parameter) {
      alert('RHS value is required');
      return;
    }

    // Build rule object in enhanced format
    const rule = {
      id: formData.id,
      name: formData.name,
      rule_type: 'attribute_comparison',
      description: formData.description,
      
      target: {
        ifc_class: formData.ifc_class,
        selector: {
          filters: formData.filters.map(f => ({
            pset: f.pset,
            property: f.property,
            op: f.operator,
            value: f.value === 'true' ? true : f.value === 'false' ? false : f.value
          }))
        }
      },

      condition: {
        op: formData.condition_operator,
        lhs: buildLhsSource(),
        rhs: buildRhsSource()
      },

      parameters: buildParameters(),

      severity: formData.severity,

      explanation: {
        short: formData.short_message,
        on_fail: formData.on_fail,
        on_pass: formData.on_pass
      },

      provenance: {
        source: 'regulation',
        regulation: formData.regulation,
        section: formData.code_reference,
        jurisdiction: 'US'
      }
    };

    onSave(rule);
  };

  const buildLhsSource = () => {
    if (formData.lhs.source_type === 'qto') {
      return {
        source: 'qto',
        qto_name: formData.lhs.qto_name,
        quantity: formData.lhs.quantity,
        unit: formData.lhs.unit
      };
    } else if (formData.lhs.source_type === 'pset') {
      return {
        source: 'pset',
        pset_name: formData.lhs.pset_name,
        property: formData.lhs.property,
        unit: formData.lhs.unit
      };
    } else {
      return {
        source: 'attribute',
        attribute: formData.lhs.attribute,
        unit: formData.lhs.unit
      };
    }
  };

  const buildRhsSource = () => {
    if (formData.rhs.type === 'constant') {
      return {
        source: 'constant',
        value: parseFloat(formData.rhs.value) || formData.rhs.value,
        unit: formData.rhs.unit
      };
    } else {
      return {
        source: 'parameter',
        param: formData.rhs.parameter
      };
    }
  };

  const buildParameters = () => {
    if (formData.rhs.type === 'constant') {
      return {};
    } else {
      return {
        [formData.rhs.parameter]: parseFloat(formData.rhs.value) || formData.rhs.value
      };
    }
  };

  const sectionStyle = {
    marginBottom: '1.5rem',
    border: '1px solid #e5e7eb',
    borderRadius: '0.5rem',
    backgroundColor: '#fff'
  };

  const sectionHeaderStyle = {
    padding: '0.75rem 1rem',
    backgroundColor: '#f3f4f6',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    cursor: 'pointer',
    fontWeight: '600',
    fontSize: '0.95rem',
    border: 'none',
    width: '100%',
    textAlign: 'left'
  };

  const sectionContentStyle = {
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem'
  };

  const labelStyle = {
    display: 'block',
    fontSize: '0.875rem',
    fontWeight: '500',
    marginBottom: '0.5rem',
    color: '#1f2937'
  };

  const inputStyle = {
    width: '100%',
    padding: '0.5rem 0.75rem',
    border: '1px solid #d1d5db',
    borderRadius: '0.375rem',
    fontSize: '0.875rem',
    boxSizing: 'border-box'
  };

  return (
    <div style={{ maxHeight: '90vh', overflowY: 'auto', paddingRight: '0.5rem' }}>
      {/* BASIC SECTION */}
      <div style={sectionStyle}>
        <button
          onClick={() => toggleSection('basic')}
          style={sectionHeaderStyle}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#e5e7eb'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#f3f4f6'}
        >
          {expandedSections.basic ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          Basic
        </button>
        {expandedSections.basic && (
          <div style={sectionContentStyle}>
            <div>
              <label style={labelStyle}>Rule ID *</label>
              <input
                type="text"
                placeholder="ADA_CORRIDOR_MIN_WIDTH_1"
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>Name *</label>
              <input
                type="text"
                placeholder="ADA Corridor Minimum Width"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>Description</label>
              <textarea
                placeholder="Description of what this rule checks..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                style={{ ...inputStyle, minHeight: '80px', resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={labelStyle}>Severity *</label>
                <select
                  value={formData.severity}
                  onChange={(e) => setFormData({ ...formData, severity: e.target.value })}
                  style={inputStyle}
                >
                  <option value="ERROR">ERROR</option>
                  <option value="WARNING">WARNING</option>
                  <option value="INFO">INFO</option>
                </select>
              </div>

              <div>
                <label style={labelStyle}>Regulation</label>
                <input
                  type="text"
                  placeholder="Americans with Disabilities Act (ADA)"
                  value={formData.regulation}
                  onChange={(e) => setFormData({ ...formData, regulation: e.target.value })}
                  style={inputStyle}
                />
              </div>
            </div>

            <div>
              <label style={labelStyle}>Code Reference</label>
              <input
                type="text"
                placeholder="§403.5.1"
                value={formData.code_reference}
                onChange={(e) => setFormData({ ...formData, code_reference: e.target.value })}
                style={inputStyle}
              />
            </div>
          </div>
        )}
      </div>

      {/* TARGET SECTION */}
      <div style={sectionStyle}>
        <button
          onClick={() => toggleSection('target')}
          style={sectionHeaderStyle}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#e5e7eb'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#f3f4f6'}
        >
          {expandedSections.target ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          Target
        </button>
        {expandedSections.target && (
          <div style={sectionContentStyle}>
            <div>
              <label style={labelStyle}>IFC Class *</label>
              <select
                value={formData.ifc_class}
                onChange={(e) => setFormData({ ...formData, ifc_class: e.target.value })}
                style={inputStyle}
              >
                <option value="IfcDoor">IfcDoor</option>
                <option value="IfcSpace">IfcSpace</option>
                <option value="IfcWindow">IfcWindow</option>
                <option value="IfcWall">IfcWall</option>
                <option value="IfcSlab">IfcSlab</option>
                <option value="IfcStairFlight">IfcStairFlight</option>
                <option value="IfcColumn">IfcColumn</option>
                <option value="IfcBeam">IfcBeam</option>
              </select>
            </div>

            <div>
              <label style={labelStyle}>Filters</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {/* Existing Filters */}
                {formData.filters.map((filter, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '0.75rem',
                      backgroundColor: '#f0fdf4',
                      border: '1px solid #bbf7d0',
                      borderRadius: '0.375rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.875rem'
                    }}
                  >
                    <span>
                      <strong>{filter.pset}</strong> → {filter.property} {filter.operator} {filter.value}
                    </span>
                    <button
                      onClick={() => handleRemoveFilter(idx)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#dc2626',
                        color: 'white',
                        border: 'none',
                        borderRadius: '0.25rem',
                        cursor: 'pointer',
                        fontSize: '0.75rem'
                      }}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}

                {/* Add Filter Row */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(5, 1fr)',
                  gap: '0.5rem',
                  padding: '0.75rem',
                  backgroundColor: '#f9fafb',
                  border: '1px dashed #d1d5db',
                  borderRadius: '0.375rem'
                }}>
                  <select
                    value={newFilter.type}
                    onChange={(e) => setNewFilter({ ...newFilter, type: e.target.value })}
                    style={{ ...inputStyle, fontSize: '0.75rem' }}
                  >
                    <option value="property">Property</option>
                    <option value="attribute">Attribute</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Pset_SpaceCommon"
                    value={newFilter.pset}
                    onChange={(e) => setNewFilter({ ...newFilter, pset: e.target.value })}
                    style={{ ...inputStyle, fontSize: '0.75rem' }}
                  />

                  <input
                    type="text"
                    placeholder="Category"
                    value={newFilter.property}
                    onChange={(e) => setNewFilter({ ...newFilter, property: e.target.value })}
                    style={{ ...inputStyle, fontSize: '0.75rem' }}
                  />

                  <select
                    value={newFilter.operator}
                    onChange={(e) => setNewFilter({ ...newFilter, operator: e.target.value })}
                    style={{ ...inputStyle, fontSize: '0.75rem' }}
                  >
                    <option value="=">=</option>
                    <option value="!=">!=</option>
                    <option value=">">&gt;</option>
                    <option value="<">&lt;</option>
                  </select>

                  <input
                    type="text"
                    placeholder="Corridor"
                    value={newFilter.value}
                    onChange={(e) => setNewFilter({ ...newFilter, value: e.target.value })}
                    style={{ ...inputStyle, fontSize: '0.75rem' }}
                  />
                </div>

                <button
                  onClick={handleAddFilter}
                  style={{
                    padding: '0.5rem 0.75rem',
                    backgroundColor: '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '0.5rem'
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#059669'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = '#10b981'}
                >
                  <Plus size={16} />
                  Add Filter
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CONDITION SECTION */}
      <div style={sectionStyle}>
        <button
          onClick={() => toggleSection('condition')}
          style={sectionHeaderStyle}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#e5e7eb'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#f3f4f6'}
        >
          {expandedSections.condition ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          Condition
        </button>
        {expandedSections.condition && (
          <div style={sectionContentStyle}>
            {/* LHS */}
            <div style={{ paddingBottom: '1rem', borderBottom: '1px solid #e5e7eb' }}>
              <label style={{ ...labelStyle, marginBottom: '1rem' }}>Left Hand Side (LHS) *</label>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <label style={labelStyle}>Source Type</label>
                  <select
                    value={formData.lhs.source_type}
                    onChange={(e) => setFormData({
                      ...formData,
                      lhs: { ...formData.lhs, source_type: e.target.value }
                    })}
                    style={inputStyle}
                  >
                    <option value="qto">Quantity (Qto)</option>
                    <option value="pset">Property Set (PSet)</option>
                    <option value="attribute">Attribute</option>
                  </select>
                </div>

                <div>
                  <label style={labelStyle}>Unit</label>
                  <select
                    value={formData.lhs.unit}
                    onChange={(e) => setFormData({
                      ...formData,
                      lhs: { ...formData.lhs, unit: e.target.value }
                    })}
                    style={inputStyle}
                  >
                    <option value="mm">mm</option>
                    <option value="m">m</option>
                    <option value="m2">m²</option>
                    <option value="m3">m³</option>
                    <option value="count">count</option>
                  </select>
                </div>
              </div>

              {formData.lhs.source_type === 'qto' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={labelStyle}>QTO Name</label>
                    <input
                      type="text"
                      placeholder="Qto_SpaceBaseQuantities"
                      value={formData.lhs.qto_name}
                      onChange={(e) => setFormData({
                        ...formData,
                        lhs: { ...formData.lhs, qto_name: e.target.value }
                      })}
                      style={inputStyle}
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Quantity Name</label>
                    <input
                      type="text"
                      placeholder="Width"
                      value={formData.lhs.quantity}
                      onChange={(e) => setFormData({
                        ...formData,
                        lhs: { ...formData.lhs, quantity: e.target.value }
                      })}
                      style={inputStyle}
                    />
                  </div>
                </div>
              )}

              {formData.lhs.source_type === 'pset' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <label style={labelStyle}>PSet Name</label>
                    <input
                      type="text"
                      placeholder="Pset_SpaceCommon"
                      value={formData.lhs.pset_name}
                      onChange={(e) => setFormData({
                        ...formData,
                        lhs: { ...formData.lhs, pset_name: e.target.value }
                      })}
                      style={inputStyle}
                    />
                  </div>
                  <div>
                    <label style={labelStyle}>Property Name</label>
                    <input
                      type="text"
                      placeholder="Category"
                      value={formData.lhs.property}
                      onChange={(e) => setFormData({
                        ...formData,
                        lhs: { ...formData.lhs, property: e.target.value }
                      })}
                      style={inputStyle}
                    />
                  </div>
                </div>
              )}

              {formData.lhs.source_type === 'attribute' && (
                <div>
                  <label style={labelStyle}>Attribute Name</label>
                  <input
                    type="text"
                    placeholder="width_mm"
                    value={formData.lhs.attribute}
                    onChange={(e) => setFormData({
                      ...formData,
                      lhs: { ...formData.lhs, attribute: e.target.value }
                    })}
                    style={inputStyle}
                  />
                </div>
              )}
            </div>

            {/* OPERATOR AND RHS */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1rem', alignItems: 'flex-end' }}>
              <div>
                <label style={labelStyle}>Operator *</label>
                <select
                  value={formData.condition_operator}
                  onChange={(e) => setFormData({ ...formData, condition_operator: e.target.value })}
                  style={inputStyle}
                >
                  <option value=">=">&ge;</option>
                  <option value=">">></option>
                  <option value="<=">&le;</option>
                  <option value="<">&lt;</option>
                  <option value="=">=</option>
                  <option value="!=">≠</option>
                </select>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <label style={labelStyle}>RHS Type *</label>
                  <select
                    value={formData.rhs.type}
                    onChange={(e) => setFormData({
                      ...formData,
                      rhs: { ...formData.rhs, type: e.target.value }
                    })}
                    style={inputStyle}
                  >
                    <option value="constant">Constant</option>
                    <option value="parameter">Parameter</option>
                  </select>
                </div>

                <div>
                  <label style={labelStyle}>
                    {formData.rhs.type === 'constant' ? 'Value' : 'Parameter'} *
                  </label>
                  <input
                    type={formData.rhs.type === 'constant' ? 'number' : 'text'}
                    placeholder={formData.rhs.type === 'constant' ? '914' : 'min_corridor_width_mm'}
                    value={formData.rhs.value}
                    onChange={(e) => setFormData({
                      ...formData,
                      rhs: { ...formData.rhs, value: e.target.value }
                    })}
                    style={inputStyle}
                  />
                </div>
              </div>
            </div>

            {formData.rhs.type === 'constant' && (
              <div>
                <label style={labelStyle}>Unit</label>
                <select
                  value={formData.rhs.unit}
                  onChange={(e) => setFormData({
                    ...formData,
                    rhs: { ...formData.rhs, unit: e.target.value }
                  })}
                  style={inputStyle}
                >
                  <option value="mm">mm</option>
                  <option value="m">m</option>
                  <option value="m2">m²</option>
                  <option value="m3">m³</option>
                  <option value="count">count</option>
                </select>
              </div>
            )}
          </div>
        )}
      </div>

      {/* EXPLANATION SECTION */}
      <div style={sectionStyle}>
        <button
          onClick={() => toggleSection('explanation')}
          style={sectionHeaderStyle}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#e5e7eb'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#f3f4f6'}
        >
          {expandedSections.explanation ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
          Explanation & Messaging
        </button>
        {expandedSections.explanation && (
          <div style={sectionContentStyle}>
            <div>
              <label style={labelStyle}>Short Message</label>
              <textarea
                placeholder="Accessible corridors must be at least 914 mm wide."
                value={formData.short_message}
                onChange={(e) => setFormData({ ...formData, short_message: e.target.value })}
                style={{ ...inputStyle, minHeight: '60px', resize: 'vertical' }}
              />
              <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                Brief explanation of the rule
              </div>
            </div>

            <div>
              <label style={labelStyle}>On Fail Message</label>
              <textarea
                placeholder="Corridor {guid} has width {lhs} mm, below required {rhs} mm."
                value={formData.on_fail}
                onChange={(e) => setFormData({ ...formData, on_fail: e.target.value })}
                style={{ ...inputStyle, minHeight: '60px', resize: 'vertical' }}
              />
              <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                Variables: {'{guid}'}, {'{lhs}'}, {'{rhs}'}, {'{unit}'}
              </div>
            </div>

            <div>
              <label style={labelStyle}>On Pass Message</label>
              <textarea
                placeholder="Corridor {guid} meets the ADA width requirement ({lhs} mm ≥ {rhs} mm)."
                value={formData.on_pass}
                onChange={(e) => setFormData({ ...formData, on_pass: e.target.value })}
                style={{ ...inputStyle, minHeight: '60px', resize: 'vertical' }}
              />
              <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                Variables: {'{guid}'}, {'{lhs}'}, {'{rhs}'}, {'{unit}'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ACTION BUTTONS */}
      <div style={{
        display: 'flex',
        gap: '0.75rem',
        marginTop: '2rem',
        paddingTop: '1.5rem',
        borderTop: '1px solid #e5e7eb'
      }}>
        <button
          onClick={handleSaveRule}
          style={{
            flex: 1,
            padding: '0.75rem 1.5rem',
            backgroundColor: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontWeight: '600',
            fontSize: '0.95rem'
          }}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#2563eb'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#3b82f6'}
        >
          Save Rule
        </button>
        <button
          onClick={onCancel}
          style={{
            flex: 1,
            padding: '0.75rem 1.5rem',
            backgroundColor: '#e5e7eb',
            color: '#1f2937',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontWeight: '600',
            fontSize: '0.95rem'
          }}
          onMouseEnter={(e) => e.target.style.backgroundColor = '#d1d5db'}
          onMouseLeave={(e) => e.target.style.backgroundColor = '#e5e7eb'}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default EnhancedAddRuleForm;
