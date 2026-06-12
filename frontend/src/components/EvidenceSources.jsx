import React from 'react';
import { Database, Search, Building2, BookOpen, Globe, CheckCircle2 } from 'lucide-react';

export default function EvidenceSources({ hasRun }) {
  const sources = [
    { id: 1, name: 'SEC Collector', type: 'Financial Database', icon: <Building2 size={20} color="var(--accent-blue)" />, contributed: 'Typically contributes: Revenue figures, SEC filings structure, Subsidiaries data.' },
    { id: 2, name: 'Wikipedia', type: 'Public Knowledge Graph', icon: <BookOpen size={20} color="var(--accent-blue)" />, contributed: 'Typically contributes: General company profile, History, Overview summaries.' },
    { id: 3, name: 'Wikidata', type: 'Structured Fact DB', icon: <Database size={20} color="var(--accent-blue)" />, contributed: 'Typically contributes: Acquisitions, Geographic spread, HQ location, SIC Codes.' },
    { id: 4, name: 'DB Collector', type: 'Business Intelligence', icon: <Search size={20} color="var(--accent-blue)" />, contributed: 'Typically contributes: Industry classification, B2B/B2C indicators, Employee count.' },
    { id: 5, name: 'Domain Scraper', type: 'Live Web Scraping', icon: <Globe size={20} color="var(--accent-blue)" />, contributed: 'Typically contributes: HTTPS encryption status, E-commerce signals, Privacy policies.' }
  ];

  if (!hasRun) return null;

  return (
    <div className="glass-panel">
      <h2 style={{ marginBottom: '20px' }}><Search size={20} color="var(--accent-cyan)" /> Evidence Sources Explainer</h2>
      <p className="text-muted" style={{ fontSize: '0.875rem', marginBottom: '20px' }}>Breakdown of the raw data contributed by each parallel collector agent before reconciliation.</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        {sources.map(source => (
          <div key={source.id} className="source-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ background: 'rgba(59, 130, 246, 0.1)', padding: '10px', borderRadius: '8px' }}>
                {source.icon}
              </div>
              <span className="badge success"><CheckCircle2 size={12} style={{ marginRight: '4px' }}/> Extracted</span>
            </div>
            
            <div>
              <div style={{ fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>{source.name}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{source.type}</div>
            </div>
            
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.4', marginTop: 'auto', paddingTop: '12px', borderTop: '1px dashed rgba(255,255,255,0.1)' }}>
              <strong>{source.contributed}</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
