import os

file_path = r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\BatchAnalysisModal.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add ArrowRight to lucide-react imports if not there
if 'ChevronRight' not in content:
    content = content.replace('ArrowLeft, ', 'ArrowLeft, ChevronRight, ChevronLeft, ')

# 2. Add ModifierDetailsModal import if not there
if 'ModifierDetailsModal' not in content:
    content = content.replace("import PortfolioDashboard from './PortfolioDashboard';", "import PortfolioDashboard from './PortfolioDashboard';\nimport ModifierDetailsModal from './ModifierDetailsModal';")

# 3. Replace state
state_search = """  // Detail View State
  const [viewingRowId, setViewingRowId] = useState(null);"""
state_replace = """  // Wizard Navigation State
  const [currentView, setCurrentView] = useState('portfolio'); // 'portfolio', 'results', 'company', 'modifier'
  const [currentCompanyIndex, setCurrentCompanyIndex] = useState(0);
  const [currentModifierIndex, setCurrentModifierIndex] = useState(0);
  
  // Detail View State (Deprecated, keeping for compatibility if needed)
  const [viewingRowId, setViewingRowId] = useState(null);"""
content = content.replace(state_search, state_replace)

# 4. Update reset()
reset_search = """    setViewingRowId(null);
    cancelRef.current = false;"""
reset_replace = """    setViewingRowId(null);
    setCurrentView('portfolio');
    setCurrentCompanyIndex(0);
    setCurrentModifierIndex(0);
    cancelRef.current = false;"""
content = content.replace(reset_search, reset_replace)

# 5. Extract completedRows earlier and handleNext/handleBack logic
render_detail_search = """  // RENDER DETAIL VIEW
  if (viewingRowId !== null) {"""
render_detail_replace = """
  const completedRows = rows.filter(r => r.status === 'Completed' && r.rawData);

  const getModifierList = (companyIdx) => {
    const row = completedRows[companyIdx];
    if (!row || !row.rawData) return [];
    return row.rawData.modifiers || [];
  };

  const handleNext = () => {
    if (currentView === 'portfolio') {
      setCurrentView('results');
    } else if (currentView === 'results') {
      if (completedRows.length > 0) {
        setCurrentCompanyIndex(0);
        setCurrentView('company');
      }
    } else if (currentView === 'company') {
      setCurrentModifierIndex(0);
      setCurrentView('modifier');
    } else if (currentView === 'modifier') {
      const mods = getModifierList(currentCompanyIndex);
      if (currentModifierIndex < mods.length - 1) {
        setCurrentModifierIndex(currentModifierIndex + 1);
      } else if (currentCompanyIndex < completedRows.length - 1) {
        setCurrentCompanyIndex(currentCompanyIndex + 1);
        setCurrentView('company');
      }
    }
  };

  const handleBack = () => {
    if (currentView === 'results') {
      setCurrentView('portfolio');
    } else if (currentView === 'company') {
      setCurrentView('results');
    } else if (currentView === 'modifier') {
      if (currentModifierIndex > 0) {
        setCurrentModifierIndex(currentModifierIndex - 1);
      } else {
        setCurrentView('company');
      }
    }
  };

  let isNextDisabled = false;
  if (currentView === 'results' && completedRows.length === 0) isNextDisabled = true;
  if (currentView === 'modifier') {
    const mods = getModifierList(currentCompanyIndex);
    if (currentModifierIndex === mods.length - 1 && currentCompanyIndex === completedRows.length - 1) {
      isNextDisabled = true;
    }
  }

  const isBackDisabled = currentView === 'portfolio';

  const viewFullResult = (rowId) => {
    const idx = completedRows.findIndex(r => r.id === rowId);
    if (idx !== -1) {
      setCurrentCompanyIndex(idx);
      setCurrentView('company');
    }
  };

  const handleHeatMapSelect = (companyId, modIndex) => {
    const idx = completedRows.findIndex(r => r.id === companyId);
    if (idx !== -1) {
      setCurrentCompanyIndex(idx);
      if (modIndex !== null && modIndex !== undefined) {
        setCurrentModifierIndex(modIndex);
        setCurrentView('modifier');
      } else {
        setCurrentView('company');
      }
    }
  };

  // RENDER DETAIL VIEW
  if (viewingRowId !== null) {"""
