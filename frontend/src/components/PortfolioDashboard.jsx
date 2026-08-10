import { useState, useMemo, useCallback } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import {
  ShieldCheck, ShieldAlert, Shield, AlertTriangle, HelpCircle,
  ChevronRight, ChevronDown, ChevronUp, ArrowLeft, Search,
  TrendingDown, TrendingUp, Activity, Database, Users, CheckCircle, XCircle, Clock, Square
} from 'lucide-react';

// ─── Color mapping — handles both American and British spellings from backend ──

function resolveRatingStyle(rating = '') {
  const up = rating.trim().toUpperCase();
  // Partial Unfavorable — must check before generic unfavorable
  if ((up.includes('PARTIAL') && (up.includes('UNFAVOUR') || up.includes('UNFAVOR')))) {
    return { color: '#EA580C', bg: '#FFF7ED', border: '#FED7AA' };
  }
  if (up.includes('UNFAVOUR') || up.includes('UNFAVOR')) {
    return { color: '#DC2626', bg: '#FEF2F2', border: '#FECACA' };
  }
  if (up === 'VERY FAVOURABLE' || up === 'VERY FAVORABLE') {
    return { color: '#059669', bg: '#ECFDF5', border: '#A7F3D0' };
  }
  if ((up.includes('FAVOUR') || up.includes('FAVOR')) && up.includes('PARTIAL')) {
    return { color: '#65A30D', bg: '#F7FEE7', border: '#D9F99D' };
  }
  if (up.includes('FAVOUR') || up.includes('FAVOR')) {
    return { color: '#16A34A', bg: '#F0FDF4', border: '#BBF7D0' };
  }
  if (up === 'AVERAGE') {
    return { color: '#CA8A04', bg: '#FEFCE8', border: '#FEF08A' };
  }
  return { color: '#64748B', bg: '#F8FAFC', border: '#CBD5E1' };
}

// Normalise verdict strings so summary cards can bucket them correctly
function normaliseVerdict(verdict = '') {
  const up = verdict.trim().toUpperCase();
  if (up.includes('PARTIAL') && (up.includes('UNFAVOUR') || up.includes('UNFAVOR'))) return 'Partially Unfavorable';
  if (up.includes('UNFAVOUR') || up.includes('UNFAVOR')) return 'Unfavorable';
  if (up === 'VERY FAVOURABLE' || up === 'VERY FAVORABLE') return 'Favorable'; // treat Very Fav as Fav for bucketing
  if ((up.includes('FAVOUR') || up.includes('FAVOR')) && up.includes('PARTIAL')) return 'Partially Favorable';
  if (up.includes('FAVOUR') || up.includes('FAVOR')) return 'Favorable';
  if (up === 'AVERAGE') return 'Average';
  return 'Unknown';
}

function getModifierRisk(mod) {
  if (!mod) return { position: 50, label: 'Unknown', markerColor: '#EAB308' };

  const rating = mod.rating || mod.modifier_value || 'Unknown';
  const upRating = String(rating).trim().toUpperCase();

  let position = 50;
  let label = 'Average';

  if (upRating.includes('HIGHLY UNFAVOUR') || upRating.includes('HIGHLY UNFAVOR')) {
    position = 98;
    label = 'Highly Unfavorable';
  } else if ((upRating.includes('PARTIAL') || upRating.includes('PARTIALLY')) && (upRating.includes('UNFAVOUR') || upRating.includes('UNFAVOR'))) {
    position = 70;
    label = 'Partially Unfavorable';
  } else if (upRating.includes('UNFAVOUR') || upRating.includes('UNFAVOR')) {
    position = 90;
    label = 'Unfavorable';
  } else if ((upRating.includes('PARTIAL') || upRating.includes('PARTIALLY')) && (upRating.includes('FAVOUR') || upRating.includes('FAVOR'))) {
    position = 40;
    label = 'Partially Favorable';
  } else if (upRating.includes('HIGHLY FAVOUR') || upRating.includes('HIGHLY FAVOR') || upRating.includes('VERY FAVOUR') || upRating.includes('VERY FAVOR')) {
    position = 10;
    label = 'Highly Favorable';
  } else if (upRating.includes('FAVOUR') || upRating.includes('FAVOR')) {
    position = 25;
    label = 'Favorable';
  } else if (upRating.includes('AVERAGE')) {
    position = 50;
    label = 'Average';
  }

  // Priority override: visualizationScore -> normalizedScore
  if (mod.visualizationScore !== undefined && mod.visualizationScore !== null && !isNaN(Number(mod.visualizationScore))) {
    position = Number(mod.visualizationScore);
  } else if (mod.normalizedScore !== undefined && mod.normalizedScore !== null && !isNaN(Number(mod.normalizedScore))) {
    position = Number(mod.normalizedScore);
  }
  
  const clampedPosition = Math.max(0, Math.min(100, position));
  
  let markerColor = '#EAB308';
  if (clampedPosition <= 15) markerColor = '#16A34A';
  else if (clampedPosition <= 35) markerColor = '#22C55E';
  else if (clampedPosition <= 45) markerColor = '#84CC16';
  else if (clampedPosition <= 60) markerColor = '#EAB308';
  else if (clampedPosition <= 80) markerColor = '#F97316';
  else markerColor = '#DC2626';

  return { position: clampedPosition, label, markerColor };
}

