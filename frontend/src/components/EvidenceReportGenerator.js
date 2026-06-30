import { modifierMetadata } from './ModifierTable';
import { extractEvidenceLinks } from './EvidenceSources';

export const getReportHtml = (data, companyName, verdictData) => {
  // Strip internal logs and prompts - we only include what's safe
  const timestamp = new Date().toLocaleString();
  const company = companyName || 'Target Profile';
  
  let riskCategory = "N/A";
  let confidenceScore = "N/A";

  if (verdictData) {
    riskCategory = verdictData.riskCategory || riskCategory;
    confidenceScore = verdictData.underwritingScore || confidenceScore;
  }
  
  let html = `<html><head><title>Evidence Report - ${company}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 40px; color: #334155; line-height: 1.6; } 
    h1 { color: #0F172A; }
    .modifier { margin-bottom: 30px; border: 1px solid #E2E8F0; padding: 20px; border-radius: 8px; background: #F8FAFC; page-break-inside: avoid; }
    .modifier h2 { margin-top: 0; color: #F26A21; font-size: 1.2rem; }
    h3 { font-size: 1rem; color: #475569; margin-bottom: 8px; border-bottom: 1px solid #CBD5E1; padding-bottom: 4px; }
    ul { margin: 0; padding-left: 20px; }
    li { margin-bottom: 4px; }
    @media print {
      body { padding: 0; }
      .modifier { border: none; background: transparent; border-bottom: 1px solid #ccc; border-radius: 0; }
    }
  </style>
  </head><body>
  <h1>Evidence Report</h1>
  <p><strong>Timestamp:</strong> ${timestamp}</p>
  <p><strong>Company:</strong> ${company}</p>
  <p><strong>Final Verdict:</strong> ${riskCategory}</p>
  <p><strong>Overall Confidence:</strong> ${confidenceScore}</p>
  <hr/>`;
  
  data.forEach(mod => {
      const meta = modifierMetadata[mod.name] || { scale: "Variable", logic: "Derived dynamically based on inputs" };
      let rawConf = mod.confidence || mod.confidence_score || mod.evidence_confidence || mod.fact_checker_confidence || mod.accuracy_score || mod.claims_accuracy || mod.sources_confidence;
      if (rawConf === undefined || rawConf === null || rawConf === "") {
        const fcStr = JSON.stringify(mod.fact_checker_result || mod.fact_checker_output || '').toLowerCase();
        if (fcStr.includes('partially verified')) rawConf = 75;
        else if (fcStr.includes('verified')) rawConf = 100;
        else if (fcStr.includes('unsupported') || fcStr.includes('rejected')) rawConf = 40;
      }
      const conf = rawConf !== undefined && rawConf !== null ? `(Confidence: ${rawConf}%)` : '(Confidence: Unavailable)';
      
      html += `<div class="modifier">
          <h2>${mod.name}</h2>
          <p><strong>Category:</strong> ${mod.rating} ${conf}</p>
          <p><strong>Raw Score:</strong> ${mod.score || 'N/A'}</p>
          <p><strong>Formula:</strong> ${meta.logic}</p>
          <h3>Decision Summary</h3>
          <p>${mod.summary || mod.rationale || 'N/A'}</p>`;
      
      if (mod.positive_factors) {
        html += `<p><strong>Positive Factors:</strong></p><ul>`;
        const pf = Array.isArray(mod.positive_factors) ? mod.positive_factors : [mod.positive_factors];
        pf.forEach(f => html += `<li>${f}</li>`);
        html += `</ul>`;
      }

      if (mod.risk_factors) {
        html += `<p><strong>Risk Factors:</strong></p><ul>`;
        const rf = Array.isArray(mod.risk_factors) ? mod.risk_factors : [mod.risk_factors];
        rf.forEach(f => html += `<li>${f}</li>`);
        html += `</ul>`;
      }

      // Use the robust source extraction utility
      const uniqueSources = extractEvidenceLinks(mod);

      if (uniqueSources.length > 0 || mod.evidence_summary) {
        html += `<h3>Supporting Evidence</h3><ul>`;
        uniqueSources.forEach(src => {
          const urlHtml = src.url ? `<br/><a href="${src.url}" target="_blank" style="display:inline-block; margin-top:4px; padding:2px 6px; background:#EFF6FF; color:#3B82F6; text-decoration:none; font-size:0.85rem; border:1px solid #BFDBFE; border-radius:4px;">Open ${src.title.includes('Wikipedia') ? 'Wikipedia' : (src.title.includes('SEC') ? 'SEC Filing' : (src.title.includes('Privacy') ? 'Privacy Policy' : (src.title.includes('Terms') ? 'Terms' : (src.title.includes('Website') ? 'Official Website' : 'Source'))))}</a>` : '';
          
          html += `<li style="margin-bottom: 12px; list-style: none;">
            <div style="font-weight: 600; color: #0F172A;"><span style="color: #059669;">✓</span> ${src.title}</div>
            <div style="font-size: 0.85rem; color: #475569;">Collector: ${src.collector}</div>
            <div style="font-size: 0.85rem; color: #475569;">Evidence: ${src.evidence}</div>
            ${urlHtml}
          </li>`;
        });
        
        if (uniqueSources.length === 0 && mod.evidence_summary) {
           const es = Array.isArray(mod.evidence_summary) ? mod.evidence_summary : [mod.evidence_summary];
           es.forEach(f => html += `<li>✓ ${f}</li>`);
        }
        html += `</ul>`;
      }
      
      if (mod.conclusion) {
        html += `<p><strong>Conclusion:</strong> ${mod.conclusion}</p>`;
      }

      html += `</div>`;
  });
  html += `</body></html>`;
  return html;
};

export const downloadReportHtml = (data, companyName, verdictData) => {
  const html = getReportHtml(data, companyName, verdictData);
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `Evidence_Report_${new Date().toISOString().split('T')[0]}.html`;
  a.click();
  URL.revokeObjectURL(url);
};

export const printReportPdf = (data, companyName, verdictData) => {
  const html = getReportHtml(data, companyName, verdictData);
  const printWindow = window.open('', '_blank');
  printWindow.document.write(html);
  printWindow.document.close();
  printWindow.onload = () => {
    printWindow.focus();
    printWindow.print();
  };
};