content = content.replace(render_detail_search, render_detail_replace)

# 6. Change viewFullResult call in Table
view_full_search = """<button onClick={() => setViewingRowId(row.id)} style={{ background: '#F1F5F9'"""
view_full_replace = """<button onClick={() => viewFullResult(row.id)} style={{ background: '#F1F5F9'"""
content = content.replace(view_full_search, view_full_replace)

# 7. Restructure the body rendering
body_search = """              <div style={{ width: '100%', overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '6px', flex: 1 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left', minWidth: '1200px' }}>"""

body_replace = """              {(!isFinished || currentView === 'results') && (
                <div style={{ width: '100%', overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '6px', flex: 1 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left', minWidth: '1200px' }}>"""
content = content.replace(body_search, body_replace)

table_end_search = """                  </tbody>
                </table>
              </div>
              {isFinished && <PortfolioDashboard rows={rows} />}"""
table_end_replace = """                  </tbody>
                </table>
              </div>
              )}

              {isFinished && currentView === 'portfolio' && (
                <PortfolioDashboard 
                  rows={rows} 
                  onSelectCompanyAndModifier={handleHeatMapSelect}
                />
              )}

              {isFinished && currentView === 'company' && completedRows[currentCompanyIndex] && (() => {
                const row = completedRows[currentCompanyIndex];
                const activeReconciled = row.rawData.reconciled_profile;
                const activeClaims = row.rawData.fact_checker_claims;
                const activeModifiers = row.rawData.modifiers;
                const activeVerdict = row.rawData.final_verdict;
                return (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
                    <AgentResultCards reconciledProfile={activeReconciled} claims={activeClaims} modifiers={activeModifiers} verdict={activeVerdict} />
                    <ReconciledProfile data={activeReconciled} claims={activeClaims} verdict={activeVerdict} />
                    <VerdictCard data={activeVerdict} modifiers={activeModifiers} claims={activeClaims} />
                  </div>
                );
              })()}

              {isFinished && currentView === 'modifier' && completedRows[currentCompanyIndex] && (() => {
                const row = completedRows[currentCompanyIndex];
                const mods = row.rawData.modifiers || [];
                const mod = mods[currentModifierIndex];
                return (
                  <div style={{ padding: '16px 0', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
                    {mod ? (
                      <div style={{ position: 'relative' }}>
                        <ModifierDetailsModal isOpen={true} onClose={() => {}} modifier={mod} />
                        {/* Note: In a real implementation we would adjust ModifierDetailsModal to not render the backdrop, 
                            but since it's hardcoded to position:fixed, we will render the exact same UI structure here to avoid CSS issues. */}
                        <div 
                          className="glass-panel" 
                          style={{
                            width: '100%',
                            background: 'rgba(16, 23, 42, 0.95)',
                            border: '1px solid var(--accent-orange)',
                            position: 'relative',
                            padding: '24px',
                            borderRadius: '12px'
                          }}
                        >
                          <h2 style={{ color: 'var(--accent-orange)', marginBottom: '8px', marginTop: 0 }}>Modifier Details</h2>
                          <div style={{ fontSize: '1.2rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '24px' }}>
                            {mod.name}
                          </div>

                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                              <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px' }}>Category Rating</div>
                              <div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#FFF' }}>{mod.rating}</div>
                            </div>
                            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                              <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px' }}>Raw Mathematical Score</div>
                              <div style={{ fontWeight: '700', fontSize: '1.1rem', fontFamily: 'monospace', color: 'var(--accent-orange)' }}>{mod.score}</div>
                            </div>
                          </div>

                          <div style={{ marginBottom: '24px' }}>
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', marginBottom: '12px', color: '#FFF' }}>Input Data Used</h3>
                            <p style={{ background: 'rgba(20, 184, 166, 0.1)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(20, 184, 166, 0.2)', fontSize: '0.95rem', lineHeight: '1.5', color: '#E2E8F0' }}>
                              Evaluated using facts from Reconciled Profile and SEC/Wikidata sources related to {mod.name}.
                            </p>
                          </div>

                          <div style={{ marginBottom: '24px' }}>
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', marginBottom: '12px', color: '#FFF' }}>Evaluated Rationale & Backend Output</h3>
                            <p style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)', fontSize: '0.95rem', lineHeight: '1.5', color: '#E2E8F0' }}>
                              {mod.rationale}
                            </p>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-success)', fontSize: '0.85rem', fontWeight: '500', background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                            Evidence/Claim Support: Rule verified against Fact Checker ground truth.
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Modifier not found</div>
                    )}
                  </div>
                );
              })()}"""
