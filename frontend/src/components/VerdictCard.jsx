import React, { useState } from 'react';
import { Gavel, AlertTriangle, ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';

export default function VerdictCard({ data }) {
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

  return (
    <div className="glass-panel" style={{ 
      background: 'linear-gradient(145deg, rgba(16, 23, 42, 0.9) 0%, rgba(9, 12, 21, 0.95) 100%)',
      border: `1px solid ${mainColor}`,
      boxShadow: `0 0 30px ${isFavorable ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)'}`,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background glowing orb */}
      <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '150px', height: '150px', background: mainColor, filter: 'blur(80px)', opacity: 0.2, zIndex: 0 }}></div>

      <div style={{ position: 'relative', zIndex: 1 }}>
        <h2 style={{ color: mainColor }}><Gavel size={24} /> Final Underwriting Verdict</h2>
        
        <div style={{ display: 'flex', gap: '40px', marginTop: '32px' }}>
          <div style={{ flex: 1 }}>
            <div className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Risk Category</div>
            <div style={{ fontSize: '2.5rem', fontWeight: '700', color: isZeroConfidence ? 'var(--accent-warning)' : mainColor, lineHeight: 1 }}>
              {isZeroConfidence ? "Needs Review" : data.riskCategory}
            </div>
            {isZeroConfidence && (
              <div style={{ color: 'var(--accent-warning)', fontSize: '0.85rem', marginTop: '12px', background: 'rgba(245, 158, 11, 0.1)', padding: '8px', borderRadius: '6px', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
                <AlertTriangle size={14} style={{ verticalAlign: 'text-bottom', marginRight: '4px' }} />
                Risk category is provisional due to low evidence confidence. (Backend: {data.riskCategory})
              </div>
            )}
            
            <div style={{ marginTop: '24px' }}>
               <div className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', cursor: 'help' }} title="Entity Status checks company/domain alignment.">
                 Entity Status ℹ️
               </div>
               {isZeroConfidence ? (
                 <>
                   <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Backend Entity Status: Match</div>
                   <div style={{ color: 'var(--accent-warning)', fontWeight: '600', marginTop: '4px' }}>UI Review Status: Needs Review</div>
                   <div style={{ color: 'var(--accent-warning)', fontSize: '0.8rem', marginTop: '6px', lineHeight: '1.4' }}>
                     Domain may not strongly match the company. Entity/domain match could not be strongly verified from evidence sources.
                   </div>
                 </>
               ) : (
                 <div style={{ color: 'var(--text-primary)', fontWeight: '600' }}>Match Confirmed</div>
               )}
            </div>
          </div>
          
          <div style={{ flex: 1.5, display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
              <div style={{ position: 'relative', width: '80px', height: '80px' }}>
                <svg width="80" height="80" viewBox="0 0 100 100" style={{ transform: 'rotate(-90deg)' }}>
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
                  <circle cx="50" cy="50" r="40" fill="transparent" stroke="url(#gaugeGradient)" strokeWidth="8" strokeDasharray="251.2" strokeDashoffset={251.2 - (251.2 * scoreNum / 100)} strokeLinecap="round" style={{ transition: 'stroke-dashoffset 1s ease-in-out' }} />
                  <defs>
                    <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="var(--accent-blue)" />
                      <stop offset="100%" stopColor={mainColor} />
                    </linearGradient>
                  </defs>
                </svg>
                <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '700', fontSize: '1.1rem' }}>
                  {data.underwritingScore}
                </div>
              </div>
              <div style={{ flex: 1 }}>
                <div className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', cursor: 'help' }} title="Evidence Confidence Score checks source corroboration. Low confidence requires human review.">
                  Evidence Confidence Score ℹ️
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Based on multi-agent corroboration and fact-checking reliability.</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '24px' }}>
              <div style={{ flex: 1 }}>
                <div className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Confidence Band</div>
                <div className={`badge ${data.confidenceBand === 'Low' ? 'warning' : 'success'}`} style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
                  {data.confidenceBand}
                </div>
              </div>

              {data.humanEscalation && (
                <div style={{ flex: 1 }}>
                  <div className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Escalation Required</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-warning)', fontWeight: '600', background: 'rgba(245, 158, 11, 0.1)', padding: '6px 12px', borderRadius: '999px', display: 'inline-flex' }}>
                    <AlertTriangle size={16} /> True
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Final Verdict Explanation Collapsible Section */}
        <div style={{ marginTop: '24px', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '16px' }}>
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
              padding: 0,
              width: '100%'
            }}
          >
            {isExplanationExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            Final Verdict Explanation
          </button>
          
          {isExplanationExpanded && (
            <div style={{ 
              marginTop: '16px', 
              background: 'rgba(0,0,0,0.2)', 
              padding: '16px', 
              borderRadius: '8px', 
              border: '1px solid rgba(255,255,255,0.05)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              lineHeight: '1.5'
            }}>
              <div><strong style={{ color: 'var(--text-primary)' }}>Risk Category:</strong> Overall cyber risk tier based on 13 modifier ratings.</div>
              <div><strong style={{ color: 'var(--text-primary)' }}>Evidence Confidence Score:</strong> Source reliability / corroboration score from fact checker.</div>
              <div><strong style={{ color: 'var(--text-primary)' }}>Human Escalation:</strong> True when evidence confidence is low or mismatch/discrepancy exists.</div>
              <div style={{ marginTop: '4px', borderTop: '1px dashed rgba(255,255,255,0.1)', paddingTop: '8px' }}>
                <em style={{ color: 'var(--accent-cyan)' }}>Difference:</em> The <strong>Risk Category</strong> represents the underwriting danger/appetite of the company itself, while the <strong>Evidence Confidence Score</strong> represents how much we trust the data we collected to make that decision.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
