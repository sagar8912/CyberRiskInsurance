import { Gavel, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function VerdictCard({ data }) {
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
            <div style={{ fontSize: '2.5rem', fontWeight: '700', color: mainColor, lineHeight: 1 }}>
              {data.riskCategory}
            </div>
            
            <div style={{ marginTop: '24px' }}>
               <div className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px' }}>Entity Status</div>
               <div style={{ color: 'var(--text-primary)', fontWeight: '600' }}>Match Confirmed</div>
            </div>
          </div>
          
          <div style={{ flex: 1.5, display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <div className="flex-between" style={{ marginBottom: '8px' }}>
                <span className="text-muted" style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Evidence Confidence Score</span>
                <span style={{ fontWeight: '700', fontSize: '1.1rem' }}>{data.underwritingScore}</span>
              </div>
              <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${scoreNum}%`, background: `linear-gradient(90deg, var(--accent-blue), ${mainColor})`, borderRadius: '4px' }}></div>
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
      </div>
    </div>
  );
}
