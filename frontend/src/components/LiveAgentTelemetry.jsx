import React, { useState, useEffect, useRef } from 'react';
import { Activity, MessageSquare, Terminal } from 'lucide-react';

export default function LiveAgentTelemetry({ currentStep, isAutoPlaying, hasRun }) {
  const [messages, setMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const logsContainerRef = useRef(null);
  const messagesContainerRef = useRef(null);

  // Auto scroll internally to bottom without jumping page
  useEffect(() => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight;
    }
  }, [logs]);

  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (currentStep === 0 && !hasRun) {
      setMessages([]);
      setLogs([]);
      return;
    }

    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });

    // Simulate logs and messages based on current step
    if (currentStep === 1) {
      setLogs(prev => [...prev, { time: timeString, text: 'System Initialized. Awaiting Input.', status: 'info' }]);
    } else if (currentStep === 2) {
      setLogs(prev => [...prev, { time: timeString, text: 'Supervisor Agent Started', status: 'info' }]);
      setTimeout(() => setLogs(prev => [...prev, { time: timeString, text: 'Validating Entity Context', status: 'success' }]), 500);
      setMessages(prev => [...prev, { sender: 'Supervisor', receiver: 'Collectors', content: 'Context verified. Dispatching parallel scraping agents.', status: 'success' }]);
    } else if (currentStep === 3) {
      setLogs(prev => [
        ...prev, 
        { time: timeString, text: 'SEC Collector Started', status: 'info' },
        { time: timeString, text: 'Wikipedia Collector Started', status: 'info' },
        { time: timeString, text: 'Domain Scraper Started', status: 'info' }
      ]);
      setTimeout(() => {
        setLogs(prev => [...prev, { time: timeString, text: 'Financials Extracted', status: 'success' }]);
        setMessages(prev => [...prev, { sender: 'SEC Collector', receiver: 'Coordinator', content: 'Sent revenue=16B, subsidiaries=1', status: 'success' }]);
      }, 600);
      setTimeout(() => {
        setLogs(prev => [...prev, { time: timeString, text: 'Digital Footprint Scanned', status: 'success' }]);
        setMessages(prev => [...prev, { sender: 'Domain Scraper', receiver: 'Coordinator', content: 'Sent ecommerce=true, TLS=valid', status: 'success' }]);
      }, 1200);
    } else if (currentStep === 4) {
      setLogs(prev => [...prev, { time: timeString, text: 'Coordinator Agent Merging Evidence', status: 'warning' }]);
      setTimeout(() => {
        setLogs(prev => [...prev, { time: timeString, text: 'Entity Profile Reconciled', status: 'success' }]);
        setMessages(prev => [...prev, { sender: 'Coordinator', receiver: 'Fact Checker', content: 'Dispatched reconciled profile for claim validation.', status: 'success' }]);
      }, 1000);
    } else if (currentStep === 5) {
      setLogs(prev => [...prev, { time: timeString, text: 'Fact Checker Verifying Claims', status: 'warning' }]);
      setTimeout(() => {
        setLogs(prev => [...prev, { time: timeString, text: 'Claims Verification Complete', status: 'success' }]);
        setMessages(prev => [...prev, { sender: 'Fact Checker', receiver: 'Underwriter', content: 'Verified 4 claims, 2 partial, 1 unsupported.', status: 'warning' }]);
      }, 1000);
    } else if (currentStep === 6) {
      setLogs(prev => [...prev, { time: timeString, text: 'Underwriter Executing Risk Models', status: 'warning' }]);
      setTimeout(() => {
        setLogs(prev => [...prev, { time: timeString, text: '15 Modifiers Applied', status: 'success' }]);

        setMessages(prev => [...prev, { sender: 'Underwriter', receiver: 'System', content: 'Generated actuarial scores. Rendering Final Verdict.', status: 'success' }]);
      }, 1000);
    } else if (currentStep >= 7 || hasRun) {
      if (logs.length > 0 && logs[logs.length-1].text !== 'Analysis Complete') {
        setLogs(prev => [...prev, { time: timeString, text: 'Analysis Complete', status: 'success' }]);
      }
    }

  }, [currentStep, hasRun]);

  if (currentStep === 0 && !hasRun) return null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '32px' }}>
      
      {/* Live Agent Communication */}
      <div className="glass-panel" style={{ background: '#FFFFFF', padding: '0', display: 'flex', flexDirection: 'column', height: '350px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ padding: '16px', background: '#F8FAFC', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MessageSquare size={18} color="var(--accent-orange)" />
          <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: '700', color: 'var(--text-primary)' }}>Live Agent Communication</h3>
          {(isAutoPlaying || (currentStep > 0 && currentStep < 7)) && (
            <div className="loader-small" style={{ width: '12px', height: '12px', marginLeft: 'auto', borderColor: 'rgba(242, 106, 33, 0.3)', borderLeftColor: 'var(--accent-orange)' }}></div>
          )}
        </div>
        <div ref={messagesContainerRef} style={{ padding: '20px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', background: '#F8FAFC' }}>
          {messages.map((msg, idx) => (
            <div key={idx} className="fade-in-slide-up" style={{ 
              background: '#FFFFFF', 
              border: '1px solid #E5E7EB', 
              borderLeft: `4px solid ${msg.status === 'success' ? '#10B981' : (msg.status === 'warning' ? '#F59E0B' : '#EF4444')}`,
              borderRadius: '6px', 
              padding: '12px 16px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                <span style={{ fontWeight: '800', color: 'var(--text-primary)' }}>{msg.sender}</span>
                <span style={{ color: '#94A3B8' }}>➔</span>
                <span style={{ fontWeight: '700', color: 'var(--text-secondary)' }}>{msg.receiver}</span>
              </div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)', lineHeight: '1.5', fontWeight: '500' }}>
                {msg.content}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Live Activity Feed */}
      <div className="glass-panel" style={{ background: '#FFFFFF', padding: '0', display: 'flex', flexDirection: 'column', height: '350px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
        <div style={{ padding: '16px', background: '#F8FAFC', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={18} color="var(--accent-orange)" />
          <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '0.02em' }}>System Activity Feed</h3>
        </div>
        <div ref={logsContainerRef} style={{ padding: '16px 20px', flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.85rem', background: '#FFFFFF' }}>
          {logs.map((log, idx) => (
            <div key={idx} className="fade-in-slide-up" style={{ 
              display: 'flex', 
              gap: '16px', 
              padding: '10px 0',
              borderBottom: '1px solid #F1F5F9',
              color: log.status === 'success' ? '#059669' : (log.status === 'warning' ? '#D97706' : '#334155') 
            }}>
              <span style={{ color: '#94A3B8', flexShrink: 0, fontFamily: 'monospace', fontWeight: '600' }}>[{log.time}]</span>
              <span style={{ fontWeight: '500', lineHeight: '1.4' }}>{log.text}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
