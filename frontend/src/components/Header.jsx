import { Shield, Activity, WifiOff, RefreshCw, Cpu, Database, CheckSquare, Users } from 'lucide-react';

export default function Header({ isLoading, apiFailed, company, domain }) {
  const getStatusBadge = () => {
    if (isLoading) return <div className="badge cyan" style={{ padding: '6px 12px' }}><RefreshCw size={14} className="pulse-glow" style={{ animation: 'spin 2s linear infinite' }} /> RUNNING</div>;
    if (apiFailed) return <div className="badge warning" style={{ padding: '6px 12px' }}><WifiOff size={14} /> MOCK MODE / API DISCONNECTED</div>;
    return <div className="badge success" style={{ padding: '6px 12px' }}><Activity size={14} /> SYSTEM CONNECTED</div>;
  };

  return (
    <div className="glass-panel flex-between" style={{ padding: '20px 32px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div className="pulse-glow" style={{ background: 'rgba(34, 211, 238, 0.1)', padding: '14px', borderRadius: '16px', border: '1px solid rgba(34, 211, 238, 0.3)' }}>
          <Shield color="var(--accent-cyan)" size={32} />
        </div>
        <div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: '2px' }}>Cyber Risk Auto-Underwriter</h1>
          <p className="text-muted" style={{ fontSize: '0.95rem' }}>Explainable multi-agent underwriting intelligence</p>
          
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px', flexWrap: 'wrap' }}>
            <span className="badge neutral" style={{ background: 'transparent' }}><Cpu size={12} style={{ marginRight: '4px' }}/> Multi-Agent</span>
            <span className="badge neutral" style={{ background: 'transparent' }}><Database size={12} style={{ marginRight: '4px' }}/> Evidence-Driven</span>
            <span className="badge neutral" style={{ background: 'transparent' }}><CheckSquare size={12} style={{ marginRight: '4px' }}/> Modifier-Based</span>
            <span className="badge neutral" style={{ background: 'transparent' }}><Users size={12} style={{ marginRight: '4px' }}/> Human-in-the-Loop</span>
          </div>
          
          {company && domain && (
            <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Analyzing:</span>
              <span style={{ background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '4px', color: 'var(--accent-cyan)', fontWeight: '600' }}>{company}</span>
              <span style={{ color: 'var(--text-secondary)' }}>({domain})</span>
            </div>
          )}
        </div>
      </div>
      
      <div>
        {getStatusBadge()}
      </div>
    </div>
  );
}
