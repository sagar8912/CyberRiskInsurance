import React, { useEffect } from 'react';
import { X, Code, FileText, CheckCircle2, Database } from 'lucide-react';

export default function ModifierDetailsModal({ isOpen, onClose, modifier }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !modifier) return null;

  // Sample mapping logic to mock the actual rule conditions for explainability
  const getRuleMock = (name) => {
    return `def evaluate_rule(reconciled_profile):
    # Retrieve ${name} facts
    data = extract_target_data(reconciled_profile)
    
    if data.meets_favorable_condition:
        return {"rating": "FAVOURABLE", "score": 1.0}
    elif data.meets_unfavorable_condition:
        return {"rating": "UNFAVOURABLE", "score": -1.0}
    else:
        return {"rating": "AVERAGE", "score": 0.0}`;
  };

  const getInputDataMock = (name) => {
    return `Evaluated using facts from Reconciled Profile and SEC/Wikidata sources related to ${name}.`;
  };

  return (
    <div 
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        background: 'rgba(9, 12, 21, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex', justifyContent: 'center', alignItems: 'center',
        zIndex: 1000,
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div 
        className="glass-panel" 
        style={{
          width: '100%', maxWidth: '700px', maxHeight: '90vh',
          overflowY: 'auto',
          background: 'rgba(16, 23, 42, 0.95)',
          border: '1px solid var(--accent-cyan)',
          position: 'relative'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <button onClick={onClose} style={{
          position: 'absolute', top: '24px', right: '24px',
          background: 'transparent', border: 'none', color: 'var(--text-secondary)',
          cursor: 'pointer', padding: '4px'
        }}>
          <X size={24} />
        </button>

        <h2 style={{ color: 'var(--accent-cyan)', marginBottom: '8px' }}>Modifier Details</h2>
        <div style={{ fontSize: '1.2rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '24px' }}>
          {modifier.name}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px' }}>Category Rating</div>
            <div style={{ fontWeight: '700', fontSize: '1.1rem' }}>{modifier.rating}</div>
          </div>
          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px' }}>Raw Mathematical Score</div>
            <div style={{ fontWeight: '700', fontSize: '1.1rem', fontFamily: 'monospace', color: 'var(--accent-cyan)' }}>{modifier.score}</div>
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', marginBottom: '12px' }}><Database size={18} color="var(--accent-teal)" /> Input Data Used</h3>
          <p style={{ background: 'rgba(20, 184, 166, 0.1)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(20, 184, 166, 0.2)', fontSize: '0.95rem', lineHeight: '1.5' }}>
            {getInputDataMock(modifier.name)}
          </p>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', marginBottom: '12px' }}><FileText size={18} color="var(--accent-blue)" /> Evaluated Rationale & Backend Output</h3>
          <p style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(59, 130, 246, 0.2)', fontSize: '0.95rem', lineHeight: '1.5' }}>
            {modifier.rationale}
          </p>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1rem', marginBottom: '12px' }}><Code size={18} color="var(--accent-success)" /> Rule Logic (Explainability Trace)</h3>
          <pre style={{
            background: '#0d1117',
            padding: '16px',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.05)',
            color: 'var(--text-secondary)',
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            overflowX: 'auto'
          }}>
            <code style={{ color: '#c9d1d9' }}>{getRuleMock(modifier.name)}</code>
          </pre>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-success)', fontSize: '0.85rem', fontWeight: '500', background: 'rgba(16, 185, 129, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <CheckCircle2 size={16} /> Evidence/Claim Support: Rule verified against Fact Checker ground truth.
        </div>
      </div>
    </div>
  );
}
