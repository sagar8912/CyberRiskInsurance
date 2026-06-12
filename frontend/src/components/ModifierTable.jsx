import React, { useState } from 'react';
import { Calculator, Eye } from 'lucide-react';
import ModifierDetailsModal from './ModifierDetailsModal';

export default function ModifierTable({ data }) {
  const [selectedModifier, setSelectedModifier] = useState(null);
  const [showInternalLogic, setShowInternalLogic] = useState(false);

  if (!data) return null;
  
  const getRatingBadge = (rating) => {
    const r = rating.toUpperCase();
    let badgeClass = "neutral";
    
    // Use strict includes/equals ordering to prevent partial matching bugs
    if (r === 'VERY FAVOURABLE' || r.includes('VERY FAVOURABLE')) {
      badgeClass = "emerald";
    } else if (r === 'PARTIALLY FAVOURABLE' || (r.includes('PARTIALLY FAVOURABLE') && !r.includes('UNFAVOURABLE'))) {
      badgeClass = "cyan"; // Lighter blue/cyan for partial
    } else if (r === 'FAVOURABLE' || (r.includes('FAVOURABLE') && !r.includes('PARTIALLY') && !r.includes('UNFAVOURABLE'))) {
      badgeClass = "teal";
    } else if (r === 'AVERAGE' || r.includes('AVERAGE')) {
      badgeClass = "slate";
    } else if (r === 'PARTIALLY UNFAVOURABLE' || r.includes('PARTIALLY UNFAVOURABLE')) {
      badgeClass = "warning";
    } else if (r === 'UNFAVOURABLE' || r.includes('UNFAVOURABLE')) {
      badgeClass = "danger";
    }

    return <span className={`badge ${badgeClass}`}>{rating.toUpperCase()}</span>;
  };

  return (
    <>
      <div className="glass-panel" style={{ padding: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '24px 24px 16px 24px', position: 'sticky', top: 0, background: 'rgba(16, 23, 42, 0.95)', backdropFilter: 'blur(8px)', zIndex: 11, borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}><Calculator size={20} color="var(--accent-cyan)" /> Underwriter Modifiers</h2>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
            <span style={{ fontSize: '0.85rem', color: showInternalLogic ? 'var(--text-primary)' : 'var(--text-secondary)' }}>Show Internal Logic Details</span>
            <div style={{ 
              width: '40px', height: '22px', 
              background: showInternalLogic ? 'var(--accent-cyan)' : 'rgba(255,255,255,0.1)', 
              borderRadius: '12px', position: 'relative', transition: '0.3s' 
            }}>
              <div style={{ 
                width: '18px', height: '18px', 
                background: '#fff', borderRadius: '50%', 
                position: 'absolute', top: '2px', 
                left: showInternalLogic ? '20px' : '2px', 
                transition: '0.3s' 
              }}></div>
            </div>
            <input 
              type="checkbox" 
              style={{ display: 'none' }} 
              checked={showInternalLogic} 
              onChange={(e) => setShowInternalLogic(e.target.checked)} 
            />
          </label>
        </div>
        <div style={{ width: '100%', overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Modifier Name</th>
                {showInternalLogic && <th>Raw Score</th>}
                <th>Category Rating</th>
                <th>Rationale</th>
                {showInternalLogic && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {data.map((mod) => (
                <tr key={mod.id}>
                  <td className="text-muted">{mod.id}</td>
                  <td style={{ fontWeight: '500', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{mod.name}</td>
                  {showInternalLogic && <td style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{mod.score}</td>}
                  <td>{getRatingBadge(mod.rating)}</td>
                  <td className="text-muted" style={{ fontSize: '0.85rem', lineHeight: '1.5', minWidth: '350px', whiteSpace: 'normal', wordBreak: 'break-word' }}>{mod.rationale}</td>
                  {showInternalLogic && (
                    <td>
                      <button 
                        onClick={() => setSelectedModifier(mod)}
                        style={{
                          background: 'rgba(34, 211, 238, 0.1)',
                          border: '1px solid rgba(34, 211, 238, 0.2)',
                          color: 'var(--accent-cyan)',
                          padding: '6px 12px',
                          borderRadius: '6px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '0.75rem',
                          fontWeight: '600',
                          textTransform: 'uppercase',
                          transition: 'all 0.2s'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.background = 'rgba(34, 211, 238, 0.2)'}
                        onMouseOut={(e) => e.currentTarget.style.background = 'rgba(34, 211, 238, 0.1)'}
                      >
                        <Eye size={14} /> Logic
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <ModifierDetailsModal 
        isOpen={!!selectedModifier} 
        onClose={() => setSelectedModifier(null)} 
        modifier={selectedModifier} 
      />
    </>
  );
}