content = content.replace(table_end_search, table_end_replace)

# 8. Add wizard footer when isFinished
footer_search = """        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #E2E8F0', background: '#F8FAFC', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          {!isProcessing && (
             <button onClick={handleClose} style={{ background: 'transparent', border: '1px solid #CBD5E1', padding: '8px 16px', borderRadius: '6px', color: '#475569', fontWeight: '600', cursor: 'pointer' }}>
               {isFinished ? 'Close' : 'Cancel'}
             </button>
          )}"""
footer_replace = """        {/* Footer */}
        {isFinished ? (
          <div style={{ padding: '16px 24px', borderTop: '1px solid #E2E8F0', background: '#F8FAFC', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button onClick={handleClose} style={{ background: 'transparent', border: '1px solid #CBD5E1', padding: '8px 16px', borderRadius: '6px', color: '#475569', fontWeight: '600', cursor: 'pointer' }}>
                Close Batch
              </button>
              
              {currentView === 'company' && (
                <span style={{ fontSize: '0.85rem', color: '#64748B', fontWeight: '600' }}>
                  Company {currentCompanyIndex + 1} of {completedRows.length} &middot; {completedRows[currentCompanyIndex]?.company}
                </span>
              )}
              {currentView === 'modifier' && (
                <span style={{ fontSize: '0.85rem', color: '#64748B', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ background: '#E2E8F0', padding: '4px 8px', borderRadius: '4px', color: '#334155' }}>
                    Company {currentCompanyIndex + 1} of {completedRows.length}
                  </span>
                  <ChevronRight size={14} color="#94A3B8" />
                  <span style={{ color: '#0F172A' }}>
                    Modifier {currentModifierIndex + 1} of {getModifierList(currentCompanyIndex).length}
                  </span>
                </span>
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <button 
                onClick={handleBack} 
                disabled={isBackDisabled}
                style={{ 
                  background: isBackDisabled ? '#F1F5F9' : '#FFFFFF', 
                  border: '1px solid #CBD5E1', 
                  padding: '8px 16px', borderRadius: '6px', 
                  color: isBackDisabled ? '#94A3B8' : '#0F172A', 
                  fontWeight: '600', cursor: isBackDisabled ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: '6px'
                }}
              >
                <ChevronLeft size={16} /> Back
              </button>
              
              <button 
                onClick={handleNext} 
                disabled={isNextDisabled}
                style={{ 
                  background: isNextDisabled ? '#94A3B8' : 'var(--accent-orange)', 
                  border: 'none', 
                  padding: '8px 16px', borderRadius: '6px', 
                  color: '#FFF', 
                  fontWeight: '600', cursor: isNextDisabled ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: '6px'
                }}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          </div>
        ) : (
          <div style={{ padding: '16px 24px', borderTop: '1px solid #E2E8F0', background: '#F8FAFC', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            {!isProcessing && (
               <button onClick={handleClose} style={{ background: 'transparent', border: '1px solid #CBD5E1', padding: '8px 16px', borderRadius: '6px', color: '#475569', fontWeight: '600', cursor: 'pointer' }}>
                 Cancel
               </button>
            )}"""
content = content.replace(footer_search, footer_replace)

footer_end_search = """              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}"""
footer_end_replace = """              </button>
            )
          )}
          </div>
        )}
      </div>
    </div>
  );
}"""
content = content.replace(footer_end_search, footer_end_replace)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to BatchAnalysisModal.jsx successfully.")
