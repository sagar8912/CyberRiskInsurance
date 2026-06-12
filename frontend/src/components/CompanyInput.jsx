import { Building2, Globe, Play, Info } from 'lucide-react';

export default function CompanyInput({ company, setCompany, domain, setDomain, onRunAnalysis, isLoading, apiFailed }) {
  const isValidDomain = domain === '' || /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(domain);

  return (
    <div className="glass-panel">
      <h2><Building2 size={20} color="var(--accent-cyan)" /> Target Entity Analysis</h2>
      <p className="text-muted" style={{ fontSize: '0.875rem', marginBottom: '20px' }}>Enter company name and domain to launch agent workflow.</p>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
        <div>
          <label className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', display: 'block' }}>Company Name</label>
          <input 
            type="text" 
            className="input-field" 
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Microsoft"
          />
        </div>
        <div>
          <label className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '8px', display: 'block' }}>Primary Domain</label>
          <div style={{ position: 'relative' }}>
            <Globe size={18} color="var(--text-secondary)" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
            <input 
              type="text" 
              className={`input-field ${!isValidDomain ? 'invalid' : ''}`}
              style={{ paddingLeft: '38px', borderColor: !isValidDomain ? 'var(--accent-red)' : '' }}
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. microsoft.com"
            />
          </div>
          {!isValidDomain && <div style={{ color: 'var(--accent-red)', fontSize: '0.75rem', marginTop: '4px' }}>Invalid domain format</div>}
        </div>
      </div>
      
      <div className="flex-between">
        <button 
          className="btn-primary" 
          onClick={onRunAnalysis}
          disabled={isLoading || !company || !domain || !isValidDomain}
          style={{ width: '200px' }}
        >
          {isLoading ? (
            <><div className="loader-small"></div> Processing...</>
          ) : (
            <><Play size={18} /> Run Analysis</>
          )}
        </button>

        {apiFailed && (
          <div className="mock-warning" style={{ margin: 0, padding: '8px 12px' }}>
            <Info size={16} /> API disconnected. Using mock fallback.
          </div>
        )}
      </div>
    </div>
  );
}
