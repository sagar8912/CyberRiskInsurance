import { Activity, WifiOff, RefreshCw, Database, ShieldAlert } from 'lucide-react';

export default function Header({ isLoading, apiFailed, isAdminMode, setIsAdminMode, setIsBatchModalOpen }) {
  const getStatusBadge = () => {
    if (isLoading) return <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: '800', color: '#D97706', background: '#FEF3C7', padding: '8px 16px', borderRadius: '99px' }}><RefreshCw size={16} className="pulse-glow" style={{ animation: 'spin 2s linear infinite' }} /> SYSTEM RUNNING</div>;
    if (apiFailed) return <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: '800', color: '#DC2626', background: '#FEF2F2', padding: '8px 16px', borderRadius: '99px' }}><WifiOff size={16} /> API DISCONNECTED</div>;
    return <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', fontWeight: '800', color: '#059669', background: '#ECFDF5', padding: '8px 16px', borderRadius: '99px' }}><Activity size={16} /> SYSTEM CONNECTED</div>;
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'space-between', 
      alignItems: 'center', 
      padding: '20px 40px', 
      background: '#FFFFFF', 
      borderBottom: '1px solid #E2E8F0',
      width: '100%',
      position: 'sticky',
      top: 0,
      zIndex: 50,
      boxShadow: '0 2px 4px rgba(0,0,0,0.02)'
    }}>
      
      <div>
        <img src="/exl-logo.png" alt="EXL Logo" style={{ height: '32px', objectFit: 'contain' }} />
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <button 
          onClick={() => setIsBatchModalOpen(true)}
          style={{
            background: '#F1F5F9', border: '1px solid #E2E8F0', padding: '8px 16px', 
            borderRadius: '6px', color: '#475569', fontSize: '0.85rem', fontWeight: '600',
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px'
          }}
        >
          <Database size={16} /> Batch Analysis
        </button>

        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <span style={{ fontSize: '0.85rem', color: isAdminMode ? '#F26A21' : '#64748B', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '4px' }}>
             {isAdminMode && <ShieldAlert size={14} />} Admin Mode
          </span>
          <div style={{ 
            width: '36px', height: '20px', 
            background: isAdminMode ? '#F26A21' : '#E2E8F0', 
            borderRadius: '10px', position: 'relative', transition: '0.3s' 
          }}>
            <div style={{ 
              width: '16px', height: '16px', 
              background: '#fff', borderRadius: '50%', 
              position: 'absolute', top: '2px', 
              left: isAdminMode ? '18px' : '2px', 
              transition: '0.3s' 
            }}></div>
          </div>
          <input 
            type="checkbox" 
            style={{ display: 'none' }} 
            checked={isAdminMode} 
            onChange={(e) => setIsAdminMode(e.target.checked)} 
          />
        </label>
        
        {getStatusBadge()}
      </div>
      
    </div>
  );
}
