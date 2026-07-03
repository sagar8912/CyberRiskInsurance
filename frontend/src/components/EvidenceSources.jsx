import React, { useState } from 'react';

const RELIABILITY_MAP = {
  'SECCollector': '★★★★★',
  'DBCollector': '★★★★★',
  'System': '★★★★★',
  'Wikidata': '★★★★☆',
  'DomainScraper': '★★★☆☆',
  'ResponsesAPI': '★★★☆☆',
  'Wikipedia': '★★★☆☆'
};

const PRIORITY_MAP = {
  'SECCollector': 1,
  'DBCollector': 2,
  'System': 3,
  'Wikidata': 4,
  'DomainScraper': 5,
  'ResponsesAPI': 6,
  'Wikipedia': 7
};

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

  const formatEv = (obj, key) => {
    if (!obj || obj[key] === undefined || obj[key] === null || obj[key] === '') return null;
    const val = obj[key];
    
    if (Array.isArray(val)) {
      const cleanVal = val.filter(v => v !== null && v !== undefined && v !== '');
      if (cleanVal.length === 0) return null;
      if (typeof cleanVal[0] === 'object' && cleanVal[0] !== null) {
        if (key === 'acquisitions') return cleanVal.map(a => `${a.name || a.title || 'Unknown'} (Acquired ${a.recency_years ? new Date().getFullYear() - Math.floor(a.recency_years) : 'Unknown'})`).join('\n');
        if (key === 'domains') return cleanVal.map(d => `${d.url || d} (HTTPS: ${d.https_encrypted ? 'Yes' : 'No'})`).join('\n');
        if (key === 'subsidiaries' || key === 'subsidiaries_list') return cleanVal.map(s => s.name || s.title || s).join('\n');
        return cleanVal.map(x => JSON.stringify(x)).join('\n');
      }
      return cleanVal.join('\n');
    }
    
    if (typeof val === 'object' && val !== null) {
      if (Object.keys(val).length === 0) return null;
      return Object.entries(val).map(([k,v]) => `${k}: ${v}`).join('\n');
    }
    
    if (typeof val === 'boolean') return val ? 'Yes' : 'No';
    if (String(val).trim() === '') return null;
    if (String(val).trim() === '[]') return null;
    if (String(val).trim() === '{}') return null;
    return String(val);
  };

  const addLink = (topic, collector, field_type, summary, url) => {
    if (!summary) return;
    if (String(summary).trim() === '' || String(summary) === '[]' || String(summary) === '{}') return;
    
    let finalUrl = url;
    if (!finalUrl) {
      if (collector === 'Wikipedia') finalUrl = co.Wikipedia?.findings?.url || mod.wikipedia_url;
      else if (collector === 'Wikidata') finalUrl = co.Wikidata?.findings?.url || co.Wikidata?.findings?.official_website;
      else if (collector === 'SECCollector') finalUrl = co.SECCollector?.findings?.filing_url || mod.filing_url;
      else if (collector === 'DomainScraper') finalUrl = mod.official_website || mod.url;
    }
    if (!finalUrl) {
      finalUrl = mod.official_website || mod.url || mod.source_url || mod.filing_url || mod.wikipedia_url || null;
    }
    rawLinks.push({ topic, collector, field_type, evidence: summary, url: finalUrl, status: 'Verified', priority: PRIORITY_MAP[collector] || 99 });
  };

  if (modNameLow.includes('acquisitions') || modNameLow.includes('mergers')) {
     addLink('Acquisitions', 'Wikipedia', 'acquisitions', formatEv(co.Wikipedia?.findings, 'acquisitions'), null);
     addLink('Acquisitions', 'Wikidata', 'acquisitions', formatEv(co.Wikidata?.findings, 'acquisitions'), null);
     addLink('Acquisitions', 'ResponsesAPI', 'acquisitions', formatEv(co.ResponsesAPI?.findings, 'acquisitions'), null);
     addLink('Acquisitions', 'SECCollector', 'acquisitions', formatEv(co.SECCollector?.findings, 'acquisitions'), null);
  }
  
  if (modNameLow.includes('sensitive information') || modNameLow.includes('b2c')) {
     addLink('Customer Segments', 'DomainScraper', 'customer_type', formatEv(co.DomainScraper?.findings, 'customer_type'), null);
     addLink('Ecommerce Evidence', 'DomainScraper', 'ecommerce', formatEv(co.DomainScraper?.findings, 'has_ecommerce'), null);
     addLink('Privacy Policy', 'DomainScraper', 'privacy_policy_url', formatEv(co.DomainScraper?.findings, 'privacy_policy_url'), co.DomainScraper?.findings?.privacy_policy_url);
     addLink('Official Website', 'System', 'official_website', mod.official_website ? mod.official_website : null, mod.official_website);
  }

  if (modNameLow.includes('domain encryption') || modNameLow.includes('internet footprint')) {
     addLink('Domain Scan', 'DomainScraper', 'domain_list', formatEv(co.DomainScraper?.findings, 'domains'), null);
     addLink('Official Website', 'System', 'official_website', mod.official_website ? mod.official_website : null, mod.official_website);
  }

  if (modNameLow.includes('geographic spread')) {
     addLink('Official Website', 'Wikidata', 'official_website', formatEv(co.Wikidata?.findings, 'official_website'), co.Wikidata?.findings?.official_website);
     addLink('Countries of Operation', 'Wikipedia', 'countries_of_operation', formatEv(co.Wikipedia?.findings, 'countries'), null);
     addLink('Headquarters', 'DBCollector', 'headquarters_country', formatEv(co.DBCollector?.findings, 'headquarters'), null);
  }

  if (modNameLow.includes('nature of services')) {
     addLink('Products and Services', 'DomainScraper', 'products', formatEv(co.DomainScraper?.findings, 'products'), null);
     addLink('Industry Classification', 'Wikidata', 'industry', formatEv(co.Wikidata?.findings, 'industry'), null);
     addLink('Industry Classification', 'Wikipedia', 'industry', formatEv(co.Wikipedia?.findings, 'industry'), null);
     addLink('Business Segments', 'SECCollector', 'business_segments', formatEv(co.SECCollector?.findings, 'business_segments'), null);
     addLink('Official Website', 'System', 'official_website', mod.official_website ? mod.official_website : null, mod.official_website);
  }
  
  if (modNameLow.includes('complexity')) {
     addLink('Subsidiaries', 'SECCollector', 'subsidiaries', formatEv(co.SECCollector?.findings, 'subsidiaries'), null);
     addLink('Subsidiaries', 'SECCollector', 'subsidiaries', formatEv(co.SECCollector?.findings, 'subsidiaries_list'), null);
     addLink('Subsidiaries', 'Wikipedia', 'subsidiaries', formatEv(co.Wikipedia?.findings, 'subsidiaries'), null);
     addLink('Subsidiaries', 'Wikidata', 'subsidiaries', formatEv(co.Wikidata?.findings, 'subsidiaries'), null);
  }
  
  if (modNameLow.includes('privacy regulation')) {
     addLink('Privacy Policy', 'DomainScraper', 'privacy_policy_url', formatEv(co.DomainScraper?.findings || mod, 'privacy_policy_url'), co.DomainScraper?.findings?.privacy_policy_url || mod.privacy_policy_url);
     addLink('Terms Page', 'DomainScraper', 'terms_url', formatEv(co.DomainScraper?.findings || mod, 'terms_url'), co.DomainScraper?.findings?.terms_url || mod.terms_url);
     addLink('Compliance Mentions', 'DomainScraper', 'compliance', formatEv(co.DomainScraper?.findings, 'compliance'), null);
  }
  
  if (modNameLow.includes('seasonality')) {
     addLink('Quarterly Revenue', 'SECCollector', 'quarterly_revenue', formatEv(co.SECCollector?.findings, 'quarterly_revenue'), null);
  }

  if (modNameLow.includes('volatility')) {
     addLink('Cloud/SaaS Indicators', 'DomainScraper', 'cloud_indicators', formatEv(co.DomainScraper?.findings, 'cloud_indicators'), null);
     addLink('Official Website', 'System', 'official_website', mod.official_website ? mod.official_website : null, mod.official_website);
  }

  if (modNameLow.includes('years in business')) {
     addLink('Founding Year', 'DBCollector', 'founding_year', formatEv(co.DBCollector?.findings, 'founding_year'), null);
     addLink('Founding Year', 'Wikipedia', 'founding_year', formatEv(co.Wikipedia?.findings, 'founding_year'), null);
     addLink('Founding Year', 'Wikidata', 'founding_year', formatEv(co.Wikidata?.findings, 'founding_year'), null);
  }

  // 1. Group by semantic field_type
  const fieldMap = new Map();
  rawLinks.forEach(link => {
     let ft = link.field_type;
     // Add safe synonym mapping only where valid
     if (['headquarters_country', 'primary_country'].includes(ft)) ft = 'country';
     if (['official_websites'].includes(ft)) ft = 'official_website';
     if (['customer_segment_type'].includes(ft)) ft = 'customer_type';
     if (['has_ecommerce'].includes(ft)) ft = 'ecommerce';
     if (['sic_industry', 'industry_classification'].includes(ft)) ft = 'industry';
     if (['countries', 'countries_of_operation'].includes(ft)) ft = 'countries_of_operation';
     
     if (!fieldMap.has(ft)) fieldMap.set(ft, []);
     fieldMap.get(ft).push(link);
  });

  const uniqueSources = [];

  fieldMap.forEach((links, ft) => {
     links.sort((a, b) => a.priority - b.priority);
     const bestLink = links[0];
     
     let conflictBadge = null;
     if (links.length > 1) {
         for (let i = 1; i < links.length; i++) {
             const otherLink = links[i];
             const str1 = String(bestLink.evidence).toLowerCase().replace(/\s+/g, '');
             const str2 = String(otherLink.evidence).toLowerCase().replace(/\s+/g, '');
             
             // Do not show conflict badge when values are complementary rather than conflicting.
             if (str1 !== str2 && !str1.includes(str2) && !str2.includes(str1)) {
                 conflictBadge = {
                     field: bestLink.topic,
                     msg: `${otherLink.collector} returned conflicting data.`,
                     otherCollector: otherLink.collector,
                     otherEvidence: otherLink.evidence,
                     selectedCollector: bestLink.collector,
                     reason: 'Higher priority source and stronger entity match.'
                 };
                 console.log(`[Conflict Debug] field_type: ${ft} | Compared: ${bestLink.collector} vs ${otherLink.collector} | Values: ${bestLink.evidence} vs ${otherLink.evidence} | Decision: conflict | Reason: ${conflictBadge.reason}`);
                 break;
             } else {
                 console.log(`[Conflict Debug] field_type: ${ft} | Compared: ${bestLink.collector} vs ${otherLink.collector} | Values: ${bestLink.evidence} vs ${otherLink.evidence} | Decision: complementary/ignored | Reason: values do not meaningfully differ`);
             }
         }
     }
     
     bestLink.conflict = conflictBadge;
     uniqueSources.push(bestLink);
  });
  
  const finalSources = [];
  const globalSeen = new Set();
  
  uniqueSources.forEach(link => {
      const nUrl = normalizeUrl(link.url);
      const key = `${link.collector}-${link.evidence}-${nUrl}`.toLowerCase().trim();
      if (!globalSeen.has(key)) {
          globalSeen.add(key);
          finalSources.push(link);
      }
  });

  return finalSources;
};

