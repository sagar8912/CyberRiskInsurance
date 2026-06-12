import React, { useState, useEffect } from 'react';
import { Check, CircleDashed } from 'lucide-react';

export default function ExecutionTimeline({ isLoading, hasRun }) {
  const steps = [
    "Supervisor Validation",
    "Parallel Collectors",
    "Coordinator Reconciliation",
    "Fact Verification",
    "Underwriting Modifiers",
    "Final Verdict"
  ];

  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (isLoading) {
      setActiveStep(0);
      const interval = setInterval(() => {
        setActiveStep(prev => (prev < 5 ? prev + 1 : prev));
      }, 800); // Progressively highlight steps while loading
      return () => clearInterval(interval);
    } else if (hasRun) {
      setActiveStep(6); // All complete
    } else {
      setActiveStep(-1); // Not started
    }
  }, [isLoading, hasRun]);

  return (
    <div className="glass-panel" style={{ padding: '20px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'relative' }}>
        {/* Background track line */}
        <div style={{ position: 'absolute', top: '12px', left: '40px', right: '40px', height: '2px', background: 'rgba(255,255,255,0.05)', zIndex: 0 }}></div>
        
        {/* Animated active line */}
        <div style={{ 
            position: 'absolute', top: '12px', left: '40px', height: '2px', background: 'var(--accent-cyan)', zIndex: 1,
            width: activeStep >= 0 ? `${(Math.min(activeStep, 5) / 5) * 100}%` : '0%',
            transition: 'width 0.5s ease-in-out',
            boxShadow: '0 0 10px var(--accent-cyan)'
        }}></div>

        {steps.map((step, idx) => {
          const isCompleted = activeStep > idx || hasRun;
          const isCurrent = activeStep === idx && isLoading;
          
          return (
            <div key={idx} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', zIndex: 2, width: '120px' }}>
              <div style={{
                width: '24px', height: '24px', borderRadius: '50%',
                display: 'flex', justifyContent: 'center', alignItems: 'center',
                background: isCompleted ? 'var(--accent-cyan)' : (isCurrent ? 'var(--bg-surface)' : 'var(--bg-base)'),
                border: `2px solid ${isCompleted || isCurrent ? 'var(--accent-cyan)' : 'var(--border-color)'}`,
                color: isCompleted ? '#000' : 'var(--accent-cyan)',
                transition: 'all 0.3s',
                boxShadow: isCurrent ? '0 0 15px rgba(34, 211, 238, 0.4)' : 'none'
              }}>
                {isCompleted ? <Check size={14} strokeWidth={3} /> : (isCurrent ? <CircleDashed size={14} className="pulse-glow" style={{ animation: 'spin 2s linear infinite' }} /> : <span style={{ fontSize: '10px' }}>{idx + 1}</span>)}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                <div style={{ 
                  fontSize: '0.75rem', textAlign: 'center', fontWeight: '600',
                  color: isCompleted ? 'var(--text-secondary)' : (isCurrent ? 'var(--text-primary)' : 'rgba(255,255,255,0.3)')
                }}>
                  {step}
                </div>
                <div style={{ 
                  fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '500',
                  color: isCompleted ? 'var(--accent-cyan)' : (isCurrent ? 'var(--accent-cyan)' : 'var(--text-secondary)'),
                  opacity: isCompleted ? 0.6 : 1
                }}>
                  {isCompleted ? 'Completed' : (isCurrent ? 'Running' : 'Waiting')}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  );
}
