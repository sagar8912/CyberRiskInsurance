import { FileText, Database, MapPin, Building, Globe, ShieldCheck } from 'lucide-react';

export default function ReconciledProfile({ data, claims, verdict }) {
  if (!data) return null;

  const scoreNum = verdict ? (parseFloat(verdict.underwritingScore.replace('%','')) || 0) : 100;
  const isLowConfidence = scoreNum === 0 || (verdict && verdict.confidenceBand === 'Low');
  const isZeroConfidence = scoreNum === 0;

  const getClaimStatus = (claimName) => {
    if (!claims || !claimName) return null;
    const claim = claims.find(c => c.claim === claimName);
    if (claim) return claim.status; // "Verified", "Partially Verified", "Unsupported"
    if (isZeroConfidence) return "Provisional";
    return null;
  };

  const getStatusBadge = (status) => {
    if (!status) return null;
    if (status === "Verified") return <span className="badge success" style={{fontSize: '0.65rem', padding: '2px 6px'}}>Verified</span>;
    if (status === "Partially Verified") return <span className="badge warning" style={{fontSize: '0.65rem', padding: '2px 6px'}}>Partial</span>;
    if (status === "Unsupported") return <span className="badge danger" style={{fontSize: '0.65rem', padding: '2px 6px'}}>Unsupported</span>;
    if (status === "Provisional") return <span className="badge neutral" style={{fontSize: '0.65rem', padding: '2px 6px'}}>Provisional</span>;
    return null;
  };

  let formattedRevenue = data.revenue;
  if (typeof formattedRevenue === 'string' && formattedRevenue.startsWith('$')) {
    formattedRevenue = formattedRevenue.replace(/\s/g, '');
  }
  const profileItems = [
    { label: "Revenue", value: formattedRevenue, icon: <Database size={16} color="var(--accent-cyan)" />, claimName: "revenue" },
    { label: "Subsidiaries", value: data.subsidiariesCount, icon: <Building size={16} color="var(--accent-blue)" />, claimName: "subsidiaries_count" },
    { label: "Acquisitions", value: data.acquisitionsCount, icon: <Building size={16} color="var(--accent-teal)" />, claimName: "acquisitions_count" },
    { label: "Customer Type", value: data.customerType, icon: <Globe size={16} color="var(--accent-cyan)" />, claimName: "customer_type" },
    { label: "E-Commerce", value: (data.ecommercePlatform || data.has_ecommerce || data.ecommerce) ? "True" : "False", icon: <Globe size={16} color="var(--accent-blue)" />, claimName: "has_ecommerce" },
    { label: "Countries of Ops", value: data.countriesOfOps, icon: <MapPin size={16} color="var(--accent-teal)" />, claimName: null },
    { label: "Privacy Policy", value: data.privacyPolicy ? "Published" : "Unknown", icon: <ShieldCheck size={16} color="var(--accent-success)" />, claimName: "privacy_policy_published" },
  ];

  return (
    <div className="glass-panel">
      <h2><FileText size={20} color="var(--accent-cyan)" /> Reconciled Profile</h2>
      {isLowConfidence ? (
         <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
               <span className="badge warning">Provisional / Low Evidence</span>
            </div>
            <p className="text-muted" style={{ fontSize: '0.85rem' }}>These profile values were collected by agents but could not be strongly corroborated by evidence sources.</p>
         </div>
      ) : (
         <p className="text-muted" style={{ fontSize: '0.875rem', marginBottom: '20px' }}>Merged and de-conflicted from prioritized agent collector sources</p>
      )}
      
      <div className="metric-grid">
        {profileItems.map((item, i) => (
          <div key={i} className="metric-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
              <div className="metric-label">
                {item.icon} {item.label}
              </div>
              <div>
                {getStatusBadge(getClaimStatus(item.claimName))}
              </div>
            </div>
            <div className="metric-value" style={{ 
              wordBreak: 'normal', 
              whiteSpace: item.label === "Countries of Ops" ? 'normal' : 'nowrap', 
              overflowWrap: 'normal',
              lineHeight: '1.2' 
            }}>
              {item.value === "True" || item.value === "Published" ? (
                <span className="badge success">{item.value}</span>
              ) : item.value === "False" || item.value === "Unknown" ? (
                <span className="badge neutral">{item.value}</span>
              ) : (
                item.value
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
