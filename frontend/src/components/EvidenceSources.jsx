import React, { useState } from 'react';

const normalizeUrl = (url) => {
  if (!url) return null;
  let cleanUrl = String(url).trim().toLowerCase();
  cleanUrl = cleanUrl.replace(/\s+/g, '');
  if (cleanUrl === 'notfound' || cleanUrl === 'n/a' || cleanUrl === 'none') return null;
  
  if (cleanUrl.endsWith('/')) cleanUrl = cleanUrl.slice(0, -1);
  if (cleanUrl.startsWith('http://')) cleanUrl = 'https://' + cleanUrl.slice(7);
  
  if (!cleanUrl.startsWith('https://')) {
    if (cleanUrl.includes('.')) {
      cleanUrl = 'https://' + cleanUrl;
    } else {
      return null;
    }
  }
  return cleanUrl;
};

const extractEvidenceLinks = (mod) => {
  const rawLinks = [];
  const co = mod.collector_outputs || {};
  const modNameLow = mod.name ? mod.name.toLowerCase() : '';

  const addLink = (title, collector, summary, url) => {
    rawLinks.push({ title, collector, evidence: summary, url, status: 'Verified' });
  };

  // 1. Modifier-specific mapping (Aggressively filtered)
  if (modNameLow.includes('acquisitions') || modNameLow.includes('mergers')) {
     if (co.Wikipedia?.findings?.acquisitions) addLink('Wikipedia Company Profile', 'Wikipedia', 'Acquisitions data extracted', co.Wikipedia.findings.url || mod.wikipedia_url);
     if (co.Wikidata?.findings?.acquisitions) addLink('Wikidata Company Data', 'Wikidata', 'Acquisitions verified', co.Wikidata.findings.official_website || mod.official_website);
     if (co.ResponsesAPI?.findings?.acquisitions) addLink('Acquisition Evidence', 'ResponsesAPI', 'Acquisitions verified via API', null);
     if (co.SECCollector?.findings?.acquisitions) addLink('SEC Filing', 'SECCollector', 'Acquisition mentions extracted from SEC filing', co.SECCollector.findings.filing_url || mod.filing_url);
  }
  
  if (modNameLow.includes('sensitive information') || modNameLow.includes('b2c')) {
     if (co.DomainScraper?.findings?.customer_type) addLink('Customer Segments', 'DomainScraper', `Customer type: ${co.DomainScraper.findings.customer_type}`, mod.official_website);
     if (co.DomainScraper?.findings?.has_ecommerce) addLink('Ecommerce Evidence', 'DomainScraper', 'Ecommerce functionality detected', mod.official_website);
     if (co.DomainScraper?.findings?.privacy_policy_url) addLink('Privacy Policy', 'DomainScraper', 'Privacy policy published', co.DomainScraper.findings.privacy_policy_url);
     if (mod.official_website) addLink('Official Website', 'System', 'Official domain verified', mod.official_website);
  }

  if (modNameLow.includes('domain encryption') || modNameLow.includes('internet footprint')) {
     if (co.DomainScraper?.findings?.domains) addLink('Domain Scan', 'DomainScraper', 'HTTPS checked domains / domains discovered', mod.official_website);
     if (mod.official_website) addLink('Official Website', 'System', 'Official domain verified', mod.official_website);
  }

  if (modNameLow.includes('geographic spread')) {
     if (co.Wikidata?.findings?.official_website) addLink('Wikidata Official Website', 'Wikidata', 'Verified domain mapping', co.Wikidata.findings.official_website);
     if (co.Wikipedia?.findings?.countries) addLink('Wikipedia Countries of Operation', 'Wikipedia', 'Countries of operation extracted', co.Wikipedia.findings.url || mod.wikipedia_url);
     if (co.DBCollector?.findings?.headquarters) addLink('DB Country Source', 'DBCollector', `Headquarters: ${co.DBCollector.findings.headquarters}`, null);
  }

  if (modNameLow.includes('nature of services')) {
     if (co.DomainScraper?.findings?.products) addLink('Products/Services', 'DomainScraper', 'Products and services extracted', mod.official_website);
     if (co.Wikidata?.findings?.industry) addLink('Wikidata Industry', 'Wikidata', `Industry: ${co.Wikidata.findings.industry}`, mod.official_website);
     if (co.Wikipedia?.findings?.industry) addLink('Wikipedia Industry Classification', 'Wikipedia', `Industry: ${co.Wikipedia.findings.industry}`, co.Wikipedia.findings.url || mod.wikipedia_url);
     if (mod.official_website) addLink('Official Website', 'System', 'Official domain verified', mod.official_website);
  }
  
  if (modNameLow.includes('complexity')) {
     if (co.SECCollector?.findings?.subsidiaries) addLink('SEC Subsidiaries', 'SECCollector', 'Subsidiaries extracted from SEC filing', co.SECCollector.findings.filing_url || mod.filing_url);
     if (co.Wikipedia?.findings?.subsidiaries) addLink('Wikipedia Subsidiaries', 'Wikipedia', 'Subsidiaries extracted', co.Wikipedia.findings.url || mod.wikipedia_url);
     if (co.Wikidata?.findings?.subsidiaries) addLink('Wikidata Subsidiaries', 'Wikidata', 'Subsidiaries verified', mod.official_website);
  }
  
  if (modNameLow.includes('privacy regulation')) {
     if (co.DomainScraper?.findings?.privacy_policy_url || mod.privacy_policy_url) addLink('Privacy Policy', 'DomainScraper', 'Privacy policy published', co.DomainScraper?.findings?.privacy_policy_url || mod.privacy_policy_url);
     if (co.DomainScraper?.findings?.terms_url || mod.terms_url) addLink('Terms Page', 'DomainScraper', 'Terms page found', co.DomainScraper?.findings?.terms_url || mod.terms_url);
     if (co.DomainScraper?.findings?.compliance) addLink('Compliance Mentions', 'DomainScraper', 'Compliance frameworks verified', mod.official_website);
  }
  
  if (modNameLow.includes('seasonality')) {
     if (co.SECCollector?.findings?.quarterly_revenue) addLink('SEC Filing', 'SECCollector', 'Quarterly revenue extracted', co.SECCollector.findings.filing_url || mod.filing_url);
  }

  if (modNameLow.includes('volatility')) {
     if (co.DomainScraper?.findings?.cloud_indicators) addLink('Cloud/SaaS Indicators', 'DomainScraper', 'Digital exposure signals extracted', mod.official_website);
     if (mod.official_website) addLink('Official Website', 'System', 'Official domain verified', mod.official_website);
  }

  if (modNameLow.includes('years in business')) {
     if (co.DBCollector?.findings?.founding_year) addLink('DB Founding Year', 'DBCollector', `Founding year: ${co.DBCollector.findings.founding_year}`, null);
     if (co.Wikipedia?.findings?.founding_year) addLink('Wikipedia Company Profile', 'Wikipedia', `Founding year: ${co.Wikipedia.findings.founding_year}`, co.Wikipedia.findings.url || mod.wikipedia_url);
     if (co.Wikidata?.findings?.founding_year) addLink('Wikidata Company Data', 'Wikidata', `Founding year: ${co.Wikidata.findings.founding_year}`, mod.official_website);
  }

  // 2. Deduplication and Normalization
  console.log(`Evidence before dedupe for ${mod.name}:`, rawLinks.length);
  
  const uniqueSources = [];
  const seenMap = new Set();
  
  rawLinks.forEach(link => {
    let nUrl = normalizeUrl(link.url);
    let originalUrl = nUrl ? link.url.trim() : null; // keep original case for display if needed, but nUrl is for deduping
    if (originalUrl && !originalUrl.startsWith('http')) originalUrl = nUrl;
    
    const key = nUrl || `${link.title}-${link.collector}-${link.evidence}`.toLowerCase().trim();
    
    if (!seenMap.has(key)) {
      seenMap.add(key);
      uniqueSources.push({
        title: link.title,
        collector: link.collector,
        evidence: typeof link.evidence === 'string' ? link.evidence : JSON.stringify(link.evidence)?.slice(0, 100),
        url: originalUrl,
        status: link.status
      });
    }
  });

  console.log(`Evidence after dedupe for ${mod.name}:`, uniqueSources.length);
  return uniqueSources;
};

