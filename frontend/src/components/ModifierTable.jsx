import React, { useState } from 'react';
import { Calculator, Info } from 'lucide-react';
import EvidenceSources from './EvidenceSources';
import { downloadReportHtml, printReportPdf } from './EvidenceReportGenerator';
import { modifierMetadata } from './modifierMetadata';

export default function ModifierTable({ data, isAdminMode, verdictData, autoExpandIndex }) {
  const [expandedModifiers, setExpandedModifiers] = useState(
    autoExpandIndex !== undefined ? { [data[autoExpandIndex]?.id]: true } : {}
  );
  const [adminExpanded, setAdminExpanded] = useState({});

  if (!data) return null;
  
  const toggleExpand = (id) => {
    setExpandedModifiers(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const toggleAdminExpand = (id) => {
    setAdminExpanded(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const handleDownloadHtml = () => {
    downloadReportHtml(data, verdictData?.target_entity?.name, verdictData?.final_verdict);
  };

  const handlePrintPdf = () => {
    printReportPdf(data, verdictData?.target_entity?.name, verdictData?.final_verdict);
  };

  return (
    <>
      <div className="glass-panel" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '24px 24px 16px 24px', position: 'sticky', top: 0, background: 'var(--bg-surface)', zIndex: 11, borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Calculator size={20} color="var(--accent-orange)" /> Underwriter Modifiers
          </h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button 
              onClick={handleDownloadHtml}
              style={{
                background: 'var(--accent-orange)', color: '#fff', border: 'none', 
                padding: '6px 12px', borderRadius: '6px', fontSize: '0.8rem', 
                fontWeight: '700', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
              }}
            >
              Download HTML
            </button>
            <button 
              onClick={handlePrintPdf}
              style={{
                background: '#0F172A', color: '#fff', border: 'none', 
                padding: '6px 12px', borderRadius: '6px', fontSize: '0.8rem', 
                fontWeight: '700', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
              }}
            >
              Save PDF
            </button>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(0,0,0,0.05)', padding: '6px 12px', borderRadius: '20px' }}>
              <Info size={14} color="var(--accent-orange)" /> Actuarial logic derived from CNA underwriting matrix
            </div>
          </div>
        </div>
        <div style={{ width: '100%', overflowX: 'auto', background: '#FFFFFF', borderRadius: '0 0 8px 8px' }}>
          <table style={{ width: '100%', minWidth: '1200px', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead style={{ background: '#F8FAFC', borderBottom: '2px solid #E2E8F0' }}>
              <tr>
                <th style={{ padding: '16px 24px', fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748B', fontWeight: '800', letterSpacing: '0.05em', width: '40px' }}>#</th>
                <th style={{ padding: '16px 24px', fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748B', fontWeight: '800', letterSpacing: '0.05em', width: '250px' }}>Modifier Name</th>
                {isAdminMode && <th style={{ padding: '16px 24px', fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748B', fontWeight: '800', letterSpacing: '0.05em', width: '120px' }}>Raw Score</th>}
                {isAdminMode && <th style={{ padding: '16px 24px', fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748B', fontWeight: '800', letterSpacing: '0.05em', width: '180px' }}>Scale</th>}
                {isAdminMode && <th style={{ padding: '16px 24px', fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748B', fontWeight: '800', letterSpacing: '0.05em', width: '250px' }}>Scoring Logic</th>}
                <th style={{ padding: '16px 24px', fontSize: '0.7rem', textTransform: 'uppercase', color: '#64748B', fontWeight: '800', letterSpacing: '0.05em', width: '200px' }}>Category Rating</th>
              </tr>
            </thead>
            <tbody>
              {data.map((mod, index) => {
                const meta = modifierMetadata[mod.name] || { scale: "Variable", logic: "Derived dynamically based on inputs" };
                
                // Premium Badge Generator
                const r = mod.rating.toUpperCase();
                let colors = { bg: '#F8FAFC', text: '#64748B', border: '#E2E8F0' }; // Default Slate
                if (r === 'VERY FAVOURABLE' || r.includes('VERY FAVOURABLE')) {
                  colors = { bg: '#ECFDF5', text: '#059669', border: '#A7F3D0' };
                } else if (r === 'PARTIALLY FAVOURABLE' || (r.includes('PARTIALLY FAVOURABLE') && !r.includes('UNFAVOURABLE'))) {
                  colors = { bg: '#FEF3C7', text: '#D97706', border: '#FDE68A' };
                } else if (r === 'FAVOURABLE' || (r.includes('FAVOURABLE') && !r.includes('PARTIALLY') && !r.includes('UNFAVOURABLE'))) {
                  colors = { bg: '#F0FDF4', text: '#16A34A', border: '#BBF7D0' };
                } else if (r === 'PARTIALLY UNFAVOURABLE' || r.includes('PARTIALLY UNFAVOURABLE')) {
                  colors = { bg: '#FFF7ED', text: '#C2410C', border: '#FFEDD5' };
                } else if (r === 'UNFAVOURABLE' || r.includes('UNFAVOURABLE')) {
                  colors = { bg: '#FEF2F2', text: '#DC2626', border: '#FECACA' };
                }

                const colSpan = isAdminMode ? 6 : 3;
                const isExpanded = expandedModifiers[mod.id];
                
                // Card style helper
                const cardStyle = {
                  background: '#FFFFFF',
                  borderRadius: '8px',
                  padding: '16px',
                  border: '1px solid #E2E8F0',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                };
                
                const cardHeaderStyle = { margin: '0 0 4px 0', color: '#0F172A', fontSize: '0.9rem', fontWeight: '700' };

                return (
                <React.Fragment key={mod.id}>
                  <tr style={{ 
                    borderBottom: ((index === data.length - 1) && !isExpanded) ? 'none' : '1px solid #F1F5F9',
                    transition: 'background 0.2s ease',
                    background: '#FFFFFF'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#F8FAFC'}
                  onMouseLeave={(e) => e.currentTarget.style.background = '#FFFFFF'}
                  >
                    <td style={{ padding: '20px 24px', fontSize: '0.8rem', color: '#94A3B8', fontWeight: '800', fontFamily: 'monospace' }}>
                      {String(mod.id).padStart(2, '0')}
                    </td>
                    <td style={{ padding: '20px 24px', fontWeight: '800', color: '#0F172A', fontSize: '0.9rem', whiteSpace: 'nowrap' }}>
                      {mod.name}
                    </td>
                    
                    {isAdminMode && (
                      <td style={{ padding: '20px 24px' }}>
                        <span style={{ 
                          fontFamily: 'monospace', color: '#F26A21', fontWeight: '800', 
                          background: 'rgba(242, 106, 33, 0.1)', border: '1px solid rgba(242, 106, 33, 0.2)',
                          padding: '4px 10px', borderRadius: '6px', fontSize: '0.85rem'
                        }}>
                          {mod.score}
                        </span>
                      </td>
                    )}
                    {isAdminMode && (
                      <td style={{ padding: '20px 24px', fontSize: '0.8rem', color: '#64748B', fontWeight: '600' }}>
                        {meta.scale}
                      </td>
                    )}
                    {isAdminMode && (
                      <td style={{ padding: '20px 24px', fontSize: '0.8rem', color: '#475569', lineHeight: '1.5' }}>
                        {meta.logic}
                      </td>
                    )}
                    
                    <td style={{ padding: '20px 24px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <span style={{ 
                            background: colors.bg, 
                            color: colors.text, 
                            border: `1px solid ${colors.border}`, 
                            padding: '6px 12px', 
                            borderRadius: '6px', 
                            fontSize: '0.7rem', 
                            fontWeight: '800', 
                            letterSpacing: '0.05em', 
                            display: 'inline-flex', 
                            alignItems: 'center', 
                            gap: '6px',
                            boxShadow: '0 1px 2px rgba(0,0,0,0.02)'
                          }}>
                            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: colors.text }}></div>
                            {r}
                          </span>
                        </div>
                        
                        <div style={{ marginTop: '4px' }}>
                          <button 
                            onClick={() => toggleExpand(mod.id)}
                            style={{ 
                              background: 'none', border: 'none', padding: 0, 
                              color: '#3B82F6', fontSize: '0.8rem', fontWeight: '600', 
                              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px',
                              transition: 'color 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.target.style.color = '#2563EB'}
                            onMouseLeave={(e) => e.target.style.color = '#3B82F6'}
                          >
                            Decision Rationale 
                            <span style={{ 
                              display: 'inline-block', 
                              transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)', 
                              transition: 'transform 0.3s ease',
                              fontSize: '0.6rem'
                            }}>
                              ▼
                            </span>
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                  
                  {isExpanded && (
                    <tr style={{ background: '#F8FAFC', borderBottom: (index === data.length - 1) ? 'none' : '1px solid #E2E8F0' }}>
                      <td colSpan={colSpan} style={{ padding: '24px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                          
                          {/* Decision Summary */}
                          <div style={cardStyle}>
                            <h4 style={cardHeaderStyle}>Decision Summary</h4>
                            {typeof mod.rationale === 'object' && mod.rationale !== null ? (
                              <>
                                <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.5', marginBottom: '16px' }}>
                                  {mod.rationale.decision_summary}
                                </div>
                                
                                {/* Input Values */}
                                <div style={{ borderTop: '1px solid #F1F5F9', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>Input Values <span style={{ color: '#94A3B8' }}>↓</span></h5>
                                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', background: '#F8FAFC', padding: '8px', borderRadius: '4px' }}>
                                    {(mod.rationale.input_values || mod.rationale.rule_evaluation) && Object.entries(mod.rationale.input_values || mod.rationale.rule_evaluation).map(([k, v]) => (
                                      <div key={k} style={{ display: 'flex', flexDirection: 'column' }}>
                                        <span style={{ fontSize: '0.7rem', color: '#64748B', fontWeight: '600' }}>{k}</span>
                                        <span style={{ fontSize: '0.8rem', color: '#0F172A', fontWeight: '500' }}>{v}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                                
                                {/* Rule Conditions (Matched Rule) */}
                                <div style={{ borderTop: '1px solid #F1F5F9', marginTop: '12px', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>Rule Conditions <span style={{ color: '#94A3B8' }}>↓</span></h5>
                                  <div style={{ fontSize: '0.85rem', color: '#0F172A', fontWeight: '500', background: '#F8FAFC', padding: '8px', borderRadius: '4px' }}>
                                    {mod.rationale.rule_conditions && Array.isArray(mod.rationale.rule_conditions) ? (
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                        {mod.rationale.rule_conditions.map((cond, i) => (
                                          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px', paddingBottom: '4px', borderBottom: i < mod.rationale.rule_conditions.length - 1 ? '1px solid #E2E8F0' : 'none' }}>
                                            <div style={{ display: 'flex', gap: '8px' }}>
                                              {i > 0 && <span style={{ color: '#64748B', fontSize: '0.75rem', fontWeight: 'bold', marginTop: '2px' }}>AND</span>}
                                              <span>{cond}</span>
                                            </div>
                                            <span style={{ color: '#16A34A', fontWeight: 'bold', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>PASS ✓</span>
                                          </div>
                                        ))}
                                      </div>
                                    ) : (
                                      mod.rationale.rule_conditions || mod.rationale.matched_rule
                                    )}
                                  </div>
                                </div>
                                
                                {/* Matched Bucket */}
                                <div style={{ borderTop: '1px solid #F1F5F9', marginTop: '12px', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                                      <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>Matched Bucket <span style={{ color: '#94A3B8' }}>↓</span></h5>
                                      <span style={{ fontSize: '0.85rem', color: '#0F172A', fontWeight: '600', marginTop: '4px' }}>{mod.rationale.rule_name || mod.rationale.matched_bucket}</span>
                                      {mod.rationale.rule_description && (
                                        <div style={{ fontSize: '0.8rem', color: '#64748B', marginTop: '4px', whiteSpace: 'pre-line' }}>{mod.rationale.rule_description.replace(/\\n/g, '\n')}</div>
                                      )}
                                      <div style={{ fontSize: '0.85rem', color: '#0F172A', marginTop: '6px' }}><strong>Assigned Category:</strong> {mod.rationale.assigned_category}</div>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                                      <span style={{ fontSize: '0.7rem', color: '#64748B', fontWeight: '600', textTransform: 'uppercase' }}>Rule ID</span>
                                      <span style={{ fontSize: '0.85rem', color: '#0F172A', fontWeight: '800', background: '#E2E8F0', padding: '2px 6px', borderRadius: '4px', marginTop: '2px' }}>{mod.rationale.rule_id || mod.rationale.matched_bucket}</span>
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Assigned Category */}
                                <div style={{ borderTop: '1px solid #F1F5F9', marginTop: '12px', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '4px' }}>Assigned Category <span style={{ color: '#94A3B8' }}>↓</span></h5>
                                  <div style={{ fontSize: '0.85rem', color: '#0F172A', fontWeight: '700' }}>{mod.rationale.assigned_category}</div>
                                </div>
                                
                                {/* Business Explanation */}
                                <div style={{ borderTop: '1px solid #F1F5F9', marginTop: '12px', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <h5 style={{ margin: 0, fontSize: '0.8rem', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Business Explanation</h5>
                                  <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.5', whiteSpace: 'pre-line' }}>{mod.rationale.reason || mod.rationale.why}</div>
                                  
                                  {mod.rationale.business_impact && (
                                    <>
                                      <h5 style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: '#334155', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Business Impact</h5>
                                      <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px', fontSize: '0.85rem', color: '#475569', lineHeight: '1.5' }}>
                                        {Array.isArray(mod.rationale.business_impact) ? mod.rationale.business_impact.map((impact, i) => (
                                          <li key={i} style={{ marginBottom: '4px' }}>{impact}</li>
                                        )) : (
                                          <li>{mod.rationale.business_impact}</li>
                                        )}
                                      </ul>
                                    </>
                                  )}
                                </div>
                                
                                {mod.rationale.conclusion && (
                                  <div style={{ borderTop: '1px solid #F1F5F9', marginTop: '12px', paddingTop: '12px', fontSize: '0.85rem', color: '#0F172A', fontWeight: '600' }}>
                                    Conclusion: <span style={{ fontWeight: '400', color: '#475569' }}>{mod.rationale.conclusion}</span>
                                  </div>
                                )}
                              </>
                            ) : (
                              <>
                                <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.5' }}>
                                  {mod.summary || mod.rationale || 'Not Available'}
                                </div>
                                {mod.conclusion && (
                                  <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #F1F5F9', fontSize: '0.85rem', color: '#475569', lineHeight: '1.5' }}>
                                    <strong>Conclusion:</strong> {mod.conclusion}
                                  </div>
                                )}
                              </>
                            )}
                          </div>

                          {/* Supporting Evidence */}
                          <div style={cardStyle}>
                            <h4 style={cardHeaderStyle}>Supporting Evidence</h4>
                            <EvidenceSources mod={mod} />
                          </div>

                          {/* Positive Factors */}
                          <div style={{ ...cardStyle, background: '#ECFDF5', borderColor: '#A7F3D0' }}>
                            <h4 style={{ ...cardHeaderStyle, color: '#059669' }}>Positive Factors</h4>
                            {(() => {
                              const ratObj = typeof mod.rationale === 'object' && mod.rationale !== null ? mod.rationale : null;
                              let pf = mod.positive_factors || (ratObj && ratObj.positive_factors);
                              let hasPf = pf && (Array.isArray(pf) ? pf.length > 0 : true);
                              
                              if (!hasPf && !ratObj) {
                                const rat = mod.rationale || mod.summary || mod.decision_summary || "";
                                if (rat.toLowerCase().includes('positive') || rat.toLowerCase().includes('favour') || rat.toLowerCase().includes('strong') || rat.toLowerCase().includes('mature')) {
                                   pf = [ rat ];
                                   hasPf = true;
                                }
                              }
                              
                              if (index === 0) {
                                console.log(`Positive Factors: Field Found=${hasPf}, Mapped=${Array.isArray(pf) ? pf.length : 1} items, Rendered=Yes`);
                              }
                              
                              if (!hasPf) {
                                return <div style={{ fontSize: '0.85rem', color: '#065F46', fontStyle: 'italic' }}>No positive factors returned by backend.</div>;
                              }
                              return (
                                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: '#065F46' }}>
                                  {Array.isArray(pf) 
                                    ? pf.map((f, i) => <li key={i} style={{ marginBottom: '4px' }}>✓ {f.replace(/^✓\s*/, '')}</li>)
                                    : <li>✓ {String(pf).replace(/^✓\s*/, '')}</li>}
                                </ul>
                              );
                            })()}
                          </div>

                          {/* Risk Factors */}
                          <div style={{ ...cardStyle, background: '#FEF2F2', borderColor: '#FECACA' }}>
                            <h4 style={{ ...cardHeaderStyle, color: '#DC2626' }}>Risk Factors</h4>
                            {(() => {
                              const ratObj = typeof mod.rationale === 'object' && mod.rationale !== null ? mod.rationale : null;
                              let rf = mod.risk_factors || (ratObj && ratObj.risk_factors);
                              let hasRf = rf && (Array.isArray(rf) ? rf.length > 0 : true);
                              
                              if (!hasRf && !ratObj) {
                                const rat = mod.rationale || mod.summary || mod.decision_summary || "";
                                if (rat.toLowerCase().includes('negative') || rat.toLowerCase().includes('unfavour') || rat.toLowerCase().includes('risk') || rat.toLowerCase().includes('regulatory complexity') || rat.toLowerCase().includes('large attack surface') || rat.toLowerCase().includes('high exposure')) {
                                   rf = [ rat ];
                                   hasRf = true;
                                }
                              }
                              
                              if (index === 0) {
                                console.log(`Risk Factors: Field Found=${hasRf}, Mapped=${Array.isArray(rf) ? rf.length : 1} items, Rendered=Yes`);
                              }
                              
                              if (!hasRf) {
                                return <div style={{ fontSize: '0.85rem', color: '#991B1B', fontStyle: 'italic' }}>No risk factors returned by backend.</div>;
                              }
                              return (
                                <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.85rem', color: '#991B1B' }}>
                                  {Array.isArray(rf) 
                                    ? rf.map((f, i) => <li key={i} style={{ marginBottom: '4px' }}>⚠ {f.replace(/^⚠\s*/, '')}</li>)
                                    : <li>⚠ {String(rf).replace(/^⚠\s*/, '')}</li>}
                                </ul>
                              );
                            })()}
                          </div>

                          {/* Developer/Admin Details */}
                          {isAdminMode && (
                            <div style={{ ...cardStyle, gridColumn: '1 / -1', background: '#0F172A', color: '#F8FAFC', borderColor: '#334155' }}>
                              <button 
                                onClick={() => toggleAdminExpand(mod.id)}
                                style={{ 
                                  background: 'none', border: 'none', padding: 0, 
                                  color: '#F26A21', fontSize: '0.9rem', fontWeight: '700', 
                                  cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px',
                                  width: '100%', textAlign: 'left', outline: 'none'
                                }}
                              >
                                Developer / Admin Details 
                                <span style={{ 
                                  display: 'inline-block', 
                                  transform: adminExpanded[mod.id] ? 'rotate(180deg)' : 'rotate(0deg)', 
                                  transition: 'transform 0.3s ease',
                                  fontSize: '0.7rem'
                                }}>
                                  ▼
                                </span>
                              </button>
                              
                              {adminExpanded[mod.id] && (
                                (() => {
                                  const ratObj = typeof mod.rationale === 'object' && mod.rationale !== null ? mod.rationale : null;
                                  const adminData = {
                                    calculation: [
                                      { label: 'Raw Score', value: mod.score },
                                      { label: 'Formula', value: meta.logic },
                                      { label: 'Scale', value: meta.scale },
                                      { label: 'Rule ID', value: ratObj?.rule_id || ratObj?.matched_bucket }
                                    ].filter(x => x.value),
                                    execution: [
                                      { label: 'Execution Time', value: mod.execution_time },
                                      { label: 'Collectors Used', value: mod.collectors_used ? (Array.isArray(mod.collectors_used) ? mod.collectors_used.join(', ') : mod.collectors_used) : null },
                                      { label: 'API Used', value: mod.api_used || mod.backend_api || mod.api_details }
                                    ].filter(x => x.value),
                                    reasoning: [
                                      { label: 'Prompt', value: mod.prompt_used || mod.prompt || mod.backend_explanation, isPre: true },
                                      { label: 'Fact Checker', value: mod.fact_checker_result || mod.fact_checker_output || mod.fact_checker, isPre: true },
                                      { label: 'Coordinator', value: mod.coordinator_output || mod.coordinator || mod.internal_calculation || mod.collector_outputs, isPre: true },
                                      { label: 'Underwriter', value: mod.underwriter_output || mod.underwriter, isPre: true }
                                    ].filter(x => x.value),
                                    backend: [
                                      { label: 'Fallback Logic', value: mod.fallback_logic },
                                      { label: 'Errors', value: mod.errors || mod.error },
                                      { label: 'Warnings', value: mod.warnings || mod.warning }
                                    ].filter(x => x.value)
                                  };
                                  
                                  const backendCategory = ratObj?.assigned_category || 'N/A';
                                  const frontendCategory = r; // `r` is the calculated category string at the top of the render block
                                  const mappingMatch = backendCategory.toUpperCase() === frontendCategory.toUpperCase();

                                  const hasAdminData = adminData.calculation.length > 0 || adminData.execution.length > 0 || adminData.reasoning.length > 0 || adminData.backend.length > 0;

                                  if (!hasAdminData) {
                                    return <div style={{ marginTop: '16px', color: '#94A3B8', fontSize: '0.85rem', fontStyle: 'italic' }}>No internal telemetry available for this modifier.</div>;
                                  }

                                  const renderSection = (title, items) => {
                                    if (items.length === 0) return null;
                                    return (
                                      <div style={{ marginBottom: '16px' }}>
                                        <h5 style={{ margin: '0 0 12px 0', color: '#38BDF8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{title}</h5>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
                                          {items.map((item, i) => (
                                            <div key={i} style={{ gridColumn: item.isPre ? '1 / -1' : 'auto' }}>
                                              <strong style={{ color: '#94A3B8', fontSize: '0.75rem', textTransform: 'uppercase' }}>{item.label}</strong>
                                              {item.isPre ? (
                                                <pre style={{ margin: '4px 0 0 0', background: '#020617', padding: '12px', borderRadius: '4px', overflowX: 'auto', fontSize: '0.75rem', fontFamily: 'monospace', color: '#E2E8F0', whiteSpace: 'pre-wrap', maxHeight: '200px' }}>
                                                  {typeof item.value === 'object' ? JSON.stringify(item.value, null, 2) : String(item.value)}
                                                </pre>
                                              ) : (
                                                <div style={{ fontSize: '0.85rem', color: '#F8FAFC', marginTop: '2px' }}>{String(item.value)}</div>
                                              )}
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    );
                                  };

                                  return (
                                    <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #334155' }}>
                                      {/* Backend Mapping Check */}
                                      <div style={{ marginBottom: '16px', background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #334155' }}>
                                        <h5 style={{ margin: '0 0 8px 0', color: '#F8FAFC', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                          Backend Mapping Check
                                        </h5>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.8rem' }}>
                                          <div>
                                            <span style={{ color: '#94A3B8' }}>Backend Category:</span>
                                            <div style={{ color: '#38BDF8', fontWeight: 'bold' }}>{backendCategory}</div>
                                          </div>
                                          <div>
                                            <span style={{ color: '#94A3B8' }}>Frontend Category:</span>
                                            <div style={{ color: '#38BDF8', fontWeight: 'bold' }}>{frontendCategory}</div>
                                          </div>
                                          <div style={{ gridColumn: '1 / -1', marginTop: '4px', paddingTop: '8px', borderTop: '1px solid #1E293B', display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ color: '#94A3B8' }}>Status:</span>
                                            <span style={{ color: mappingMatch ? '#10B981' : '#EF4444', fontWeight: 'bold' }}>
                                              {mappingMatch ? 'Match ✓' : 'Mismatch ⚠'}
                                            </span>
                                          </div>
                                        </div>
                                      </div>
                                      {renderSection('Calculation', adminData.calculation)}
                                      {renderSection('Execution', adminData.execution)}
                                      {renderSection('Reasoning', adminData.reasoning)}
                                      {renderSection('Backend', adminData.backend)}
                                    </div>
                                  );
                                })()
                              )}
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
