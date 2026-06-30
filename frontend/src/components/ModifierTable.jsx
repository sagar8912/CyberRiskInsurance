import React, { useState } from 'react';
import { Calculator, Info } from 'lucide-react';
import EvidenceSources from './EvidenceSources';
import { downloadReportHtml, printReportPdf } from './EvidenceReportGenerator';

export const modifierMetadata = {
  "Mergers and Acquisitions": { scale: "0-10+ Points", logic: "Lower score = More favourable (less integration risk)" },
  "Amount of sensitive information": { scale: "Customer Type & E-com", logic: "B2C + Ecommerce increases data breach severity" },
  "Domain Encryption": { scale: "Encrypted Ratio", logic: "100% encrypted domains = Favourable" },
  "Geographic Spread": { scale: "Country Count", logic: "Wider spread increases regulatory complexity" },
  "Internet footprint": { scale: "Domains × Size Multiplier", logic: "Larger footprint increases attack surface" },
  "Nature of services": { scale: "Low / Medium / High Risk", logic: "Higher risk industries increase cyber exposure" },
  "Organizational Complexity": { scale: "Subsidiary Count", logic: "More subsidiaries = broader threat landscape" },
  "Privacy Regulation": { scale: "Compliance Mentions", logic: "Published policy + Compliance = Favourable" },
  "Seasonality of sales": { scale: "Coefficient of Variation", logic: "High variance means peak outages are devastating" },
  "Volatility/Recovery in Sales": { scale: "Averaged Risk Index", logic: "Higher recovery complexity = Unfavourable" },
  "Applicability of Privacy Regulation": { scale: "SIC Code Mapping", logic: "Strict industries (Health/Finance) increase liability" },
  "B2C End Products": { scale: "Business Model", logic: "Direct consumer interaction increases privacy risk" },
  "Years in business": { scale: "Age in Years", logic: "Older enterprise = more established and favourable" }
};

export default function ModifierTable({ data, isAdminMode, verdictData }) {
  const [expandedModifiers, setExpandedModifiers] = useState({});
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
                    borderBottom: (index === data.length - 1 && !isExpanded) ? 'none' : '1px solid #F1F5F9',
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
                    <tr style={{ background: '#F8FAFC', borderBottom: index === data.length - 1 ? 'none' : '1px solid #E2E8F0' }}>
                      <td colSpan={colSpan} style={{ padding: '24px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
                          
                          {/* Decision Summary */}
                          <div style={cardStyle}>
                            <h4 style={cardHeaderStyle}>Decision Summary</h4>
                            <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.5' }}>
                              {mod.summary || mod.rationale || 'Not Available'}
                            </div>
                            {mod.conclusion && (
                              <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #F1F5F9', fontSize: '0.85rem', color: '#475569', lineHeight: '1.5' }}>
                                <strong>Conclusion:</strong> {mod.conclusion}
                              </div>
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
                              let pf = mod.positive_factors || mod.strengths || mod.advantages || mod.supporting_points || mod.underwriting_rationale;
                              let hasPf = pf && (Array.isArray(pf) ? pf.length > 0 : true);
                              
                              if (!hasPf) {
                                const rat = mod.rationale || mod.summary || mod.decision_summary || "";
                                if (rat.toLowerCase().includes('positive') || rat.toLowerCase().includes('favour') || rat.toLowerCase().includes('strong')) {
                                   pf = [ rat ];
                                   hasPf = true;
                                }
                              }
                              
                              if (index === 0) {
                                console.log(`Positive Factors: Field Found=${hasPf}, Mapped=${Array.isArray(pf) ? pf.length : 1} items, Rendered=Yes`);
                              }
                              
                              if (!hasPf) {
                                console.warn(`[Missing Positive Factors] No positive factors found for modifier: ${mod.name}`);
                                return <div style={{ fontSize: '0.85rem', color: '#065F46', fontStyle: 'italic' }}>No positive factors identified.</div>;
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
                              let rf = mod.risk_factors || mod.weaknesses || mod.negative_points || mod.concerns || mod.risk_summary;
                              let hasRf = rf && (Array.isArray(rf) ? rf.length > 0 : true);
                              
                              if (!hasRf) {
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
                                console.warn(`[Missing Risk Factors] No risk factors found for modifier: ${mod.name}`);
                                return <div style={{ fontSize: '0.85rem', color: '#991B1B', fontStyle: 'italic' }}>No specific risk factors identified.</div>;
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
                                  const adminData = {
                                    calculation: [
                                      { label: 'Raw Score', value: mod.score },
                                      { label: 'Formula', value: meta.logic },
                                      { label: 'Scale', value: meta.scale }
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
