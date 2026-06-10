import { Shield, Activity, WifiOff, RefreshCw, Cpu, Database, CheckSquare, Users } from 'lucide-react';

export default function Header({ isLoading, apiFailed }) {
  const getStatusBadge = () => {
    if (isLoading) return <div className="badge cyan" style={{ padding: '6px 12px' }}><RefreshCw size={14} className="pulse-glow" style={{ animation: 'spin 2s linear infinite' }} /> Running Analysis</div>;
    if (apiFailed) return <div className="badge warning" style={{ padding: '6px 12px' }}><WifiOff size={14} /> Mock Mode</div>;
    return <div className="badge success" style={{ padding: '6px 12px' }}><Activity size={14} /> System Connected</div>;
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
          
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
            <span className="badge neutral" style={{ background: 'transparent' }}><Cpu size={12} style={{ marginRight: '4px' }}/> Multi-Agent</span>
            <span className="badge neutral" style={{ background: 'transparent' }}><Database size={12} style={{ marginRight: '4px' }}/> Evidence-Driven</span>
            <span className="badge neutral" style={{ background: 'transparent' }}><CheckSquare size={12} style={{ marginRight: '4px' }}/> Modifier-Based</span>
            <span className="badge neutral" style={{ background: 'transparent' }}><Users size={12} style={{ marginRight: '4px' }}/> Human-in-the-Loop</span>
          </div>
        </div>
      </div>
      
      <div>
        {getStatusBadge()}
      </div>
    </div>
  );
}
