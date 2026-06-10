import { CheckCircle2, XCircle, AlertCircle, ListChecks } from 'lucide-react';

export default function FactCheckerTable({ data }) {
  if (!data) return null;
  
  const getBadge = (status) => {
    if (status === "Verified") return <span className="badge success">Verified</span>;
    if (status === "Partially Verified") return <span className="badge warning">Partial</span>;
    return <span className="badge danger">Unsupported</span>;
  };

  const getIcon = (status) => {
    if (status === "Verified") return <CheckCircle2 size={16} color="var(--accent-success)" />;
    if (status === "Partially Verified") return <AlertCircle size={16} color="var(--accent-warning)" />;
    return <XCircle size={16} color="var(--accent-danger)" />;
  };

  return (
    <div className="glass-panel" style={{ overflowX: 'auto', maxHeight: '400px', padding: 0 }}>
      <div style={{ padding: '24px 24px 16px 24px' }}>
        <h2 style={{ margin: 0 }}><ListChecks size={20} color="var(--accent-cyan)" /> Fact Checker Corroboration</h2>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>Underwriting Claim</th>
            <th>Status</th>
            <th>Source Count</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item, idx) => (
            <tr key={idx}>
              <td style={{ fontWeight: '500', color: 'var(--text-primary)' }}>{item.claim}</td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {getIcon(item.status)}
                  {getBadge(item.status)}
                </div>
              </td>
              <td style={{ fontFamily: 'monospace', fontSize: '1rem' }}>{item.sourceCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
