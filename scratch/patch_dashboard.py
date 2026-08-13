import os

file_path = r'c:\Users\HP\3D Objects\CyberRiskFresh\CyberRiskInsurance\frontend\src\components\PortfolioDashboard.jsx'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add onSelectCompanyAndModifier to PortfolioHeatMap props
heatmap_def_search = """function PortfolioHeatMap({ companies, selectedCompanyId, onSelectCompany }) {"""
heatmap_def_replace = """function PortfolioHeatMap({ companies, selectedCompanyId, onSelectCompany, onSelectCompanyAndModifier }) {"""
content = content.replace(heatmap_def_search, heatmap_def_replace)

# 2. Add onClick to td in PortfolioHeatMap
td_search = """                      <td key={modName}
                          title={tooltip}
                          onMouseEnter={() => setHoveredMod(modName)}
                          onMouseLeave={() => setHoveredMod(null)}
                          style={{ padding: '4px', borderBottom: '1px solid #F1F5F9', textAlign: 'center', background: hoveredMod === modName ? '#F8FAFC' : 'transparent', transition: 'background 0.2s' }}>"""
td_replace = """                      <td key={modName}
                          title={tooltip}
                          onMouseEnter={() => setHoveredMod(modName)}
                          onMouseLeave={() => setHoveredMod(null)}
                          onClick={() => {
                            if (onSelectCompanyAndModifier && c.rawData?.modifiers) {
                               const cModIndex = c.rawData.modifiers.findIndex(m => (m.name || m.modifier_name) === modName);
                               if (cModIndex !== -1) {
                                  onSelectCompanyAndModifier(c.id, cModIndex);
                               }
                            }
                          }}
                          style={{ padding: '4px', borderBottom: '1px solid #F1F5F9', textAlign: 'center', background: hoveredMod === modName ? '#F8FAFC' : 'transparent', transition: 'background 0.2s', cursor: onSelectCompanyAndModifier ? 'pointer' : 'default' }}>"""
content = content.replace(td_search, td_replace)


# 3. Add onSelectCompanyAndModifier to PortfolioDashboard props
dashboard_def_search = """export default function PortfolioDashboard({ rows }) {"""
dashboard_def_replace = """export default function PortfolioDashboard({ rows, onSelectCompanyAndModifier }) {"""
content = content.replace(dashboard_def_search, dashboard_def_replace)


# 4. Pass onSelectCompanyAndModifier from PortfolioDashboard to PortfolioHeatMap
heatmap_call_search = """          <PortfolioHeatMap 
            companies={displayList} 
            selectedCompanyId={selectedCompanyId} 
            onSelectCompany={(id) => {"""
heatmap_call_replace = """          <PortfolioHeatMap 
            companies={displayList} 
            selectedCompanyId={selectedCompanyId} 
            onSelectCompanyAndModifier={onSelectCompanyAndModifier}
            onSelectCompany={(id) => {"""
content = content.replace(heatmap_call_search, heatmap_call_replace)


with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to PortfolioDashboard.jsx successfully.")