const VERDICT_CONFIG = {
  'Favorable':             { color: '#16A34A', bg: '#F0FDF4', icon: ShieldCheck,  order: 0 },
  'Partially Favorable':   { color: '#65A30D', bg: '#F7FEE7', icon: Shield,       order: 1 },
  'Average':               { color: '#CA8A04', bg: '#FEFCE8', icon: Shield,       order: 2 },
  'Partially Unfavorable': { color: '#EA580C', bg: '#FFF7ED', icon: ShieldAlert,  order: 3 },
  'Unfavorable':           { color: '#DC2626', bg: '#FEF2F2', icon: ShieldAlert,  order: 4 },
  'Unknown':               { color: '#64748B', bg: '#F8FAFC', icon: HelpCircle,   order: 5 },
};

const VERDICT_BUCKETS = Object.keys(VERDICT_CONFIG);
const RISK_SORT_ORDER  = { 'Unfavorable': 0, 'Partially Unfavorable': 1, 'Average': 2, 'Partially Favorable': 3, 'Favorable': 4, 'Unknown': 5 };

// ─── Data accessors — match actual API response shape ────────────────────────
const getReconciledProfile = (row) => row?.rawData?.reconciled_profile || {};
const getWikidata          = (row) => row?.rawData?.wikidata_output    || {};
const getFinalVerdict      = (row) => row?.rawData?.final_verdict      || {};

function parseConf(val) {
  if (val == null) return null;
  if (typeof val === 'number') return val;
  const n = parseFloat(String(val).replace('%', ''));
  return isNaN(n) ? null : n;
}

const getField = (val) => {
  const s = String(val ?? '').trim();
  return (s === '' || s === 'N/A' || s === 'n/a' || s === 'None' || s === 'null' || s === 'Not Available' || s === 'undefined') ? null : s;
};

// ─── Shared sub-components ────────────────────────────────────────────────────

