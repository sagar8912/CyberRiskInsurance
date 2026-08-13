import os

def patch_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for search, replace in replacements:
        if search in content:
            content = content.replace(search, replace)
        else:
            print(f"Warning: Could not find string in {filepath}:\n{search}")
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# 1. AgentResultCards.jsx
patch_file(r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\AgentResultCards.jsx', [
    (
        "const favMods = modifiers ? modifiers.filter(m => m.rating.includes('FAVOURABLE') && !m.rating.includes('UNFAVOURABLE')).length : 0;",
        "const favMods = modifiers ? modifiers.filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r.includes('FAVOURABLE') && !r.includes('UNFAVOURABLE');\n  }).length : 0;"
    )
])

# 2. VerdictCard.jsx
patch_file(r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\VerdictCard.jsx', [
    (
        "const favorableModifiers = modifiers.filter(m => m.rating.includes('FAVOURABLE') && !m.rating.includes('UNFAVOURABLE'));",
        "const favorableModifiers = modifiers.filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r.includes('FAVOURABLE') && !r.includes('UNFAVOURABLE');\n  });"
    ),
    (
        "const unfavorableModifiers = modifiers.filter(m => m.rating.includes('UNFAVOURABLE'));",
        "const unfavorableModifiers = modifiers.filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r.includes('UNFAVOURABLE');\n  });"
    ),
    (
        "const neutralModifiers = modifiers.filter(m => m.rating === 'AVERAGE' || m.rating === 'NEUTRAL');",
        "const neutralModifiers = modifiers.filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r === 'AVERAGE' || r === 'NEUTRAL';\n  });"
    )
])

# 3. AgentConsensus.jsx
patch_file(r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\AgentConsensus.jsx', [
    (
        "const favorableModifiers = modifiers.filter(m => m.rating.includes('FAVOURABLE') && !m.rating.includes('UNFAVOURABLE'));",
        "const favorableModifiers = (modifiers || []).filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r.includes('FAVOURABLE') && !r.includes('UNFAVOURABLE');\n  });"
    ),
    (
        "const neutralModifiers = modifiers.filter(m => m.rating === 'AVERAGE' || m.rating === 'NEUTRAL');",
        "const neutralModifiers = (modifiers || []).filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r === 'AVERAGE' || r === 'NEUTRAL';\n  });"
    ),
    (
        "const unfavorableModifiers = modifiers.filter(m => m.rating.includes('UNFAVOURABLE'));",
        "const unfavorableModifiers = (modifiers || []).filter(m => {\n    const r = (m.rating || m.modifier_value || '').toUpperCase();\n    return r.includes('UNFAVOURABLE');\n  });"
    )
])

# 4. KeyFindings.jsx
patch_file(r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\KeyFindings.jsx', [
    (
        "const bestMod = modifiers.find(m => m.rating.includes('VERY FAVOURABLE'));",
        "const bestMod = (modifiers || []).find(m => {\n      const r = (m.rating || m.modifier_value || '').toUpperCase();\n      return r.includes('VERY FAVOURABLE');\n    });"
    ),
    (
        "const worstMod = modifiers.find(m => m.rating.includes('UNFAVOURABLE'));",
        "const worstMod = (modifiers || []).find(m => {\n      const r = (m.rating || m.modifier_value || '').toUpperCase();\n      return r.includes('UNFAVOURABLE');\n    });"
    )
])

# 5. ModifierTable.jsx
patch_file(r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\ModifierTable.jsx', [
    (
        "const r = mod.rating.toUpperCase();",
        "const r = (mod.rating || mod.modifier_value || '').toUpperCase();"
    )
])

# 6. BatchAnalysisModal.jsx (Error Boundary, safe modifiers, re-add ModifierTable, fix rating display)
batch_path = r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\BatchAnalysisModal.jsx'
with open(batch_path, 'r', encoding='utf-8') as f:
    batch_content = f.read()

# Add ModifierTable import
if "import ModifierTable from './ModifierTable';" not in batch_content:
    batch_content = batch_content.replace(
        "import ModifierDetailsModal from './ModifierDetailsModal';",
        "import ModifierDetailsModal from './ModifierDetailsModal';\nimport ModifierTable from './ModifierTable';"
    )

