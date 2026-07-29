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
// API response keys (from api.py format_analysis_response):
//   final_verdict.riskCategory      = verdict string (NOT .verdict)
//   final_verdict.underwritingScore = confidence as "72%" (NOT .confidence_score)
//   reconciled_profile.revenue      = flat string (NOT .financials.revenue)
//   wikidata_output.country         = country (NOT reconciled_profile.headquarters.country)
//   wikidata_output.industry        = industry (NOT reconciled_profile.firmographics.industry)

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

  const rating  = mod.rating || mod.modifier_value || 'Unknown';
  const { color, bg } = resolveRatingStyle(rating);
  const ratObj  = (typeof mod.rationale === 'object' && mod.rationale !== null) ? mod.rationale : null;

  const summary         = ratObj?.decision_summary || ratObj?.reason || (typeof mod.rationale === 'string' ? mod.rationale : null) || mod.summary || null;
  const positiveFactors = mod.positive_factors || ratObj?.positive_factors || [];
  const riskFactors     = mod.risk_factors     || ratObj?.risk_factors     || [];
  const ruleConditions  = ratObj?.rule_conditions || null;
  const businessImpact  = ratObj?.business_impact || null;
  const conclusion      = ratObj?.conclusion || mod.conclusion || null;
  const sources         = mod.sources || mod.evidence_sources || [];
  const hasDetail       = summary || positiveFactors.length > 0 || riskFactors.length > 0 || ruleConditions || businessImpact || sources.length > 0;

  return (
    <div style={{ borderBottom: '1px solid #F8FAFC' }}>
      <button
        onClick={() => hasDetail && setExpanded(v => !v)}
        style={{
          width: '100%', display: 'grid',
          gridTemplateColumns: '26px 1fr auto auto auto',
          alignItems: 'center', gap: '10px',
          padding: '11px 16px', background: 'transparent', border: 'none',
          cursor: hasDetail ? 'pointer' : 'default',
          borderLeft: `4px solid ${color}`,
          transition: 'background 0.12s', textAlign: 'left',
        }}
        onMouseEnter={e => { if (hasDetail) e.currentTarget.style.background = '#F8FAFC'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
      >
        <span style={{ fontSize: '0.7rem', color: '#CBD5E1', fontFamily: 'monospace', fontWeight: '700' }}>
          {String(index + 1).padStart(2, '0')}
        </span>
        <span style={{ fontWeight: '600', color: '#1E293B', fontSize: '0.865rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {mod.name || mod.modifier_name || 'Unknown Modifier'}
        </span>
        {(mod.score !== undefined && mod.score !== null) && (
          <span style={{ fontSize: '0.7rem', fontWeight: '700', fontFamily: 'monospace', background: 'rgba(242,106,33,0.08)', color: '#EA580C', border: '1px solid rgba(242,106,33,0.2)', padding: '2px 7px', borderRadius: '4px', flexShrink: 0 }}>
            {mod.score}
          </span>
        )}
        <span style={{ background: bg, color, border: `1px solid ${color}30`, padding: '3px 9px', borderRadius: '20px', fontSize: '0.68rem', fontWeight: '700', flexShrink: 0 }}>
          {rating}
        </span>
        {hasDetail
          ? (expanded ? <ChevronUp size={13} color="#94A3B8" /> : <ChevronDown size={13} color="#94A3B8" />)
          : <span style={{ width: 13 }} />
        }
      </button>

      {expanded && hasDetail && (
        <div style={{ borderLeft: `4px solid ${color}`, background: '#FAFBFC', padding: '14px 18px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>

          {mod.score != null && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '3px' }}>Confidence</div>
              <div style={{ fontSize: '0.82rem', color: '#0F172A', fontWeight: '600' }}>{mod.score} / 1.00</div>
            </div>
          )}

          {summary && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>
                Reason for Rating
              </div>
              <p style={{ margin: 0, fontSize: '0.82rem', color: '#475569', lineHeight: 1.65 }}>
                {typeof summary === 'string' ? summary : JSON.stringify(summary)}
              </p>
            </div>
          )}

          {Array.isArray(positiveFactors) && positiveFactors.length > 0 && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#16A34A', letterSpacing: '0.05em', marginBottom: '5px' }}>✓ Favorable Evidence</div>
              <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {positiveFactors.map((f, i) => <li key={i} style={{ fontSize: '0.81rem', color: '#166534' }}>{f}</li>)}
              </ul>
            </div>
          )}

          {Array.isArray(riskFactors) && riskFactors.length > 0 && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#DC2626', letterSpacing: '0.05em', marginBottom: '5px' }}>⚠ Unfavorable Evidence</div>
              <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {riskFactors.map((f, i) => <li key={i} style={{ fontSize: '0.81rem', color: '#991B1B' }}>{f}</li>)}
              </ul>
            </div>
          )}

          {ruleConditions && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>Business Rule</div>
              <div style={{ fontSize: '0.81rem', color: '#475569', background: '#F1F5F9', padding: '8px 10px', borderRadius: '6px', lineHeight: 1.55 }}>
                {Array.isArray(ruleConditions) ? ruleConditions.join(' AND ') : ruleConditions}
              </div>
            </div>
          )}

          {businessImpact && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>Reasoning / Business Impact</div>
              <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                {(Array.isArray(businessImpact) ? businessImpact : [businessImpact])
                  .map((imp, i) => <li key={i} style={{ fontSize: '0.81rem', color: '#475569' }}>{imp}</li>)}
              </ul>
            </div>
          )}

          {conclusion && (
            <div style={{ fontSize: '0.81rem', color: '#0F172A', fontWeight: '600', borderTop: '1px solid #F1F5F9', paddingTop: '10px' }}>
              Conclusion: <span style={{ fontWeight: '400', color: '#475569' }}>{conclusion}</span>
            </div>
          )}

          {Array.isArray(sources) && sources.length > 0 && (
            <div>
              <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>
                Source References ({sources.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {sources.slice(0, 5).map((src, i) => (
                  <div key={i} style={{ fontSize: '0.77rem', color: '#3B82F6', background: '#EFF6FF', padding: '4px 10px', borderRadius: '4px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {typeof src === 'string' ? src : src.url || src.title || JSON.stringify(src)}
                  </div>
                ))}
                {sources.length > 5 && <div style={{ fontSize: '0.73rem', color: '#94A3B8' }}>+{sources.length - 5} more sources</div>}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function PortfolioDashboard({ rows }) {
  const [selectedCategory, setSelectedCategory]   = useState(null);
  // ⚠️  CRITICAL: use null (not 0) as sentinel — row id can be 0 (first row)
  const [selectedCompanyId, setSelectedCompanyId] = useState(null);
  const [searchQuery, setSearchQuery]             = useState('');
  const [sortBy, setSortBy]                       = useState('risk');

  // Derive sets from all rows (including failed and skipped)
  const completedRows = useMemo(() => rows.filter(r => r.status === 'Completed' && r.verdict), [rows]);
  const failedCount   = useMemo(() => rows.filter(r => r.status === 'Failed').length, [rows]);
  const skippedCount  = useMemo(() => rows.filter(r => r.status === 'Invalid' || r.status === 'Missing Domain').length, [rows]);
  const totalUploaded = rows.length;
  const totalCompanies = completedRows.length;

  // Row confidence — stored as parsed number on the row from BatchAnalysisModal
  const rowConfidence = useCallback((row) => {
    if (row.confidence != null) return row.confidence;
    // fallback: try to parse from rawData directly
    return parseConf(getFinalVerdict(row).underwritingScore ?? getFinalVerdict(row).confidence_score);
  }, []);

  // Distribution — use normalised bucket names
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
  const allUnknown = useMemo(() => pieData.length === 1 && pieData[0].name === 'Unknown', [pieData]);

  // Company display list — search across name, domain, industry
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

  // ⚠️  BUG FIX: `selectedCompanyId !== null` — because id can be 0 (falsy)
  const selectedCompany = useMemo(() =>
    selectedCompanyId !== null ? completedRows.find(r => r.id === selectedCompanyId) ?? null : null
  , [selectedCompanyId, completedRows]);

  // Portfolio Insights — use corrected accessors
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
      // industry lives in wikidata_output
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

  // ── RENDER ─────────────────────────────────────────────────────────────────

  return (
    <div style={{ marginTop: '36px', borderTop: '2px solid #E8EDF2', paddingTop: '28px' }}>

      {/* ── Dashboard Header ──────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <div style={{ width: 4, height: 20, background: 'var(--accent-orange, #F26A21)', borderRadius: '2px' }} />
            <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#0F172A', fontWeight: '800', letterSpacing: '-0.02em' }}>Portfolio Risk Dashboard</h2>
          </div>
          {/* Stats row */}
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

      {/* ── Demo Risk Alert Banner ── */}
      {(totalCompanies > 0 && (insights.highRisk.length / totalCompanies) > 0.2) && (
        <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', padding: '14px 18px', marginBottom: '24px', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
          <AlertTriangle size={20} color="#DC2626" style={{ marginTop: '2px' }} />
          <div>
            <div style={{ fontSize: '0.9rem', fontWeight: '700', color: '#991B1B', marginBottom: '4px' }}>
              Portfolio Alert: High Concentration of Unfavorable Risk
            </div>
            <div style={{ fontSize: '0.82rem', color: '#B91C1C', lineHeight: 1.5 }}>
              More than 20% ({( (insights.highRisk.length / totalCompanies) * 100 ).toFixed(0)}%) of the processed portfolio has been flagged as Unfavorable or Partially Unfavorable. Immediate review recommended.
            </div>
          </div>
        </div>
      )}

      {totalCompanies === 0 ? (
        <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px', padding: '24px', textAlign: 'center', color: '#DC2626', fontSize: '0.9rem', fontWeight: '600', marginBottom: '24px' }}>
          All batch rows failed. No portfolio data to display.
        </div>
      ) : (
        <>
          {/* ── 1. Summary Cards ────────────────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', marginBottom: '20px' }}>

            {/* Total */}
            <div
              onClick={clearFilter}
              style={{
                background: !selectedCategory ? '#0F172A' : '#FFFFFF',
                padding: '14px 16px', borderRadius: '10px',
                border: `1.5px solid ${!selectedCategory ? '#0F172A' : '#E2E8F0'}`,
                cursor: 'pointer', transition: 'all 0.18s',
                boxShadow: !selectedCategory ? '0 4px 12px rgba(15,23,42,0.18)' : '0 1px 3px rgba(0,0,0,0.04)',
              }}
              onMouseEnter={e => { if (selectedCategory) { e.currentTarget.style.borderColor = '#94A3B8'; e.currentTarget.style.background = '#F8FAFC'; } }}
              onMouseLeave={e => { if (selectedCategory) { e.currentTarget.style.borderColor = '#E2E8F0'; e.currentTarget.style.background = '#FFFFFF'; } }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.67rem', fontWeight: '700', color: !selectedCategory ? '#94A3B8' : '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Total</span>
                <Activity size={13} color={!selectedCategory ? '#475569' : '#94A3B8'} />
              </div>
              <div style={{ fontSize: '1.7rem', fontWeight: '800', color: !selectedCategory ? '#FFFFFF' : '#0F172A', lineHeight: 1 }}>{totalCompanies}</div>
              <div style={{ fontSize: '0.72rem', color: !selectedCategory ? '#475569' : '#94A3B8', marginTop: '4px' }}>All Companies</div>
            </div>

            {distribution
              .filter(item => !(item.name === 'Unknown' && item.value === 0))
              .map(item => {
                const Icon     = item.icon;
                const isActive = selectedCategory === item.name;
                const isEmpty  = item.value === 0;
                return (
                  <div
                    key={item.name}
                    onClick={() => !isEmpty && selectCategory(item.name)}
                    style={{
                      background: isActive ? item.bg : '#FFFFFF',
                      padding: '14px 16px', borderRadius: '10px',
                      border: `1.5px solid ${isActive ? item.color : '#E2E8F0'}`,
                      borderTop: `3px solid ${item.color}`,
                      cursor: isEmpty ? 'default' : 'pointer',
                      opacity: isEmpty ? 0.38 : 1,
                      transition: 'all 0.18s',
                      boxShadow: isActive ? `0 4px 12px ${item.color}22` : '0 1px 3px rgba(0,0,0,0.04)',
                    }}
                    onMouseEnter={e => { if (!isEmpty && !isActive) { e.currentTarget.style.borderColor = item.color; e.currentTarget.style.background = item.bg; } }}
                    onMouseLeave={e => { if (!isActive) { e.currentTarget.style.borderColor = '#E2E8F0'; e.currentTarget.style.background = '#FFFFFF'; } }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.65rem', fontWeight: '700', color: item.color, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{item.name}</span>
                      <Icon size={13} color={item.color} />
                    </div>
                    <div style={{ fontSize: '1.65rem', fontWeight: '800', color: '#0F172A', lineHeight: 1 }}>{item.value}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94A3B8', marginTop: '4px' }}>{item.percentage}% of portfolio</div>
                  </div>
                );
              })}
          </div>

          {/* ── 2. Donut + 3. Company List ──────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: '270px 1fr', gap: '14px', marginBottom: '16px', alignItems: 'start' }}>

            {/* Donut */}
            <Card>
              <CardHeader title="Risk Distribution" subtitle="Click slice to filter" />
              <div style={{ padding: '14px 10px 12px' }}>
                {allUnknown ? (
                  <div style={{ textAlign: 'center', padding: '24px 12px' }}>
                    <HelpCircle size={30} color="#CBD5E1" style={{ marginBottom: 8 }} />
                    <div style={{ fontWeight: '600', color: '#475569', fontSize: '0.85rem', marginBottom: '4px' }}>Analysis still in progress</div>
                    <div style={{ fontSize: '0.76rem', color: '#94A3B8', lineHeight: 1.5 }}>All verdicts returned Unknown. Ensure backend scoring completed.</div>
                  </div>
                ) : (
                  <>
                    <div style={{ width: '100%', height: 190 }}>
                      <ResponsiveContainer>
                        <PieChart>
                          <Pie
                            data={pieData} cx="50%" cy="50%"
                            labelLine={false} label={renderPieLabel}
                            outerRadius={82} innerRadius={30}
                            dataKey="value"
                            onClick={d => selectCategory(d.name)}
                            style={{ cursor: 'pointer' }}
                          >
                            {pieData.map((entry, i) => (
                              <Cell
                                key={`cell-${i}`}
                                fill={entry.color}
                                opacity={selectedCategory && selectedCategory !== entry.name ? 0.3 : 1}
                                stroke={selectedCategory === entry.name ? '#1E293B' : 'white'}
                                strokeWidth={selectedCategory === entry.name ? 2 : 1}
                              />
                            ))}
                          </Pie>
                          <Tooltip content={PieTooltip} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', padding: '2px 4px 0' }}>
                      {pieData.map(d => (
                        <button key={d.name}
                          onClick={() => selectCategory(selectedCategory === d.name ? null : d.name)}
                          style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            gap: '8px', padding: '5px 8px', borderRadius: '6px', cursor: 'pointer',
                            background: selectedCategory === d.name ? d.bg : 'transparent',
                            border: `1px solid ${selectedCategory === d.name ? d.color + '60' : 'transparent'}`,
                            transition: 'all 0.12s',
                          }}
                          onMouseEnter={e => { if (selectedCategory !== d.name) e.currentTarget.style.background = '#F8FAFC'; }}
                          onMouseLeave={e => { if (selectedCategory !== d.name) e.currentTarget.style.background = 'transparent'; }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
                            <span style={{ fontSize: '0.75rem', color: '#475569', fontWeight: '500' }}>{d.name}</span>
                          </div>
                          <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#0F172A' }}>
                            {d.value} <span style={{ color: '#94A3B8', fontWeight: '400' }}>({d.percentage}%)</span>
                          </span>
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </Card>

            {/* Company List */}
            <Card>
              <CardHeader
                title={selectedCategory ? selectedCategory : 'All Companies'}
                subtitle={`${displayList.length} ${displayList.length === 1 ? 'company' : 'companies'} · click to inspect`}
              />
              <div style={{ padding: '9px 12px', borderBottom: '1px solid #F1F5F9', display: 'flex', gap: '6px', alignItems: 'center', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '180px', display: 'flex', alignItems: 'center', gap: '6px', background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '5px 10px' }}>
                  <Search size={12} color="#94A3B8" />
                  <input
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search name, domain, or industry…"
                    style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: '0.81rem', color: '#334155', width: '100%' }}
                  />
                </div>
                <div style={{ display: 'flex', gap: '3px', flexWrap: 'wrap' }}>
                  {[['risk', 'Highest Risk'], ['low', 'Lowest Risk'], ['name', 'A–Z'], ['conf', 'Confidence']].map(([val, label]) => (
                    <button key={val} onClick={() => setSortBy(val)} style={{
                      padding: '5px 9px', borderRadius: '5px', fontSize: '0.72rem', fontWeight: '600', cursor: 'pointer',
                      background: sortBy === val ? '#0F172A' : '#F1F5F9',
                      color:      sortBy === val ? '#FFF'    : '#64748B',
                      border:     sortBy === val ? '1px solid #0F172A' : '1px solid #E2E8F0',
                    }}>{label}</button>
                  ))}
                </div>
              </div>

              <div style={{ maxHeight: '360px', overflowY: 'auto' }}>
                {displayList.length === 0 && (
                  <div style={{ padding: '24px', textAlign: 'center', color: '#94A3B8', fontSize: '0.84rem' }}>
                    {searchQuery 
                      ? "No companies match your search criteria." 
                      : selectedCategory 
                        ? `No ${selectedCategory.toLowerCase()} companies found in this portfolio.` 
                        : "No companies available."}
                  </div>
                )}
                {displayList.map(company => {
                  const wikidata  = getWikidata(company);
                  const country   = getField(wikidata.country);
                  const industry  = getField(wikidata.industry);
                  const conf      = rowConfidence(company);
                  const isActive  = selectedCompanyId === company.id;
                  const { color } = resolveRatingStyle(company.verdict || 'Unknown');
                  return (
                    <button
                      key={company.id}
                      onClick={() => setSelectedCompanyId(company.id)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '10px', width: '100%',
                        padding: '10px 12px',
                        background: isActive ? '#F0F9FF' : 'transparent',
                        border: 'none', borderBottom: '1px solid #F8FAFC',
                        borderLeft: `3px solid ${isActive ? '#3B82F6' : 'transparent'}`,
                        cursor: 'pointer', textAlign: 'left', transition: 'background 0.1s',
                      }}
                      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#F8FAFC'; }}
                      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                    >
                      <div style={{ width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: '700', color: isActive ? '#0284C7' : '#0F172A', fontSize: '0.86rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {company.company}
                        </div>
                        <div style={{ fontSize: '0.73rem', color: '#94A3B8', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {company.domain}
                          {country  && <> · {country}</>}
                          {industry && <> · {industry}</>}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '3px', flexShrink: 0 }}>
                        <RatingBadge verdict={company.verdict} />
                        {conf != null && (
                          <span style={{ fontSize: '0.68rem', color: '#94A3B8' }}>{conf}% conf.</span>
                        )}
                      </div>
                      <ChevronRight size={12} color={isActive ? '#3B82F6' : '#D1D5DB'} />
                    </button>
                  );
                })}
              </div>
              <div style={{ padding: '7px 12px', borderTop: '1px solid #F8FAFC', fontSize: '0.72rem', color: '#94A3B8', textAlign: 'right' }}>
                {displayList.length} of {totalCompanies} companies
              </div>
            </Card>
          </div>

          {/* ── 4. Company Details + 5. Modifier Heat Map ────────────────────── */}
          {selectedCompany && (() => {
            const rProfile  = getReconciledProfile(selectedCompany);
            const wiki      = getWikidata(selectedCompany);
            const vData     = getFinalVerdict(selectedCompany);
            const country   = getField(wiki.country);
            const industry  = getField(wiki.industry);
            const revenue   = getField(rProfile.revenue);
            const naics     = getField(rProfile.naics_code);
            const custType  = getField(rProfile.customerType);
            const modifiers = selectedCompany.rawData?.modifiers || [];
            const { color } = resolveRatingStyle(selectedCompany.verdict || 'Unknown');
            // Confidence bar: underwritingScore is "72%" string from backend
            const confScore    = parseConf(vData.underwritingScore ?? vData.confidence_score);
            const evidScore    = getField(vData.evidenceScore ?? vData.evidence_score);
            const confBand     = getField(vData.confidenceBand);
            const riskSummary  = getField(vData.riskSummary   ?? vData.decision_summary);
            const ratingReason = getField(vData.ratingReason  ?? vData.reason);
            const execTime     = selectedCompany.executionTime ? `${selectedCompany.executionTime}s` : null;

            // Generate dynamic summary of top modifiers
            const unfavMods = modifiers.filter(m => {
              const r = (m.rating || m.modifier_value || '').toUpperCase();
              return r.includes('UNFAV');
            });
            const favMods = modifiers.filter(m => {
              const r = (m.rating || m.modifier_value || '').toUpperCase();
              return r.includes('FAV') && !r.includes('UNFAV');
            });
            const isHighRisk = normaliseVerdict(selectedCompany.verdict) === 'Unfavorable' || normaliseVerdict(selectedCompany.verdict) === 'Partially Unfavorable';

            return (
              <div style={{ display: 'grid', gridTemplateColumns: '290px 1fr', gap: '14px', marginBottom: '16px', alignItems: 'start' }}>

                {/* Company Details */}
                <Card>
                  <div style={{ padding: '14px 18px', borderBottom: '1px solid #F1F5F9' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px', marginBottom: '10px' }}>
                      <div>
                        <div style={{ fontSize: '0.98rem', fontWeight: '800', color: '#0F172A', lineHeight: 1.2 }}>{selectedCompany.company}</div>
                        <div style={{ fontSize: '0.74rem', color: '#94A3B8', marginTop: '3px' }}>{selectedCompany.domain}</div>
                      </div>
                      <RatingBadge verdict={selectedCompany.verdict} />
                    </div>
                    {confScore != null && (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.67rem', color: '#94A3B8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Confidence</span>
                          <span style={{ fontSize: '0.76rem', fontWeight: '800', color: '#0F172A' }}>{confScore}%</span>
                        </div>
                        <div style={{ height: '5px', background: '#E2E8F0', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${confScore}%`, background: color, borderRadius: '3px', transition: 'width 0.5s ease' }} />
                        </div>
                      </div>
                    )}
                  </div>

                  <div style={{ padding: '12px 18px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', borderBottom: (riskSummary || ratingReason) ? '1px solid #F1F5F9' : 'none' }}>
                    <MetaChip label="Evidence Score"   value={evidScore} />
                    <MetaChip label="Confidence Band"  value={confBand} />
                    <MetaChip label="Country"          value={country} />
                    <MetaChip label="Industry"         value={industry} />
                    <MetaChip label="Revenue"          value={revenue} />
                    <MetaChip label="NAICS Code"       value={naics} />
                    <MetaChip label="Customer Type"    value={custType} />
                    <MetaChip label="Execution Time"   value={execTime} />
                    <MetaChip label="Modifiers Scored" value={modifiers.length > 0 ? String(modifiers.length) : null} />
                  </div>

                  {(riskSummary || ratingReason || unfavMods.length > 0 || favMods.length > 0) && (
                    <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {riskSummary && (
                        <div>
                          <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>Overall Risk Summary</div>
                          <p style={{ margin: 0, fontSize: '0.8rem', color: '#475569', lineHeight: 1.65, background: '#F8FAFC', padding: '9px 11px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                            {riskSummary}
                          </p>
                        </div>
                      )}
                      
                      {/* Generated dynamic modifier summary */}
                      {(unfavMods.length > 0 || favMods.length > 0) && (
                        <div>
                          <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>Key Drivers</div>
                          <div style={{ background: '#FFFBEB', padding: '9px 11px', borderRadius: '6px', border: '1px solid #FEF08A' }}>
                            {unfavMods.length > 0 && (
                              <div style={{ marginBottom: favMods.length > 0 ? '6px' : '0' }}>
                                <span style={{ fontSize: '0.74rem', fontWeight: '700', color: '#991B1B' }}>Primary Risk Factors:</span>
                                <span style={{ fontSize: '0.74rem', color: '#7F1D1D', marginLeft: '4px' }}>
                                  {unfavMods.map(m => m.name || m.modifier_name).join(', ')}
                                </span>
                              </div>
                            )}
                            {favMods.length > 0 && (
                              <div>
                                <span style={{ fontSize: '0.74rem', fontWeight: '700', color: '#166534' }}>Mitigating Factors:</span>
                                <span style={{ fontSize: '0.74rem', color: '#14532D', marginLeft: '4px' }}>
                                  {favMods.map(m => m.name || m.modifier_name).join(', ')}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {ratingReason && (
                        <div>
                          <div style={{ fontSize: '0.67rem', textTransform: 'uppercase', fontWeight: '700', color: '#64748B', letterSpacing: '0.05em', marginBottom: '5px' }}>Final Rating Explanation</div>
                          <p style={{ margin: 0, fontSize: '0.8rem', color: '#475569', lineHeight: 1.65, background: '#F0FDF4', padding: '9px 11px', borderRadius: '6px', border: '1px solid #BBF7D0' }}>
                            {ratingReason}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Reserving Integration Placeholder */}
                  {isHighRisk && (
                    <div style={{ padding: '12px 18px', borderTop: '1px solid #F1F5F9', background: '#F8FAFC' }}>
                      <button
                        disabled
                        title="Links to the reserving tool in the integrated workflow (Demo mode)"
                        style={{
                          width: '100%', padding: '9px', background: '#E2E8F0', color: '#64748B',
                          border: 'none', borderRadius: '6px', fontSize: '0.82rem', fontWeight: '600',
                          cursor: 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px'
                        }}
                      >
                        <Database size={15} />
                        Open Reserving Analysis
                      </button>
                    </div>
                  )}
                </Card>

                {/* Modifier Heat Map */}
                <Card>
                  <CardHeader
                    title="Modifier Heat Map"
                    subtitle={modifiers.length > 0 ? `${modifiers.length} modifiers · click to expand evidence & reasoning` : undefined}
                  />
                  {modifiers.length === 0 ? (
                    <div style={{ padding: '28px', textAlign: 'center', color: '#94A3B8', fontSize: '0.84rem' }}>
                      Modifier data unavailable. Ensure the extraction agent completed successfully.
                    </div>
                  ) : (
                    <div>
                      {modifiers.map((mod, idx) => (
                        <ModifierHeatRow key={mod.id ?? `mod-${idx}`} mod={mod} index={idx} />
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            );
          })()}

          {/* ── 6. Portfolio Insights ──────────────────────────────────────────── */}
          <Card>
            <CardHeader title="Portfolio Insights" subtitle="Risk intelligence summary for underwriter review" />
            <div style={{ padding: '14px 18px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '10px' }}>

              {/* Avg Confidence */}
              <div style={{ background: '#F0F9FF', borderRadius: '8px', padding: '12px 14px', border: '1px solid #BAE6FD' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Activity size={13} color="#0284C7" />
                  <span style={{ fontSize: '0.67rem', fontWeight: '700', color: '#0284C7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Avg Confidence</span>
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: '800', color: '#0F172A', lineHeight: 1 }}>
                  {insights.avgConf ? `${insights.avgConf}%` : '—'}
                </div>
                <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>across {totalCompanies} companies</div>
              </div>

              {/* Highest Risk Companies */}
              <div style={{ background: '#FEF2F2', borderRadius: '8px', padding: '12px 14px', border: '1px solid #FECACA' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <TrendingDown size={13} color="#DC2626" />
                  <span style={{ fontSize: '0.67rem', fontWeight: '700', color: '#DC2626', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Highest Risk</span>
                </div>
                {insights.highRisk.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>No high-risk companies</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    {insights.highRisk.slice(0, 4).map(r => (
                      <button key={r.id}
                        onClick={() => { setSelectedCompanyId(r.id); setSelectedCategory(normaliseVerdict(r.verdict)); }}
                        style={{ background: 'none', border: 'none', padding: '2px 0', textAlign: 'left', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '600', color: '#991B1B', lineHeight: 1.3, display: 'flex', alignItems: 'center', gap: '5px' }}
                      >
                        <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#DC2626', flexShrink: 0 }} />
                        {r.company}
                      </button>
                    ))}
                    {insights.highRisk.length > 4 && <div style={{ fontSize: '0.7rem', color: '#94A3B8' }}>+{insights.highRisk.length - 4} more</div>}
                  </div>
                )}
              </div>

              {/* Lowest Risk Companies */}
              <div style={{ background: '#F0FDF4', borderRadius: '8px', padding: '12px 14px', border: '1px solid #BBF7D0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <ShieldCheck size={13} color="#16A34A" />
                  <span style={{ fontSize: '0.67rem', fontWeight: '700', color: '#16A34A', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Lowest Risk</span>
                </div>
                {insights.lowRisk.length === 0 ? (
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>No low-risk companies yet</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    {insights.lowRisk.slice(0, 4).map(r => (
                      <button key={r.id}
                        onClick={() => { setSelectedCompanyId(r.id); setSelectedCategory(normaliseVerdict(r.verdict)); }}
                        style={{ background: 'none', border: 'none', padding: '2px 0', textAlign: 'left', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '600', color: '#166534', lineHeight: 1.3, display: 'flex', alignItems: 'center', gap: '5px' }}
                      >
                        <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#16A34A', flexShrink: 0 }} />
                        {r.company}
                      </button>
                    ))}
                    {insights.lowRisk.length > 4 && <div style={{ fontSize: '0.7rem', color: '#94A3B8' }}>+{insights.lowRisk.length - 4} more</div>}
                  </div>
                )}
              </div>

              {/* Needs Review */}
              <div style={{ background: '#FFFBEB', borderRadius: '8px', padding: '12px 14px', border: '1px solid #FDE68A' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <AlertTriangle size={13} color="#D97706" />
                  <span style={{ fontSize: '0.67rem', fontWeight: '700', color: '#D97706', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Needs Review</span>
                </div>
                <div style={{ fontSize: '1.45rem', fontWeight: '800', color: '#0F172A', lineHeight: 1 }}>{insights.needReview.length}</div>
                <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>Unknown verdict or confidence &lt;40%</div>
              </div>

              {/* Missing Data */}
              <div style={{ background: '#F8FAFC', borderRadius: '8px', padding: '12px 14px', border: '1px solid #E2E8F0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <Database size={13} color="#64748B" />
                  <span style={{ fontSize: '0.67rem', fontWeight: '700', color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Missing Data</span>
                </div>
                <div style={{ fontSize: '1.45rem', fontWeight: '800', color: '#0F172A', lineHeight: 1 }}>{insights.missing.length}</div>
                <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>companies with no modifiers</div>
              </div>

              {/* Concentration Risk */}
              <div style={{ background: '#F5F3FF', borderRadius: '8px', padding: '12px 14px', border: '1px solid #DDD6FE' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <TrendingUp size={13} color="#7C3AED" />
                  <span style={{ fontSize: '0.67rem', fontWeight: '700', color: '#7C3AED', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Concentration Risk</span>
                </div>
                {insights.topIndustry ? (
                  <>
                    <div style={{ fontSize: '0.87rem', fontWeight: '700', color: '#4C1D95', lineHeight: 1.2 }}>{insights.topIndustry[0]}</div>
                    <div style={{ fontSize: '0.7rem', color: '#64748B', marginTop: '4px' }}>{insights.topIndustry[1]} companies in same sector</div>
                  </>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: '#94A3B8' }}>No industry data available</div>
                )}
              </div>

            </div>
          </Card>
        </>
      )}
    </div>
  );
}
