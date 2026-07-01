import React from 'react';
import { Terminal, Download, ShieldAlert } from 'lucide-react';

export default function AdminLogsPanel({ analysisData }) {
  if (!analysisData) return null;

  const logs = analysisData.logs || [];
  const collectorOutputs = analysisData.collectorOutputs || {};
  const promptResponses = analysisData.promptResponses || {};
  const factCheckerOutput = analysisData.factCheckerOutput || null;
  const coordinatorOutput = analysisData.coordinatorOutput || null;
  const underwriterOutput = analysisData.underwriterOutput || null;
  const modifierLogs = analysisData.modifier_logs || null;
  const executionTimeline = analysisData.executionTimeline || [];
  const executionTime = analysisData.executionTime || null;
  const nodeStatus = analysisData.nodeStatus || {};

  const downloadLogs = () => {
    let content = "=== SYSTEM EXECUTION LOGS ===\n\n";
    content += `Timestamp: ${new Date().toISOString()}\n`;
    content += `Company: ${analysisData.reconciled_profile?.company_name || 'N/A'}\n\n`;

    if (logs.length > 0) {
      content += "--- BACKEND TRACE ---\n";
      content += logs.join('\n') + '\n\n';
    }

    if (Object.keys(collectorOutputs).length > 0) {
      content += "--- COLLECTOR RAW OUTPUTS ---\n";
      content += JSON.stringify(collectorOutputs, null, 2) + '\n\n';
    }

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `execution_logs_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="glass-panel" style={{ marginTop: '32px', background: '#0F172A', color: '#F8FAFC', padding: '24px', borderRadius: '12px', border: '1px solid #334155' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid #1E293B', paddingBottom: '16px' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', color: '#F8FAFC' }}>
          <Terminal size={20} color="#F26A21" /> Backend Telemetry & Debug Logs
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '0.75rem', color: '#94A3B8', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldAlert size={14} /> Admin Privileges Active
          </span>
          <button
            onClick={downloadLogs}
            style={{
              background: '#F26A21', color: '#FFF', border: 'none', padding: '6px 12px',
              borderRadius: '6px', fontSize: '0.8rem', fontWeight: '700', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '6px'
            }}
          >
            <Download size={14} /> Download Complete Logs
          </button>
        </div>
      </div>

      <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '400px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', lineHeight: '1.5' }}>
        {logs.length > 0 ? (
          logs.map((log, i) => (
            <div key={i} style={{ color: log.includes('ERROR') ? '#EF4444' : log.includes('WARN') ? '#F59E0B' : '#64748B', marginBottom: '4px' }}>
              <span style={{ color: '#475569', marginRight: '8px' }}>[{new Date().toLocaleTimeString()}]</span>
              {log}
            </div>
          ))
        ) : (
          <div style={{ color: '#475569' }}>No raw execution logs available in current payload.</div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Execution Timeline</h3>
          <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '200px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#64748B' }}>
            {executionTimeline.length > 0 ? (
              executionTimeline.map((item, i) => (
                <div key={i} style={{ marginBottom: '4px' }}>
                  <span style={{ color: '#475569', marginRight: '8px' }}>[{item.time}]</span> {item.event}
                </div>
              ))
            ) : "No execution timeline available."}
          </div>
        </div>

        <div>
          <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Execution Stats</h3>
          <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '200px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#64748B' }}>
            <div><strong>Execution Time:</strong> {executionTime ? `${executionTime}s` : 'N/A'}</div>
            <div style={{ marginTop: '8px' }}><strong>Node Status:</strong></div>
            {Object.keys(nodeStatus).length > 0 ? (
              <pre style={{ margin: '4px 0 0 0', color: '#38BDF8' }}>{JSON.stringify(nodeStatus, null, 2)}</pre>
            ) : "No node status available."}
          </div>
        </div>
      </div>

      <div style={{ marginTop: '16px' }}>
        <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Collector Outputs</h3>
        <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38BDF8', whiteSpace: 'pre-wrap' }}>
          {Object.keys(collectorOutputs).length > 0
            ? JSON.stringify(collectorOutputs, null, 2)
            : "No collector outputs attached to payload."}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginTop: '16px' }}>
        {Object.keys(promptResponses).length > 0 && (
          <div>
            <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Prompt Responses</h3>
            <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38BDF8', whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(promptResponses, null, 2)}
            </div>
          </div>
        )}

        {factCheckerOutput && (
          <div>
            <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Fact Checker Output</h3>
            <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38BDF8', whiteSpace: 'pre-wrap' }}>
              {typeof factCheckerOutput === 'object' ? JSON.stringify(factCheckerOutput, null, 2) : factCheckerOutput}
            </div>
          </div>
        )}

        {coordinatorOutput && (
          <div>
            <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Coordinator Output</h3>
            <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38BDF8', whiteSpace: 'pre-wrap' }}>
              {typeof coordinatorOutput === 'object' ? JSON.stringify(coordinatorOutput, null, 2) : coordinatorOutput}
            </div>
          </div>
        )}

        {underwriterOutput && (
          <div>
            <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Underwriter Output</h3>
            <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38BDF8', whiteSpace: 'pre-wrap' }}>
              {typeof underwriterOutput === 'object' ? JSON.stringify(underwriterOutput, null, 2) : underwriterOutput}
            </div>
          </div>
        )}

        {modifierLogs && (
          <div>
            <h3 style={{ fontSize: '0.9rem', color: '#94A3B8', marginBottom: '8px' }}>Modifier Logs</h3>
            <div style={{ background: '#020617', padding: '16px', borderRadius: '8px', maxHeight: '250px', overflowY: 'auto', fontFamily: 'monospace', fontSize: '0.8rem', color: '#38BDF8', whiteSpace: 'pre-wrap' }}>
              {typeof modifierLogs === 'object' ? JSON.stringify(modifierLogs, null, 2) : modifierLogs}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
