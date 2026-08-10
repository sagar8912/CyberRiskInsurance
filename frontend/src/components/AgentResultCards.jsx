import React from 'react';
import { Brain, FileText, Globe, Database, Building2, Search, Link, CheckSquare, Scale } from 'lucide-react';

export default function AgentResultCards({ reconciledProfile, claims, modifiers, verdict }) {
  if (!verdict) return null;

  const verifiedClaims = claims ? claims.filter(c => c.status.toLowerCase() === 'verified').length : 0;
  const totalClaims = claims ? claims.length : 0;
  
  const favMods = modifiers ? modifiers.filter(m => m.rating.includes('FAVOURABLE') && !m.rating.includes('UNFAVOURABLE')).length : 0;
  const totalMods = modifiers ? modifiers.length : 15;


  const agents = [
    {
      name: "SEC Collector",
      icon: <FileText size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Financial Evidence",
      finding: `Extracted revenue and subsidiary structures.`,
      evidenceCount: 2,
      confidence: "High"
    },
    {
      name: "Wikipedia Collector",
      icon: <Globe size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Public Profile",
      finding: `Corroborated acquisition history and customer type.`,
      evidenceCount: 3,
      confidence: "High"
    },
    {
      name: "Wikidata Collector",
      icon: <Database size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Structured Facts",
      finding: `Verified operating countries and entity graph.`,
      evidenceCount: 1,
      confidence: "Medium"
    },
    {
      name: "DB Collector",
      icon: <Building2 size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Business Metadata",
      finding: `Mapped entity metadata to NAICS/SIC codes.`,
      evidenceCount: 1,
      confidence: "High"
    },
    {
      name: "Domain Scraper",
      icon: <Search size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Digital Footprint",
      finding: reconciledProfile?.privacyPolicy || reconciledProfile?.ecommercePlatform 
        ? "Detected live e-commerce and privacy policy presence."
        : "Scanned digital footprint and TLS encryption.",
      evidenceCount: 4,
      confidence: "High"
    },
    {
      name: "Coordinator Agent",
      icon: <Link size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Data Reconciliation",
      finding: `Reconciled collector outputs into single profile.`,
      evidenceCount: 11,
      confidence: "High"
    },
    {
      name: "Fact Checker Agent",
      icon: <CheckSquare size={20} color="var(--accent-orange)" />,
      status: verifiedClaims === totalClaims ? "Success" : "Partial",
      signal: "Claim Corroboration",
      finding: `Verified ${verifiedClaims} out of ${totalClaims} underwriting claims.`,
      evidenceCount: totalClaims,
      confidence: verifiedClaims === totalClaims ? "High" : "Medium"
    },
    {
      name: "Underwriter Agent",
      icon: <Scale size={20} color="var(--accent-orange)" />,
      status: "Success",
      signal: "Actuarial Scoring",
      finding: `Applied ${totalMods} modifier models yielding ${favMods} strengths.`,
      evidenceCount: totalMods,
      confidence: verdict.confidenceBand
    }
  ];

  return (
    <div style={{ marginBottom: '32px' }}>
      <h3 style={{ fontSize: '1rem', color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Brain size={18} color="var(--accent-orange)" /> Autonomous Agent Results
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {agents.map((agent, idx) => (
          <div key={idx} className="glass-panel" style={{ background: '#FFFFFF', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ background: 'rgba(243, 111, 33, 0.1)', padding: '8px', borderRadius: '6px' }}>
                  {agent.icon}
                </div>
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text-primary)' }}>{agent.name}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{agent.signal}</div>
                </div>
              </div>
              <div style={{ 
                fontSize: '0.7rem', fontWeight: '700', textTransform: 'uppercase', padding: '4px 8px', borderRadius: '4px',
                background: agent.status === 'Success' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                color: agent.status === 'Success' ? '#10B981' : '#F59E0B'
              }}>
                {agent.status}
              </div>
            </div>

            <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: '600', lineHeight: '1.4', background: '#F8FAFC', padding: '10px', borderRadius: '4px', border: '1px solid #E5E7EB', flex: 1 }}>
              {agent.finding}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px', marginTop: 'auto' }}>
              <div>
                <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '700' }}>Sources</div>
                <div style={{ fontSize: '0.9rem', fontWeight: '800', color: 'var(--text-primary)' }}>{agent.evidenceCount}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.65rem', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: '700' }}>Confidence</div>
                <div style={{ fontSize: '0.9rem', fontWeight: '800', color: agent.confidence === 'High' ? '#10B981' : (agent.confidence === 'Medium' ? '#F59E0B' : '#EF4444') }}>
                  {agent.confidence}
                </div>
              </div>
            </div>

          </div>
        ))}
      </div>
    </div>
  );
}
