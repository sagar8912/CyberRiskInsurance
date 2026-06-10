import React, { useState } from 'react';
import { Calculator, Eye } from 'lucide-react';
import ModifierDetailsModal from './ModifierDetailsModal';

export default function ModifierTable({ data }) {
  const [selectedModifier, setSelectedModifier] = useState(null);

  if (!data) return null;
  
  const getRatingBadge = (rating) => {
    const r = rating.toUpperCase();
    let badgeClass = "neutral";
    
    if (r.includes('VERY FAVOURABLE')) {
      badgeClass = "success";
    } else if (r.includes('PARTIALLY FAVOURABLE')) {
      badgeClass = "cyan"; // Lighter blue/cyan for partial
    } else if (r.includes('FAVOURABLE')) {
      badgeClass = "teal";
    } else if (r.includes('PARTIALLY UNFAVOURABLE')) {
      badgeClass = "warning";
    } else if (r.includes('UNFAVOURABLE')) {
      badgeClass = "danger";
    }

    return <span className={`badge ${badgeClass}`}>{rating.toUpperCase()}</span>;
  };

  return (
    <>
      <div className="glass-panel" style={{ overflowX: 'auto', padding: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '24px 24px 16px 24px', position: 'sticky', top: 0, background: 'rgba(16, 23, 42, 0.95)', backdropFilter: 'blur(8px)', zIndex: 11, borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <h2 style={{ margin: 0 }}><Calculator size={20} color="var(--accent-cyan)" /> Underwriter Modifiers</h2>
        </div>
        <div style={{ width: '100%' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Modifier Name</th>
                <th>Raw Score</th>
                <th>Category Rating</th>
                <th>Rationale</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((mod) => (
                <tr key={mod.id}>
                  <td className="text-muted">{mod.id}</td>
                  <td style={{ fontWeight: '500', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>{mod.name}</td>
                  <td style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>{mod.score}</td>
                  <td>{getRatingBadge(mod.rating)}</td>
                  <td className="text-muted" style={{ fontSize: '0.85rem', lineHeight: '1.4', minWidth: '300px' }}>{mod.rationale}</td>
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
