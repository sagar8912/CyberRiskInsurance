import React from 'react';
import { Network, Search, AlertTriangle, ShieldAlert } from 'lucide-react';

export default function ApiComparisonPanel({ comparisonData }) {
  // If no backend data yet, use empty state with expected structure
  const data = comparisonData || [];
  
  return (
    <div className="glass-panel" style={{ marginTop: '32px', background: '#FFFFFF', padding: '24px', borderRadius: '12px', border: '1px solid #E2E8F0', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', borderBottom: '1px solid #E2E8F0', paddingBottom: '16px' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', color: '#0F172A' }}>
          <Network size={20} color="var(--accent-orange)" /> API Integration Comparison
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
           <span style={{ fontSize: '0.75rem', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '4px' }}>
             <ShieldAlert size={14} color="var(--accent-orange)" /> Admin Only
           </span>
        </div>
      </div>
      
      {data.length === 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', background: '#F8FAFC', borderRadius: '8px', border: '1px dashed #CBD5E1' }}>
          <Search size={32} color="#94A3B8" style={{ marginBottom: '16px' }} />
          <div style={{ color: '#475569', fontWeight: '600', marginBottom: '8px' }}>No Comparison Data Available</div>
          <div style={{ color: '#94A3B8', fontSize: '0.85rem', textAlign: 'center', maxWidth: '400px' }}>
            The backend has not returned API comparison metrics for this run. Waiting for integration with Chayan's new APIs.
          </div>
        </div>
      ) : (
        <div style={{ width: '100%', overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '6px' }}>
          <table style={{ width: '100%', minWidth: '800px', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead style={{ background: '#F8FAFC' }}>
              <tr>
                <th style={{ padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '800', textTransform: 'uppercase', fontSize: '0.75rem' }}>Collector</th>
                <th style={{ padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '800', textTransform: 'uppercase', fontSize: '0.75rem' }}>Existing API</th>
                <th style={{ padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '800', textTransform: 'uppercase', fontSize: '0.75rem' }}>New API</th>
                <th style={{ padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '800', textTransform: 'uppercase', fontSize: '0.75rem' }}>Status</th>
                <th style={{ padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '800', textTransform: 'uppercase', fontSize: '0.75rem' }}>Coverage</th>
                <th style={{ padding: '12px 16px', borderBottom: '2px solid #E2E8F0', color: '#64748B', fontWeight: '800', textTransform: 'uppercase', fontSize: '0.75rem' }}>Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #F1F5F9', background: '#FFFFFF' }}>
                  <td style={{ padding: '12px 16px', fontWeight: '600', color: '#334155' }}>{row.collector}</td>
                  <td style={{ padding: '12px 16px', color: '#64748B' }}>{row.existingApi}</td>
                  <td style={{ padding: '12px 16px', color: '#64748B' }}>{row.newApi}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span style={{ 
                      background: row.status === 'Full' ? '#ECFDF5' : row.status === 'Partial' ? '#FEF3C7' : '#F1F5F9',
                      color: row.status === 'Full' ? '#059669' : row.status === 'Partial' ? '#D97706' : '#64748B',
                      padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '700'
                    }}>
                      {row.status}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#475569' }}>{row.coverage}</td>
                  <td style={{ padding: '12px 16px', color: '#475569' }}>{row.recommendation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