function RatingBadge({ verdict }) {
  const { color, bg } = resolveRatingStyle(verdict);
  return (
    <span style={{
      background: bg, color, border: `1px solid ${color}40`,
      padding: '3px 10px', borderRadius: '20px',
      fontSize: '0.71rem', fontWeight: '700', whiteSpace: 'nowrap',
      display: 'inline-flex', alignItems: 'center', gap: '5px',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      {verdict || 'Unknown'}
    </span>
  );
}

function MetaChip({ label, value }) {
  if (!getField(String(value ?? ''))) return null;
  return (
    <div>
      <div style={{ fontSize: '0.68rem', color: '#94A3B8', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.05em', marginBottom: '3px' }}>{label}</div>
      <div style={{ fontSize: '0.84rem', color: '#334155', fontWeight: '500', lineHeight: 1.4 }}>{value}</div>
    </div>
  );
}

function Card({ children, style }) {
  return (
    <div style={{ background: '#FFFFFF', borderRadius: '10px', border: '1px solid #E2E8F0', boxShadow: '0 1px 3px rgba(0,0,0,0.04)', overflow: 'hidden', ...style }}>
      {children}
    </div>
  );
}

function CardHeader({ title, subtitle, action }) {
  return (
    <div style={{ padding: '14px 18px', borderBottom: '1px solid #F1F5F9', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
      <div>
        <div style={{ fontSize: '0.88rem', fontWeight: '700', color: '#0F172A' }}>{title}</div>
        {subtitle && <div style={{ fontSize: '0.76rem', color: '#94A3B8', marginTop: '2px' }}>{subtitle}</div>}
      </div>
      {action}
    </div>
  );
}

// ─── Pie chart tooltip ────────────────────────────────────────────────────────

function PieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: '#FFF', padding: '10px 14px', border: '1px solid #E2E8F0', borderRadius: '8px', boxShadow: '0 8px 24px rgba(0,0,0,0.1)', minWidth: '160px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
        <div style={{ width: 9, height: 9, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
        <span style={{ fontWeight: '700', color: '#0F172A', fontSize: '0.86rem' }}>{d.name}</span>
      </div>
      <div style={{ fontSize: '0.8rem', color: '#475569' }}>Companies: <strong style={{ color: '#0F172A' }}>{d.value}</strong></div>
      <div style={{ fontSize: '0.8rem', color: '#475569' }}>Portfolio share: <strong style={{ color: '#0F172A' }}>{d.percentage}%</strong></div>
    </div>
  );
}

// ─── Modifier Heat Map Row ────────────────────────────────────────────────────

function ModifierHeatRow({ mod, index }) {
  const [expanded, setExpanded] = useState(false);
  const [hoverMarker, setHoverMarker] = useState(false);

  const rating  = mod.rating || mod.modifier_value || 'Unknown';
  const ratObj  = (typeof mod.rationale === 'object' && mod.rationale !== null) ? mod.rationale : null;

  const summary         = ratObj?.decision_summary || ratObj?.reason || (typeof mod.rationale === 'string' ? mod.rationale : null) || mod.summary || null;
  const positiveFactors = mod.positive_factors || ratObj?.positive_factors || [];
  const riskFactors     = mod.risk_factors     || ratObj?.risk_factors     || [];
  const ruleConditions  = ratObj?.rule_conditions || null;
  const businessImpact  = ratObj?.business_impact || null;
  const conclusion      = ratObj?.conclusion || mod.conclusion || null;
  const sources         = mod.sources || mod.evidence_sources || [];

  const evidenceCount = positiveFactors.length + riskFactors.length;
  const hasDetail = summary || evidenceCount > 0 || ruleConditions || businessImpact || sources.length > 0 || mod.score != null;

  const { position: clampedPosition, label, markerColor } = getModifierRisk(mod);

  const heatGradient = 'linear-gradient(to right, #16A34A, #84CC16, #EAB308, #F97316, #DC2626)';

  return (
    <div style={{ borderBottom: '1px solid #F1F5F9', padding: '16px 20px', background: expanded ? '#FAFBFC' : '#FFFFFF', transition: 'background 0.2s ease' }}>
      <div 
        onClick={() => hasDetail && setExpanded(v => !v)}
        style={{ cursor: hasDetail ? 'pointer' : 'default' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              width: '28px', height: '28px', borderRadius: '6px', background: '#F1F5F9', 
              color: '#64748B', display: 'flex', alignItems: 'center', justifyContent: 'center', 
              fontSize: '0.75rem', fontWeight: '700', fontFamily: 'monospace'
            }}>
              {String(index + 1).padStart(2, '0')}
            </div>
            <div>
              <div style={{ fontWeight: '700', color: '#0F172A', fontSize: '0.95rem' }}>
                {mod.name || mod.modifier_name || 'Unknown Modifier'}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748B', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontWeight: '700', color: markerColor }}>{label}</span>
              </div>
            </div>
          </div>
          <div style={{ padding: '4px' }}>
            {hasDetail ? (expanded ? <ChevronUp size={18} color="#94A3B8" /> : <ChevronDown size={18} color="#94A3B8" />) : null}
          </div>
        </div>
        
        {/* Continuous Risk Scale */}
        <div style={{ position: 'relative', width: '100%', padding: '0 8px', boxSizing: 'border-box' }}>
          <div style={{ height: '8px', background: heatGradient, borderRadius: '4px', width: '100%' }} />
          
          {/* Marker */}
          <div
            onMouseEnter={(e) => { e.stopPropagation(); setHoverMarker(true); }}
            onMouseLeave={(e) => { e.stopPropagation(); setHoverMarker(false); }}
            onClick={(e) => e.stopPropagation()}
            style={{
              position: 'absolute',
              top: '50%',
              left: `calc(${clampedPosition}% - 8px)`,
              transform: 'translateY(-50%)',
              width: '16px',
              height: '16px',
              background: '#FFFFFF',
              border: `3px solid ${markerColor}`,
              borderRadius: '50%',
              boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
              transition: 'left 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s',
              cursor: 'pointer',
              zIndex: 20
            }}
          >
            {/* Hover Tooltip */}
            <div style={{
              position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
              marginBottom: '10px', background: '#0F172A', color: '#FFF', padding: '10px 14px',
              borderRadius: '8px', fontSize: '0.75rem', whiteSpace: 'nowrap',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)', zIndex: 50,
              opacity: hoverMarker ? 1 : 0, visibility: hoverMarker ? 'visible' : 'hidden',
              transition: 'all 0.2s', pointerEvents: 'none'
            }}>
              <div style={{ fontWeight: '800', marginBottom: '6px', color: markerColor }}>{label}</div>
              {mod.score != null && <div style={{ color: '#94A3B8', marginBottom: '2px' }}>Raw Score: <span style={{ color: '#F8FAFC', fontWeight: '600' }}>{mod.score}</span></div>}
              <div style={{ color: '#94A3B8', marginBottom: '2px' }}>Normalized: <span style={{ color: '#F8FAFC', fontWeight: '600' }}>{clampedPosition.toFixed(0)}%</span></div>
              <div style={{ color: '#94A3B8', marginBottom: '2px' }}>Confidence: <span style={{ color: '#F8FAFC', fontWeight: '600' }}>{mod.score != null ? 'High' : 'Standard'}</span></div>
              <div style={{ color: '#94A3B8' }}>Evidence Count: <span style={{ color: '#F8FAFC', fontWeight: '600' }}>{evidenceCount}</span></div>
              
              <div style={{
                position: 'absolute', top: '100%', left: '50%', transform: 'translateX(-50%)',
                borderLeft: '5px solid transparent', borderRight: '5px solid transparent',
                borderTop: '5px solid #0F172A'
              }} />
            </div>
          </div>
        </div>
        
        {/* Scale Labels */}
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: '#94A3B8', fontWeight: '600', marginTop: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          <span>Highly Favorable</span>
          <span>Average</span>
          <span>Unfavorable</span>
        </div>
      </div>

      {expanded && hasDetail && (
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px dashed #E2E8F0', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          
          {summary && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '6px' }}>
                Reason for Rating
              </div>
              <p style={{ margin: 0, fontSize: '0.85rem', color: '#334155', lineHeight: 1.6 }}>
                {typeof summary === 'string' ? summary : JSON.stringify(summary)}
              </p>
            </div>
          )}

          {(positiveFactors?.length > 0 || riskFactors?.length > 0) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              {Array.isArray(positiveFactors) && positiveFactors.length > 0 && (
                <div style={{ background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '700', color: '#16A34A', letterSpacing: '0.05em', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle size={14} /> Evidence: Strengths
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {positiveFactors.map((f, i) => <li key={i} style={{ fontSize: '0.82rem', color: '#14532D', lineHeight: 1.4 }}>{f}</li>)}
                  </ul>
                </div>
              )}

              {Array.isArray(riskFactors) && riskFactors.length > 0 && (
                <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', padding: '12px' }}>
                  <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '700', color: '#DC2626', letterSpacing: '0.05em', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <AlertTriangle size={14} /> Evidence: Risk Factors
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {riskFactors.map((f, i) => <li key={i} style={{ fontSize: '0.82rem', color: '#7F1D1D', lineHeight: 1.4 }}>{f}</li>)}
                  </ul>
                </div>
              )}
            </div>
          )}

          {ruleConditions && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '6px' }}>Business Rule</div>
              <div style={{ fontSize: '0.82rem', color: '#475569', background: '#F8FAFC', padding: '10px 14px', borderRadius: '6px', border: '1px solid #E2E8F0', lineHeight: 1.5 }}>
                {Array.isArray(ruleConditions) ? ruleConditions.join(' AND ') : ruleConditions}
              </div>
            </div>
          )}

          {businessImpact && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '6px' }}>Business Impact</div>
              <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {(Array.isArray(businessImpact) ? businessImpact : [businessImpact])
                  .map((imp, i) => <li key={i} style={{ fontSize: '0.82rem', color: '#334155', lineHeight: 1.5 }}>{imp}</li>)}
              </ul>
            </div>
          )}

          {conclusion && (
            <div style={{ fontSize: '0.85rem', color: '#0F172A', fontWeight: '600', borderTop: '1px solid #F1F5F9', paddingTop: '12px' }}>
              Conclusion: <span style={{ fontWeight: '400', color: '#334155' }}>{conclusion}</span>
            </div>
          )}

          {Array.isArray(sources) && sources.length > 0 && (
            <div>
              <div style={{ fontSize: '0.7rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '8px' }}>
                Source References ({sources.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {sources.slice(0, 5).map((src, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', color: '#2563EB', background: '#EFF6FF', padding: '6px 12px', borderRadius: '6px', border: '1px solid #BFDBFE', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {typeof src === 'string' ? src : src.url || src.title || JSON.stringify(src)}
                  </div>
                ))}
                {sources.length > 5 && <div style={{ fontSize: '0.75rem', color: '#94A3B8', fontWeight: '600' }}>+{sources.length - 5} more sources</div>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Portfolio Heat Map ───────────────────────────────────────────────────────

function PortfolioHeatMap({ companies, onSelectCompany, selectedCompanyId }) {
  const [hoveredMod, setHoveredMod] = useState(null);

  const allModifiers = useMemo(() => {
    const mods = new Set();
    companies.forEach(c => {
      const mList = c.rawData?.modifiers || [];
      mList.forEach(m => {
        const name = m.name || m.modifier_name;
        if (name) mods.add(name);
      });
    });
    return Array.from(mods).sort();
  }, [companies]);

  if (companies.length === 0 || allModifiers.length === 0) return null;

  return (
    <Card style={{ marginTop: '20px', overflow: 'hidden' }}>
      <CardHeader title="Portfolio Heat Map" subtitle="Modifier concentration across the filtered portfolio" />
      <div style={{ overflowX: 'auto', padding: '0', paddingBottom: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '700', position: 'sticky', left: 0, background: '#FFF', zIndex: 10, minWidth: '180px' }}>Company</th>
              {allModifiers.map(mod => (
                <th key={mod}
                    onMouseEnter={() => setHoveredMod(mod)}
                    onMouseLeave={() => setHoveredMod(null)}
                    style={{ 
                      padding: '8px', borderBottom: '2px solid #E2E8F0', 
                      writingMode: 'vertical-rl', transform: 'rotate(180deg)',
                      textAlign: 'left', color: hoveredMod === mod ? '#0F172A' : '#94A3B8',
                      transition: 'background 0.2s, color 0.2s', cursor: 'default', height: '160px',
                      background: hoveredMod === mod ? '#F8FAFC' : 'transparent'
                    }}>
                  {mod}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {companies.map(c => {
              const mList = c.rawData?.modifiers || [];
              const isActive = selectedCompanyId === c.id;
              return (\
                <tr key={c.id} 
                    onClick={() => onSelectCompany(c.id)}
                    style={{ 
                      cursor: 'pointer',
                      background: isActive ? '#F0F9FF' : 'transparent',
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#FAFBFC'; }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}>
                  <td style={{ padding: '12px 16px', borderBottom: '1px solid #F1F5F9', fontWeight: '700', color: isActive ? '#0284C7' : '#334155', position: 'sticky', left: 0, background: isActive ? '#F0F9FF' : '#FFF', transition: 'background 0.2s, color 0.2s' }}>
                    {c.company}
                  </td>
                  {allModifiers.map(modName => {
                    const mod = mList.find(m => (m.name || m.modifier_name) === modName);
                    let cellBg = '#F1F5F9';
                    let tooltip = 'No data';
                    if (mod) {
                       const { markerColor, label } = getModifierRisk(mod);
                       cellBg = markerColor;
                       tooltip = `${label} - ${modName}`;
                    }
                    return (
                      <td key={modName}
                          title={tooltip}
                          onMouseEnter={() => setHoveredMod(modName)}
                          onMouseLeave={() => setHoveredMod(null)}
                          style={{ padding: '4px', borderBottom: '1px solid #F1F5F9', textAlign: 'center', background: hoveredMod === modName ? '#F8FAFC' : 'transparent', transition: 'background 0.2s' }}>
                        <div style={{ width: '100%', minWidth: '24px', height: '24px', background: cellBg, borderRadius: '4px', opacity: mod ? 1 : 0.15, transition: 'all 0.2s', margin: '0 auto' }} />
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function PortfolioDashboard({ rows }) {
  const [selectedCategory, setSelectedCategory]   = useState(null);
  const [selectedCompanyId, setSelectedCompanyId] = useState(null);
  const [searchQuery, setSearchQuery]             = useState('');
  const [sortBy, setSortBy]                       = useState('risk');

  const completedRows = useMemo(() => rows.filter(r => r.status === 'Completed' && r.verdict), [rows]);
  const failedCount   = useMemo(() => rows.filter(r => r.status === 'Failed').length, [rows]);
  const skippedCount  = useMemo(() => rows.filter(r => r.status === 'Invalid' || r.status === 'Missing Domain').length, [rows]);
  const totalUploaded = rows.length;
  const totalCompanies = completedRows.length;

  const rowConfidence = useCallback((row) => {
    if (row.confidence != null) return row.confidence;
    return parseConf(getFinalVerdict(row).underwritingScore ?? getFinalVerdict(row).confidence_score);
  }, []);

  const distribution = useMemo(() => {
    const counts = {};
    VERDICT_BUCKETS.forEach(v => { counts[v] = 0; });
    completedRows.forEach(row => {
      const bucket = normaliseVerdict(row.verdict || 'Unknown');
      counts[bucket] = (counts[bucket] || 0) + 1;
    });
    return VERDICT_BUCKETS.map(verdict => ({
      name: verdict,
      value: counts[verdict],
      percentage: totalCompanies > 0 ? ((counts[verdict] / totalCompanies) * 100).toFixed(1) : '0.0',
      ...VERDICT_CONFIG[verdict],
    }));
  }, [completedRows, totalCompanies]);

  const pieData    = useMemo(() => distribution.filter(d => d.value > 0), [distribution]);

  const displayList = useMemo(() => {
    let list = selectedCategory
      ? completedRows.filter(r => normaliseVerdict(r.verdict) === selectedCategory)
      : completedRows;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(r => {
        const industry = getField(getWikidata(r).industry) || '';
        return (
          r.company.toLowerCase().includes(q) ||
          r.domain.toLowerCase().includes(q)  ||
          industry.toLowerCase().includes(q)
        );
      });
    }

    const sorted = [...list];
    if      (sortBy === 'risk')  sorted.sort((a, b) => (RISK_SORT_ORDER[normaliseVerdict(a.verdict)] ?? 5) - (RISK_SORT_ORDER[normaliseVerdict(b.verdict)] ?? 5));
    else if (sortBy === 'low')   sorted.sort((a, b) => (RISK_SORT_ORDER[normaliseVerdict(b.verdict)] ?? 5) - (RISK_SORT_ORDER[normaliseVerdict(a.verdict)] ?? 5));
    else if (sortBy === 'name')  sorted.sort((a, b) => a.company.localeCompare(b.company));
    else if (sortBy === 'conf')  sorted.sort((a, b) => (rowConfidence(b) ?? 0) - (rowConfidence(a) ?? 0));
    return sorted;
  }, [selectedCategory, completedRows, searchQuery, sortBy, rowConfidence]);

  const selectedCompany = useMemo(() =>
    selectedCompanyId !== null ? completedRows.find(r => r.id === selectedCompanyId) ?? null : null
  , [selectedCompanyId, completedRows]);

  const insights = useMemo(() => {
    const highRisk   = completedRows.filter(r => { const b = normaliseVerdict(r.verdict); return b === 'Unfavorable' || b === 'Partially Unfavorable'; })
      .sort((a, b) => (RISK_SORT_ORDER[normaliseVerdict(a.verdict)] ?? 5) - (RISK_SORT_ORDER[normaliseVerdict(b.verdict)] ?? 5));
    const lowRisk    = completedRows.filter(r => { const b = normaliseVerdict(r.verdict); return b === 'Favorable' || b === 'Partially Favorable'; })
      .sort((a, b) => (RISK_SORT_ORDER[normaliseVerdict(a.verdict)] ?? 5) - (RISK_SORT_ORDER[normaliseVerdict(b.verdict)] ?? 5));
    const needReview = completedRows.filter(r => normaliseVerdict(r.verdict) === 'Unknown' || (rowConfidence(r) ?? 100) < 40);
    const missing    = completedRows.filter(r => !r.rawData?.modifiers || r.rawData.modifiers.length === 0);
    const confs      = completedRows.map(r => rowConfidence(r) ?? 0).filter(c => c > 0);
    const avgConf    = confs.length ? (confs.reduce((a, b) => a + b, 0) / confs.length).toFixed(1) : null;
    const industries = {};
    completedRows.forEach(r => {
      const ind = getField(getWikidata(r).industry);
      if (ind) industries[ind] = (industries[ind] || 0) + 1;
    });
    const topIndustry = Object.entries(industries).sort((a, b) => b[1] - a[1])[0] || null;
    return { highRisk, lowRisk, needReview, missing, avgConf, topIndustry };
  }, [completedRows, rowConfidence]);

  if (totalCompanies === 0 && failedCount === 0) return null;

  const clearFilter     = () => { setSelectedCategory(null); setSelectedCompanyId(null); setSearchQuery(''); };
  const selectCategory  = (name) => { setSelectedCategory(name); setSelectedCompanyId(null); setSearchQuery(''); };

  const renderPieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
    if (percent < 0.06) return null;
    const R = Math.PI / 180;
    const r = innerRadius + (outerRadius - innerRadius) * 0.5;
    return (
      <text x={cx + r * Math.cos(-midAngle * R)} y={cy + r * Math.sin(-midAngle * R)}
        fill="white" textAnchor="middle" dominantBaseline="central" fontSize="0.74rem" fontWeight="bold">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    );
  };

  return (
    <div style={{ marginTop: '36px', borderTop: '2px solid #E8EDF2', paddingTop: '28px' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <div style={{ width: 4, height: 20, background: 'var(--accent-orange, #F26A21)', borderRadius: '2px' }} />
            <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#0F172A', fontWeight: '800', letterSpacing: '-0.02em' }}>Portfolio Risk Dashboard</h2>
          </div>
          <div style={{ display: 'flex', gap: '18px', paddingLeft: '14px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', color: '#64748B' }}>
              <Users size={12} color="#64748B" />
              <span><strong style={{ color: '#0F172A' }}>{totalUploaded}</strong> Uploaded</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', color: '#16A34A' }}>
              <CheckCircle size={12} color="#16A34A" />
              <span><strong>{totalCompanies}</strong> Processed</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', color: '#DC2626' }}>
              <XCircle size={12} color="#DC2626" />
              <span><strong>{failedCount}</strong> Failed</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', color: '#CA8A04' }}>
              <Square size={12} color="#CA8A04" />
              <span><strong>{skippedCount}</strong> Skipped</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.78rem', color: '#94A3B8' }}>
              <Clock size={12} color="#94A3B8" />
              <span>Updated {new Date().toLocaleTimeString()}</span>
            </div>
          </div>
        </div>
        {selectedCategory && (
          <button onClick={clearFilter} style={{ display: 'flex', alignItems: 'center', gap: '5px', background: '#F1F5F9', border: '1px solid #E2E8F0', padding: '6px 12px', borderRadius: '7px', color: '#64748B', fontWeight: '600', fontSize: '0.8rem', cursor: 'pointer' }}>
            <ArrowLeft size={13} /> Clear Filter
          </button>
        )}
      </div>

      {totalCompanies === 0 ? (
        <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '10px', padding: '36px 24px', textAlign: 'center', color: '#475569', marginBottom: '24px', transition: 'all 0.3s' }}>
          <Database size={32} color="#94A3B8" style={{ margin: '0 auto 12px' }} />
          <div style={{ fontSize: '1.05rem', fontWeight: '700', color: '#0F172A', marginBottom: '6px' }}>No Risk Intelligence Available</div>
          <div style={{ fontSize: '0.85rem' }}>No companies have successfully completed the automated underwriting extraction process.</div>
        </div>
      ) : (
        <>
          {/* Main Grid: Distribution + List */}
          <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '14px', marginBottom: '14px', alignItems: 'start' }}>
            <Card>
              <CardHeader title="Risk Profile Distribution" subtitle="Click a segment to filter" />
              <div style={{ padding: '16px' }}>
                <div style={{ width: '100%', height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        innerRadius={30}
                        paddingAngle={2}
                        label={renderPieLabel}
                        labelLine={false}
                        onClick={(entry) => selectCategory(entry.name)}
                        style={{ cursor: 'pointer' }}
                      >
                        {pieData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<PieTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader 
                title="Analyzed Accounts" 
                subtitle={`${displayList.length} accounts`}
                action={
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input 
                      type="text" 
                      placeholder="Search accounts..." 
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #E2E8F0', fontSize: '0.75rem' }}
                    />
                  </div>
                }
              />
              <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                {displayList.map(company => {
                  const isSelected = selectedCompanyId === company.id;
                  const verdict = company.verdict || 'Unknown';
                  const { color } = resolveRatingStyle(verdict);
                  return (
                    <div 
                      key={company.id}
                      onClick={() => setSelectedCompanyId(isSelected ? null : company.id)}
                      style={{
                        padding: '12px 16px',
                        borderBottom: '1px solid #F1F5F9',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        background: isSelected ? '#F0F9FF' : 'transparent',
                        borderLeft: isSelected ? '4px solid #0284C7' : '4px solid transparent'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: '700', fontSize: '0.85rem', color: '#0F172A' }}>{company.company}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748B' }}>{company.domain}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <RatingBadge verdict={verdict} />
                        <ChevronRight size={14} color="#94A3B8" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </div>

          {/* Selected Company Details View */}
          {selectedCompany && (
            <div id="company-details-section" style={{ display: 'grid', gridTemplateColumns: '290px 1fr', gap: '14px', marginBottom: '16px', alignItems: 'start', transition: 'all 0.3s ease' }}>
              <Card>
                <CardHeader title="Account Summary" />
                <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <MetaChip label="Company" value={selectedCompany.company} />
                  <MetaChip label="Domain" value={selectedCompany.domain} />
                  <MetaChip label="Industry" value={getWikidata(selectedCompany).industry} />
                  <MetaChip label="Country" value={getWikidata(selectedCompany).country} />
                  <MetaChip label="Revenue" value={getReconciledProfile(selectedCompany).revenue} />
                  <div>
                    <div style={{ fontSize: '0.68rem', color: '#94A3B8', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.05em', marginBottom: '3px' }}>Final Risk Verdict</div>
                    <RatingBadge verdict={selectedCompany.verdict} />
                  </div>
                </div>
              </Card>

              <Card>
                <CardHeader 
                  title="Modifier Breakdown" 
                  subtitle={`${(selectedCompany.rawData?.modifiers || []).length} modifiers evaluated`} 
                />
                <div>
                  {(selectedCompany.rawData?.modifiers || []).map((mod, idx) => (
                    <ModifierHeatRow key={mod.name || idx} mod={mod} index={idx} />
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* ── Portfolio Heat Map ── */}
          <PortfolioHeatMap 
            companies={displayList} 
            selectedCompanyId={selectedCompanyId} 
            onSelectCompany={(id) => {
              setSelectedCompanyId(id);
              document.querySelector('#company-details-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }} 
          />
        </>
      )}
    </div>
  );
}
