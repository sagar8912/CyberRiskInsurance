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
      const conf = rawConf !== undefined && rawConf !== null ? `(Confidence: ${rawConf}%)` : '';
      
      html += `<div class="modifier">
          <h2>${mod.name}</h2>
          <p><strong>Category:</strong> ${mod.rating} ${conf}</p>`;
          
      const ratObj = typeof mod.rationale === 'object' && mod.rationale !== null ? mod.rationale : null;

      if (ratObj) {
          html += `<h3>Decision Summary</h3>
          <p>${ratObj.decision_summary}</p>
          
          <h3>Rule Evaluation</h3>
          <ul>`;
          if (ratObj.input_values) {
             Object.entries(ratObj.input_values).forEach(([k, v]) => {
                html += `<li><strong>${k}:</strong> ${v}</li>`;
             });
          } else if (ratObj.rule_evaluation) {
             Object.entries(ratObj.rule_evaluation).forEach(([k, v]) => {
                html += `<li><strong>${k}:</strong> ${v}</li>`;
             });
          }
          html += `</ul>
          
          <h3>Rule Conditions</h3>
          <p>${Array.isArray(ratObj.rule_conditions) ? ratObj.rule_conditions.map(c => `${c} - PASS ✓`).join('<br/>AND ') : (ratObj.rule_conditions || ratObj.matched_rule)}</p>
          <p><strong>Bucket:</strong> ${ratObj.rule_name || ratObj.matched_bucket}</p>
          
          <h3>Business Explanation</h3>
          <p>${ratObj.reason || ratObj.why}</p>
          
          <h3>Business Impact</h3>
          <ul>
            ${Array.isArray(ratObj.business_impact) ? ratObj.business_impact.map(i => `<li>${i}</li>`).join('') : `<li>${ratObj.business_impact}</li>`}
          </ul>
          
          ${ratObj.conclusion ? `<p><strong>Conclusion:</strong> ${ratObj.conclusion}</p>` : ''}`;
      } else {
          html += `<h3>Decision Summary</h3>
          <p>${mod.summary || mod.rationale || 'N/A'}</p>`;
          if (mod.conclusion) {
             html += `<p><strong>Conclusion:</strong> ${mod.conclusion}</p>`;
          }
      }
      
      let pf = mod.positive_factors || (ratObj && ratObj.positive_factors);
      let hasPf = pf && (Array.isArray(pf) ? pf.length > 0 : true);
      if (!hasPf && !ratObj) {
        const rat = ratObj ? ratObj.decision_summary + " " + (ratObj.reason || ratObj.why) : (mod.rationale || mod.summary || mod.decision_summary || "");
        if (rat.toLowerCase().includes('positive') || rat.toLowerCase().includes('favour') || rat.toLowerCase().includes('strong') || rat.toLowerCase().includes('mature')) {
           pf = [ ratObj ? (ratObj.reason || ratObj.why) : rat ];
           hasPf = true;
        }
      }

      if (hasPf) {
        html += `<p><strong>Positive Factors:</strong></p><ul>`;
        const pfArr = Array.isArray(pf) ? pf : [pf];
        pfArr.forEach(f => html += `<li>${f}</li>`);
        html += `</ul>`;
      }

      let rf = mod.risk_factors || (ratObj && ratObj.risk_factors);
      let hasRf = rf && (Array.isArray(rf) ? rf.length > 0 : true);
      if (!hasRf && !ratObj) {
        const rat = ratObj ? ratObj.decision_summary + " " + (ratObj.reason || ratObj.why) + " " + ratObj.business_impact : (mod.rationale || mod.summary || mod.decision_summary || "");
        if (rat.toLowerCase().includes('negative') || rat.toLowerCase().includes('unfavour') || rat.toLowerCase().includes('risk') || rat.toLowerCase().includes('regulatory complexity') || rat.toLowerCase().includes('large attack surface') || rat.toLowerCase().includes('high exposure')) {
           rf = [ ratObj ? (ratObj.reason || ratObj.why) : rat ];
           hasRf = true;
        }
      }

      if (hasRf) {
        html += `<p><strong>Risk Factors:</strong></p><ul>`;
        const rfArr = Array.isArray(rf) ? rf : [rf];
        rfArr.forEach(f => html += `<li>${f}</li>`);
        html += `</ul>`;
      }

      // Use the robust source extraction utility
      const uniqueSources = extractEvidenceLinks(mod);

      if (uniqueSources.length > 0) {
        html += `<h3>Supporting Evidence</h3><div style="display:flex; flex-direction:column; gap:12px;">`;
        uniqueSources.forEach(src => {
          let conflictHtml = '';
          if (src.conflict) {
             conflictHtml = `<div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:4px; padding:8px; margin-bottom:8px; font-size:0.75rem;">
               <div style="color:#EF4444; font-weight:bold; margin-bottom:4px;">⚠️ Conflict Detected</div>
               <div style="color:#7F1D1D; margin-bottom:4px;">Field: ${src.conflict.field || src.topic}</div>
               <div style="color:#991B1B;"><strong>${src.conflict.otherCollector}:</strong> <span>${src.conflict.otherEvidence}</span> <br/> <strong>${src.conflict.selectedCollector}:</strong> <span>${src.evidence}</span></div>
               <div style="color:#B91C1C; margin-top:6px; font-style:italic;">Selected Source: ${src.conflict.selectedCollector} (${src.conflict.reason})</div>
             </div>`;
          }

          const urlHtml = src.url ? `<a href="${src.url}" target="_blank" style="display:inline-block; background:#EFF6FF; color:#3B82F6; text-decoration:none; padding:4px 12px; border-radius:4px; font-size:0.75rem; border:1px solid #BFDBFE;">Source URL ↗</a>` : `<span style="font-size:0.75rem; color:#94A3B8; font-style:italic;">No Source URL available</span>`;
          
          html += `<div style="border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; background: #FFFFFF; page-break-inside: avoid;">
            ${conflictHtml}
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
               <strong style="color:#0F172A; font-size:0.9rem;">${src.topic || src.title}</strong>
               <span style="font-size:0.7rem; color:#475569; background:#F1F5F9; padding:2px 8px; border-radius:12px; font-weight:600;">${src.collector}</span>
            </div>
            <div style="font-size:0.75rem; font-weight:600; color:#64748B; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.05em;">Evidence Summary</div>
            <div style="font-size:0.85rem; color:#0F172A; background:#F8FAFC; padding:8px; border-radius:4px; white-space:pre-wrap; margin-bottom:12px;">${src.evidence}</div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
               <div style="font-size:0.7rem; color:#475569;">Detected by: <strong>${src.collector}</strong></div>
               ${urlHtml}
            </div>
          </div>`;
        });
        html += `</div>`;
      } else if (mod.evidence_summary && String(mod.evidence_summary).trim() !== '[]' && String(mod.evidence_summary).trim() !== '') {
        html += `<h3>Supporting Evidence</h3><ul style="margin:0; padding-left:20px; font-size:0.85rem; color:#475569;">`;
        const es = Array.isArray(mod.evidence_summary) ? mod.evidence_summary : [mod.evidence_summary];
        es.forEach(f => {
           if (String(f).trim() !== '') html += `<li>${f}</li>`;
        });
        html += `</ul>`;
      } else {
        html += `<h3>Supporting Evidence</h3><p style="color:#94A3B8; font-size:0.85rem; font-style:italic;">No evidence returned.</p>`;
      }
      
      // Conclusion is now handled inside ratObj block or as fallback above
      html += `</div>`;
      
      const backendCat = (ratObj && ratObj.assigned_category) || 'N/A';
      console.log(`[Report Validation] ${mod.name} | Backend: ${backendCat} | Frontend: ${mod.rating} | Match: ${backendCat.toUpperCase() === (mod.rating || '').toUpperCase()}`);
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