# Add ErrorBoundary component at the top
error_boundary = """
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error('BatchAnalysis Error:', error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '48px', textAlign: 'center' }}>
          <h3 style={{ color: '#DC2626' }}>Unable to display company details.</h3>
          <p style={{ color: '#64748B', marginBottom: '24px' }}>{this.state.error?.message}</p>
          <button onClick={() => { this.setState({ hasError: false }); this.props.onReset && this.props.onReset(); }} style={{ background: 'var(--accent-orange)', color: '#FFF', padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Back to Batch Results</button>
        </div>
      );
    }
    return this.props.children;
  }
}
"""
if "class ErrorBoundary extends React.Component" not in batch_content:
    batch_content = batch_content.replace(
        "export default function BatchAnalysisModal({ isOpen, onClose }) {",
        error_boundary + "\nexport default function BatchAnalysisModal({ isOpen, onClose }) {"
    )

# Update Company View
company_view_search = """              {isFinished && currentView === 'company' && completedRows[currentCompanyIndex] && (() => {
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
              })()}"""
company_view_replace = """              {isFinished && currentView === 'company' && completedRows[currentCompanyIndex] && (() => {
                const row = completedRows[currentCompanyIndex];
                if (!row || !row.rawData) return <div style={{ padding: '24px', textAlign: 'center' }}>Loading company details...</div>;
                const activeReconciled = row.rawData.reconciled_profile || {};
                const activeClaims = Array.isArray(row.rawData.fact_checker_claims) ? row.rawData.fact_checker_claims : [];
                const activeModifiers = Array.isArray(row.rawData.modifiers) ? row.rawData.modifiers : [];
                const activeVerdict = row.rawData.final_verdict || row.rawData.verdict || null;
                const targetEntity = row.rawData.target_entity || {};
                return (
                  <ErrorBoundary onReset={() => setCurrentView('results')}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
                      <AgentResultCards reconciledProfile={activeReconciled} claims={activeClaims} modifiers={activeModifiers} verdict={activeVerdict} />
                      <ReconciledProfile data={activeReconciled} claims={activeClaims} verdict={activeVerdict} />
                      <ModifierTable data={activeModifiers} isAdminMode={false} verdictData={{ target_entity: targetEntity, final_verdict: activeVerdict }} />
                      <VerdictCard data={activeVerdict} modifiers={activeModifiers} claims={activeClaims} />
                    </div>
                  </ErrorBoundary>
                );
              })()}"""
batch_content = batch_content.replace(company_view_search, company_view_replace)

# Update Modifier View rating render
modifier_view_search = """<div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#FFF' }}>{mod.rating}</div>"""
modifier_view_replace = """<div style={{ fontWeight: '700', fontSize: '1.1rem', color: '#FFF' }}>{mod.rating || mod.modifier_value || 'Unknown'}</div>"""
batch_content = batch_content.replace(modifier_view_search, modifier_view_replace)

# Add ErrorBoundary to Modifier View just in case
modifier_section_search = """              {isFinished && currentView === 'modifier' && completedRows[currentCompanyIndex] && (() => {"""
modifier_section_replace = """              {isFinished && currentView === 'modifier' && completedRows[currentCompanyIndex] && (() => {
                return <ErrorBoundary onReset={() => setCurrentView('results')}>
                  {(() => {"""

modifier_section_end_search = """                      <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Modifier not found</div>
                    )}
                  </div>
                );
              })()}"""
modifier_section_end_replace = """                      <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Modifier not found</div>
                    )}
                  </div>
                );
              })()}
                </ErrorBoundary>
              })()}"""
# actually, doing an inner IIFE is messy via simple replace. I'll just wrap the returned div in ErrorBoundary.
modifier_render_search = """                return (
                  <div style={{ padding: '16px 0', maxWidth: '800px', margin: '0 auto', width: '100%' }}>"""
modifier_render_replace = """                return (
                  <ErrorBoundary onReset={() => setCurrentView('results')}>
                  <div style={{ padding: '16px 0', maxWidth: '800px', margin: '0 auto', width: '100%' }}>"""

modifier_render_end_search = """                      <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Modifier not found</div>
                    )}
                  </div>
                );
              })()}"""
modifier_render_end_replace = """                      <div style={{ padding: '24px', textAlign: 'center', color: '#64748B' }}>Modifier not found</div>
                    )}
                  </div>
                  </ErrorBoundary>
                );
              })()}"""
batch_content = batch_content.replace(modifier_render_search, modifier_render_replace)
batch_content = batch_content.replace(modifier_render_end_search, modifier_render_end_replace)

with open(batch_path, 'w', encoding='utf-8') as f:
    f.write(batch_content)

print("Patch applied to all files safely.")
