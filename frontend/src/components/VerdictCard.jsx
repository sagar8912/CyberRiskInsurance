import React, { useState } from 'react';
import { Gavel, AlertTriangle, ShieldAlert, ChevronDown, ChevronUp, CheckCircle, Info, XCircle, TrendingUp, TrendingDown } from 'lucide-react';

export default function VerdictCard({ data, modifiers = [], claims = [] }) {
  const [isExplanationExpanded, setIsExplanationExpanded] = useState(false);

  if (!data) {
    return (
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity: 0.3, borderStyle: 'dashed' }}>
        <ShieldAlert size={48} color="var(--text-secondary)" style={{ marginBottom: '16px' }} />
        <h3 style={{ color: 'var(--text-secondary)' }}>Awaiting Analysis</h3>
        <p className="text-muted" style={{ fontSize: '0.875rem' }}>Final verdict will appear here.</p>
      </div>
    );
  }

  const isFavorable = data.riskCategory.includes('FAVOURABLE') && !data.riskCategory.includes('UNFAVOURABLE');
  const mainColor = isFavorable ? 'var(--accent-success)' : 'var(--accent-warning)';

  // Parse score string (e.g. "33.3%") to number
  const scoreNum = parseFloat(data.underwritingScore.replace('%','')) || 0;
  const isZeroConfidence = scoreNum === 0;

  // Modifiers Aggregation
  const favorableModifiers = modifiers.filter(m => m.rating.includes('FAVOURABLE') && !m.rating.includes('UNFAVOURABLE'));
  const unfavorableModifiers = modifiers.filter(m => m.rating.includes('UNFAVOURABLE'));
  const neutralModifiers = modifiers.filter(m => m.rating === 'AVERAGE' || m.rating === 'NEUTRAL');

  const riskDrivers = favorableModifiers.slice(0, 3);
  const keyConcerns = unfavorableModifiers.slice(0, 3);

  // Claims Aggregation
  const verifiedClaims = claims.filter(c => c.status.toLowerCase() === 'verified' || (c.status.toLowerCase().includes('verified') && !c.status.toLowerCase().includes('partial'))).length;
  const partialClaims = claims.filter(c => c.status.toLowerCase().includes('partial')).length;
  const unsupportedClaims = claims.filter(c => c.status.toLowerCase() === 'unsupported' || c.status.toLowerCase().includes('unsupported')).length;

  // Circular Progress Component
  const CircularProgress = ({ percentage, color }) => {
    const radius = 36;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div style={{ position: 'relative', width: '90px', height: '90px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg width="90" height="90" style={{ transform: 'rotate(-90deg)', overflow: 'visible' }}>
          <circle cx="45" cy="45" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
          <circle 
            cx="45" cy="45" r={radius} fill="none" stroke={color} strokeWidth="8"
            strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 1s ease-in-out' }}
          />
        </svg>
        <div style={{ position: 'absolute', fontWeight: '800', fontSize: '1.2rem', color }}>
          {percentage}%
        </div>
      </div>
    );
  };

  return (
    <div className="glass-panel" style={{ 
      background: '#FFFFFF',
      border: `1px solid ${isZeroConfidence ? 'var(--accent-warning)' : mainColor}`,
      boxShadow: `0 8px 32px rgba(0, 0, 0, 0.05)`,
      position: 'relative',
      overflow: 'hidden',
      padding: '32px'
    }}>
      {/* Background glowing orb */}
      <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '200px', height: '200px', background: isZeroConfidence ? 'var(--accent-warning)' : mainColor, filter: 'blur(100px)', opacity: 0.15, zIndex: 0, pointerEvents: 'none' }}></div>

      <div style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <h2 style={{ color: isZeroConfidence ? 'var(--accent-warning)' : mainColor, margin: 0, display: 'flex', alignItems: 'center', gap: '12px', fontSize: '1.5rem', textShadow: 'none' }}>
            <Gavel size={28} /> Final Underwriting Verdict
          </h2>
          {(data.humanEscalation || isZeroConfidence) && (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: isZeroConfidence ? 'var(--accent-danger)' : 'var(--accent-warning)', fontWeight: '700', background: isZeroConfidence ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)', padding: '6px 16px', borderRadius: '999px', fontSize: '0.85rem', letterSpacing: '0.05em', border: `1px solid ${isZeroConfidence ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)'}` }}>
              <AlertTriangle size={16} /> {isZeroConfidence ? "IMMEDIATE ESCALATION" : "HUMAN REVIEW REQUIRED"}
            </div>
          )}
        </div>
        
        <div style={{ display: 'flex', gap: '48px', marginBottom: '32px', alignItems: 'center' }}>
          {/* Left: Risk Category */}
          <div style={{ flex: 1.2 }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px', fontWeight: '800', color: '#64748B' }}>Overall Risk Tier</div>
            <div style={{ 
              fontSize: '3.5rem', 
              fontWeight: '900', 
              color: 'transparent',
              backgroundImage: isZeroConfidence ? 'linear-gradient(90deg, #D97706, #F59E0B)' : (isFavorable ? 'linear-gradient(90deg, #059669, #10B981)' : 'linear-gradient(90deg, #DC2626, #EF4444)'),
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              lineHeight: 1.1, 
              letterSpacing: '-0.03em',
              filter: 'drop-shadow(0px 2px 4px rgba(0,0,0,0.05))'
            }}>
              {isZeroConfidence ? "Needs Review" : data.riskCategory}
            </div>
            {isZeroConfidence && (
              <div style={{ color: 'var(--accent-warning)', fontSize: '0.85rem', marginTop: '12px', background: 'rgba(245, 158, 11, 0.1)', padding: '8px 12px', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.2)', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: '600' }}>
                <AlertTriangle size={16} /> Provisional category due to low confidence. (Backend: {data.riskCategory})
              </div>
            )}
          </div>
          
          {/* Right: Circular Confidence */}
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: '24px', background: '#FFFFFF', padding: '20px 24px', borderRadius: '12px', border: '1px solid #E2E8F0', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
            <CircularProgress percentage={scoreNum} color={isZeroConfidence ? '#D97706' : (data.confidenceBand === 'Low' ? '#F59E0B' : '#10B981')} />
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px', fontWeight: '800', color: '#64748B' }}>Evidence Confidence</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '800', color: '#0F172A', marginBottom: '4px' }}>
                {data.confidenceBand} Band
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94A3B8', fontWeight: '500', lineHeight: '1.4' }}>
                Based on fact-checker corroboration engine results.
              </div>
            </div>
          </div>
        </div>

        {/* Middle Row: Distributions (Enterprise Metric Bars) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '32px' }}>
          
          {/* Modifier Distribution Bar */}
          <div style={{ background: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ color: '#64748B', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '800' }}>Modifier Distribution</div>
              <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#0F172A' }}>13 Total</div>
            </div>
            
            <div style={{ display: 'flex', width: '100%', height: '10px', borderRadius: '5px', overflow: 'hidden', marginBottom: '20px', background: '#F1F5F9' }}>
              <div style={{ width: `${(favorableModifiers.length/13)*100}%`, background: '#10B981', transition: 'width 1s ease-in-out' }}></div>
              <div style={{ width: `${(neutralModifiers.length/13)*100}%`, background: '#CBD5E1', transition: 'width 1s ease-in-out' }}></div>
              <div style={{ width: `${(unfavorableModifiers.length/13)*100}%`, background: '#EF4444', transition: 'width 1s ease-in-out' }}></div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981' }}></div>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A' }}>{favorableModifiers.length} Favorable</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#CBD5E1' }}></div>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A' }}>{neutralModifiers.length} Neutral</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#EF4444' }}></div>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A' }}>{unfavorableModifiers.length} Unfavorable</span>
              </div>
            </div>
          </div>

          {/* Confidence Breakdown Bar */}
          <div style={{ background: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ color: '#64748B', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '800' }}>Fact Check Breakdown</div>
              <div style={{ fontSize: '0.75rem', fontWeight: '700', color: '#0F172A' }}>{claims.length} Claims</div>
            </div>
            
            <div style={{ display: 'flex', width: '100%', height: '10px', borderRadius: '5px', overflow: 'hidden', marginBottom: '20px', background: '#F1F5F9' }}>
              <div style={{ width: `${(verifiedClaims/claims.length)*100}%`, background: '#10B981', transition: 'width 1s ease-in-out' }}></div>
              <div style={{ width: `${(partialClaims/claims.length)*100}%`, background: '#F59E0B', transition: 'width 1s ease-in-out' }}></div>
              <div style={{ width: `${(unsupportedClaims/claims.length)*100}%`, background: '#EF4444', transition: 'width 1s ease-in-out' }}></div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10B981' }}></div>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A' }}>{verifiedClaims} Verified</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#F59E0B' }}></div>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A' }}>{partialClaims} Partial</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#EF4444' }}></div>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: '#0F172A' }}>{unsupportedClaims} Unsupported</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Row: Drivers & Concerns */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          {/* Risk Drivers */}
          <div style={{ background: '#F8FAFC', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <TrendingDown size={18} color="#059669" />
              <h4 style={{ margin: 0, color: '#0F172A', fontSize: '0.85rem', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.05em' }}>Key Strengths</h4>
            </div>
            {riskDrivers.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {riskDrivers.map((m, i) => (
                  <span key={i} style={{ fontSize: '0.75rem', fontWeight: '700', color: '#059669', background: '#ECFDF5', padding: '6px 12px', borderRadius: '6px', border: '1px solid #A7F3D0', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
                    {m.name}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.85rem', color: '#94A3B8', fontWeight: '500' }}>No strong favorable factors identified.</div>
            )}
          </div>

          {/* Key Concerns */}
          <div style={{ background: '#F8FAFC', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <TrendingUp size={18} color="#DC2626" />
              <h4 style={{ margin: 0, color: '#0F172A', fontSize: '0.85rem', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.05em' }}>Key Concerns</h4>
            </div>
            {keyConcerns.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {keyConcerns.map((m, i) => (
                  <span key={i} style={{ fontSize: '0.75rem', fontWeight: '700', color: '#DC2626', background: '#FEF2F2', padding: '6px 12px', borderRadius: '6px', border: '1px solid #FECACA', boxShadow: '0 1px 2px rgba(0,0,0,0.02)' }}>
                    {m.name}
                  </span>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: '0.85rem', color: '#94A3B8', fontWeight: '500' }}>No major underwriting concerns flagged.</div>
            )}
          </div>
        </div>

        {/* Overall Decision Summary */}
        <div style={{ marginTop: '32px', padding: '24px', background: '#F8FAFC', borderRadius: '12px', border: '1px solid #E2E8F0' }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#0F172A', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Info size={18} color="var(--accent-orange)" /> Overall Decision Summary
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
            
            {/* Summary Text */}
            <div>
              <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: '1.6' }}>
                {data.overall_summary || `The company was assigned a ${data.riskCategory} risk tier based on the aggregation of all evaluated cyber risk factors.`}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748B', fontWeight: '800', marginBottom: '8px' }}>Highest Risk Modifiers</div>
                <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: '1.6' }}>
                  {keyConcerns.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: '20px' }}>
                      {keyConcerns.map((m, i) => <li key={i}>{m.name}</li>)}
                    </ul>
                  ) : 'None identified'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748B', fontWeight: '800', marginBottom: '8px' }}>Lowest Risk Modifiers</div>
                <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: '1.6' }}>
                  {riskDrivers.length > 0 ? (
                    <ul style={{ margin: 0, paddingLeft: '20px' }}>
                      {riskDrivers.map((m, i) => <li key={i}>{m.name}</li>)}
                    </ul>
                  ) : 'None identified'}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748B', fontWeight: '800', marginBottom: '8px' }}>Evidence Used</div>
                <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: '1.6' }}>
                  {data.evidence_used ? (
                    <ul style={{ margin: 0, paddingLeft: '20px' }}>
                      {data.evidence_used.map((e, i) => <li key={i}>{e}</li>)}
                    </ul>
                  ) : (
                    `${verifiedClaims} fully verified claims across ${modifiers.length} modifiers, corroborated by the consensus engine using primary open source intelligence.`
                  )}
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#64748B', fontWeight: '800', marginBottom: '8px' }}>Overall Confidence</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ 
                    fontSize: '0.85rem', 
                    color: scoreNum >= 90 ? '#059669' : scoreNum >= 70 ? '#D97706' : '#DC2626', 
                    fontWeight: '800', 
                    background: scoreNum >= 90 ? '#ECFDF5' : scoreNum >= 70 ? '#FEF3C7' : '#FEF2F2',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    border: `1px solid ${scoreNum >= 90 ? '#A7F3D0' : scoreNum >= 70 ? '#FDE68A' : '#FECACA'}`
                  }}>
                    {scoreNum}%
                  </span>
                  <span style={{ fontSize: '0.8rem', color: '#475569', fontWeight: '500' }}>Aggregated across all modifiers</span>
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* Final Verdict Explanation Collapsible Section */}
        <div style={{ marginTop: '32px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
          <button 
            onClick={() => setIsExplanationExpanded(!isExplanationExpanded)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '600',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              padding: '8px 0',
              width: '100%',
              transition: 'color 0.2s'
            }}
            onMouseOver={(e) => e.target.style.color = 'var(--text-primary)'}
            onMouseOut={(e) => e.target.style.color = 'var(--text-secondary)'}
          >
            {isExplanationExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            Executive Summary Help
          </button>
          
          {isExplanationExpanded && (
            <div style={{ 
              marginTop: '16px', 
              background: '#F8FAFC', 
              padding: '20px', 
              borderRadius: '8px', 
              border: '1px solid #E5E7EB',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              lineHeight: '1.6'
            }}>
              <div><strong style={{ color: 'var(--text-primary)' }}>Risk Category:</strong> The overall cyber risk tier derived from averaging the 13 actuarial modifier ratings.</div>
              <div><strong style={{ color: 'var(--text-primary)' }}>Evidence Confidence Score:</strong> A measure of data integrity based on the Fact Checker's corroboration of claims against raw scraped evidence.</div>
              <div><strong style={{ color: 'var(--text-primary)' }}>Human Escalation:</strong> Activated when confidence falls below acceptable thresholds, or when strict discrepancies (e.g., entity mismatch) are detected.</div>
              <div style={{ marginTop: '8px', borderTop: '1px dashed rgba(255,255,255,0.2)', paddingTop: '12px' }}>
                <em style={{ color: 'var(--accent-orange)' }}>Key Distinction:</em> The <strong>Risk Tier</strong> represents the underlying danger/appetite of the company itself. The <strong>Confidence Score</strong> represents how much we trust the data we collected to make that decision.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