export default function EvidenceSources({ mod }) {
  const [expanded, setExpanded] = useState(false);
  if (!mod) return null;

  const uniqueSources = extractEvidenceLinks(mod);

  if (uniqueSources.length === 0 && (!mod.evidence_summary || mod.evidence_summary === '[]')) {
    return <div style={{ color: '#94A3B8', fontSize: '0.85rem', fontStyle: 'italic' }}>No evidence returned.</div>;
  }
  
  const maxVisible = 5;
  const isExpandable = uniqueSources.length > maxVisible;
  const visibleItems = expanded ? uniqueSources : uniqueSources.slice(0, maxVisible);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {uniqueSources.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {visibleItems.map((src, i) => (
            <div key={i} style={{ border: '1px solid #E2E8F0', borderRadius: '6px', padding: '12px', background: '#FFFFFF', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
              
              {/* Conflict Badge */}
              {src.conflict && (
                <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '4px', padding: '8px', marginBottom: '12px' }}>
                  <div style={{ color: '#EF4444', fontWeight: 'bold', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
                    ⚠️ Conflict Detected
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#7F1D1D', marginBottom: '4px' }}>
                    Field: {src.conflict.field}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#991B1B', display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px' }}>
                    <strong>{src.conflict.otherCollector}:</strong> <span>{src.conflict.otherEvidence}</span>
                    <strong>{src.conflict.selectedCollector}:</strong> <span>{src.evidence}</span>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#B91C1C', marginTop: '6px', fontStyle: 'italic' }}>
                    Selected Source: {src.conflict.selectedCollector} <br/> Reason: {src.conflict.reason}
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div style={{ fontWeight: '600', color: '#0F172A', fontSize: '0.9rem' }}>{src.topic}</div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
                  <div style={{ fontSize: '0.7rem', color: '#475569', background: '#F1F5F9', padding: '2px 8px', borderRadius: '12px', fontWeight: '600' }}>{src.collector}</div>
                  <div style={{ fontSize: '0.65rem', color: '#F59E0B', marginTop: '2px', letterSpacing: '1px' }}>
                    {RELIABILITY_MAP[src.collector] || '★★★☆☆'}
                  </div>
                </div>
              </div>
              
              <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#64748B', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Evidence Summary
              </div>
              
              <div style={{ fontSize: '0.85rem', color: '#0F172A', marginBottom: '12px', lineHeight: '1.5', background: '#F8FAFC', padding: '8px', borderRadius: '4px', whiteSpace: 'pre-wrap' }}>
                {src.evidence}
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: '0.7rem', color: '#475569', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Detected by: <strong>{src.collector}</strong>
                </div>
                {src.url ? (
                  <a href={src.url} target="_blank" rel="noopener noreferrer" style={{
                    display: 'inline-block', background: '#EFF6FF', color: '#3B82F6', textDecoration: 'none',
                    padding: '4px 12px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600',
                    border: '1px solid #BFDBFE', transition: 'all 0.2s'
                  }}>
                    Source URL ↗
                  </a>
                ) : (
                  <span style={{ fontSize: '0.75rem', color: '#94A3B8', fontStyle: 'italic' }}>No Source URL available</span>
                )}
              </div>
            </div>
          ))}
          
          {isExpandable && (
            <button 
              onClick={() => setExpanded(!expanded)}
              style={{
                background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '8px', cursor: 'pointer',
                color: '#3B82F6', fontSize: '0.85rem', fontWeight: '600', textAlign: 'center',
                borderRadius: '6px', transition: 'all 0.2s'
              }}
            >
              {expanded ? 'Hide sources' : `View more sources (${uniqueSources.length - maxVisible} hidden)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export { extractEvidenceLinks };
