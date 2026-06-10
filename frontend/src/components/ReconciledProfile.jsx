import { FileText, Database, MapPin, Building, Globe, ShieldCheck } from 'lucide-react';

export default function ReconciledProfile({ data }) {
  if (!data) return null;
  const profileItems = [
    { label: "Revenue", value: data.revenue, icon: <Database size={16} color="var(--accent-cyan)" /> },
    { label: "Subsidiaries", value: data.subsidiariesCount, icon: <Building size={16} color="var(--accent-blue)" /> },
    { label: "Acquisitions", value: data.acquisitionsCount, icon: <Building size={16} color="var(--accent-teal)" /> },
    { label: "Customer Type", value: data.customerType, icon: <Globe size={16} color="var(--accent-cyan)" /> },
    { label: "E-Commerce", value: data.ecommercePlatform ? "True" : "False", icon: <Globe size={16} color="var(--accent-blue)" /> },
    { label: "Countries of Ops", value: data.countriesOfOps, icon: <MapPin size={16} color="var(--accent-teal)" /> },
    { label: "Privacy Policy", value: data.privacyPolicy ? "Published" : "Unknown", icon: <ShieldCheck size={16} color="var(--accent-success)" /> },
  ];

  return (
    <div className="glass-panel">
      <h2><FileText size={20} color="var(--accent-cyan)" /> Reconciled Profile</h2>
      <p className="text-muted" style={{ fontSize: '0.875rem', marginBottom: '20px' }}>Merged and de-conflicted from prioritized agent collector sources</p>
      
      <div className="metric-grid">
        {profileItems.map((item, i) => (
          <div key={i} className="metric-card">
            <div className="metric-label">
              {item.icon} {item.label}
            </div>
            <div className="metric-value">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