export default function EvidenceSources({ mod }) {
  const [expanded, setExpanded] = useState(false);
  if (!mod) return null;

  const uniqueSources = extractEvidenceLinks(mod);

  if (uniqueSources.length === 0 && !mod.evidence_summary) {
    return <div style={{ color: '#94A3B8', fontSize: '0.85rem', fontStyle: 'italic' }}>No clickable source URL returned by backend for this modifier.</div>;
  }

  const hasClickableLink = uniqueSources.some(s => s.url);
  
  // Group by collector
  const grouped = {};
  uniqueSources.forEach(src => {
    const col = src.collector || 'System';
    if (!grouped[col]) grouped[col] = [];
    grouped[col].push(src);
  });
  
  const collectors = Object.keys(grouped).sort();
  
  // Flatten for display limits but keeping group structure
  const maxVisible = 5;
  const isExpandable = uniqueSources.length > maxVisible;
  
  let visibleCount = 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {!hasClickableLink && uniqueSources.length === 0 && (
        <div style={{ color: '#94A3B8', fontSize: '0.85rem', fontStyle: 'italic' }}>
          No clickable source URL returned by backend for this modifier.
        </div>
      )}

      {uniqueSources.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {collectors.map(col => {
            const items = grouped[col];
            const visibleItems = expanded ? items : items.filter(() => {
               if (visibleCount < maxVisible) {
                 visibleCount++;
                 return true;
               }
               return false;
            });
            
            if (visibleItems.length === 0) return null;

            return (
              <div key={col} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: '800', color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid #E2E8F0', paddingBottom: '4px' }}>
                  {col}
                </div>
                {visibleItems.map((src, i) => (
                  <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingBottom: i === visibleItems.length - 1 ? '0' : '8px' }}>
                    <div style={{ color: '#0F172A', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ color: '#059669' }}>✓</span> {src.title}
                    </div>
                    <div style={{ color: '#475569', fontSize: '0.85rem' }}>
                      Evidence: {src.evidence}
                    </div>
                    {src.url && (
                      <div style={{ marginTop: '4px' }}>
                        <a href={src.url} target="_blank" rel="noopener noreferrer" style={{
                          display: 'inline-block', background: '#EFF6FF', color: '#3B82F6', textDecoration: 'none',
                          padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600',
                          border: '1px solid #BFDBFE'
                        }}>
                          Open {src.title}
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            );
          })}
          
          {isExpandable && (
            <button 
              onClick={() => setExpanded(!expanded)}
              style={{
                background: 'none', border: 'none', padding: '0', cursor: 'pointer',
                color: '#3B82F6', fontSize: '0.85rem', fontWeight: '600', textAlign: 'left',
                marginTop: '4px'
              }}
            >
              {expanded ? 'Hide sources' : `View more sources (${uniqueSources.length - maxVisible} hidden)`}
            </button>
          )}
        </div>
      )}

      {uniqueSources.length === 0 && mod.evidence_summary && (
        <ul style={{ margin: 0, paddingLeft: '20px' }}>
          {Array.isArray(mod.evidence_summary) 
            ? mod.evidence_summary.map((f, i) => <li key={i}>{f}</li>)
            : <li>{mod.evidence_summary}</li>}
        </ul>
      )}
    </div>
  );
}

// Export the utility so the report generator can use it
export { extractEvidenceLinks };
