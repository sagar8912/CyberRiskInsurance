import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';
import Header from './components/Header';
import CompanyInput from './components/CompanyInput';
import VerdictCard from './components/VerdictCard';
import ReconciledProfile from './components/ReconciledProfile';
import AgentWorkflow from './components/AgentWorkflow';
import ModifierTable from './components/ModifierTable';
import ExecutionTimeline from './components/ExecutionTimeline';
import AgentResultCards from './components/AgentResultCards';
import LiveAgentTelemetry from './components/LiveAgentTelemetry';
import AdminLogsPanel from './components/AdminLogsPanel';
import BatchAnalysisModal from './components/BatchAnalysisModal';
import { ErrorBoundary } from './components/ErrorBoundary';

import './components.css';

import {
  reconciledProfile as mockReconciled,
  factCheckerClaims as mockClaims,
  modifiers as mockModifiers,
  finalVerdict as mockVerdict
} from './data/mockData';

function App() {
  const [company, setCompany] = useState('Microsoft');
  const [domain, setDomain] = useState('microsoft.com');
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [apiFailed, setApiFailed] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [isAdminMode, setIsAdminMode] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);

  // Automated execution flow state
  const [currentStep, setCurrentStep] = useState(0);

  const addToast = (message, type = 'success') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const runPollingFallback = async (runId, apiUrl) => {
    console.warn(`[Resiliency] Switching to fallback polling /api/run-status/${runId} every 2s...`);
    addToast("Switched to polling mode for live updates", "info");
    let attempts = 0;
    while (attempts < 60) {
      attempts++;
      try {
        const res = await fetch(`${apiUrl}/api/run-status/${runId}`);
        if (res.ok) {
          const statusData = await res.json();
          if (statusData.step) {
            setCurrentStep(prev => Math.max(prev, statusData.step));
          }
          if (statusData.status === 'completed' && statusData.result) {
            console.info("[Polling] Stopped because run completed");
            setAnalysisData(statusData.result);
            setHasRun(true);
            setIsStreaming(false);
            addToast("Analysis completed successfully", "success");
            setApiFailed(false);
            return;
          } else if (statusData.status === 'failed') {
            console.error("Workflow error:", statusData.error);
            addToast(statusData.error || "Workflow failed", "error");
            setApiFailed(true);
            setIsStreaming(false);
            return;
          }
        } else if (res.status === 404 && attempts > 5) {
          break;
        }
      } catch (err) {
        console.error("[Polling] Error checking run status:", err);
      }
      await new Promise(r => setTimeout(r, 2000));
    }
    console.error("Polling fallback failed. Using mock data.");
    setApiFailed(true);
    setIsStreaming(false);
    setCurrentStep(7);
    setHasRun(true);
    addToast("Failed to connect. Using cached mock data.", "warning");
  };

  const streamAnalysis = async () => {
    const runId = 'run_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    const apiUrl = (import.meta.env.VITE_API_URL !== undefined && import.meta.env.VITE_API_URL !== '')
      ? import.meta.env.VITE_API_URL
      : (import.meta.env.PROD ? '' : 'http://localhost:8000');

    let sseActive = true;
    let lastEventTime = Date.now();
    const abortController = new AbortController();

    // Watchdog timer: If SSE connects but no events (not even heartbeats or steps) arrive for >6s, abort SSE and switch to polling
    const watchdog = setInterval(() => {
      if (sseActive && Date.now() - lastEventTime > 6000) {
        console.warn("[Resiliency] SSE watchdog timed out (no incremental events). Aborting stream and falling back to polling...");
        sseActive = false;
        abortController.abort();
      }
    }, 2000);

    try {
      const response = await fetch(`${apiUrl}/api/analyze/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company, domain, run_id: runId }),
        signal: abortController.signal
      });

      if (!response.ok) throw new Error(`API Error: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (sseActive) {
        const { value, done } = await reader.read();
        if (done) break;

        lastEventTime = Date.now();
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith(': heartbeat')) {
            lastEventTime = Date.now();
          } else if (trimmed.startsWith('data:')) {
            lastEventTime = Date.now();
            const dataStr = trimmed.slice(5).trim();
            if (dataStr) {
              try {
                const event = JSON.parse(dataStr);
                if (event.type === 'step') {
                  setCurrentStep(prev => Math.max(prev, event.step));
                } else if (event.type === 'result') {
                  setAnalysisData(event.data);
                  setHasRun(true);
                  setIsStreaming(false);
                  addToast("Analysis completed successfully", "success");
                  setApiFailed(false);
                  clearInterval(watchdog);
                  return;
                } else if (event.type === 'error') {
                  console.error("Workflow error:", event.message);
                  addToast(event.message, "error");
                  setApiFailed(true);
                  setIsStreaming(false);
                  clearInterval(watchdog);
                  return;
                }
              } catch (e) {
                console.error("Failed to parse event JSON:", e, dataStr);
              }
            }
          }
        }
      }
      clearInterval(watchdog);
      if (!sseActive) {
        await runPollingFallback(runId, apiUrl);
      }
    } catch (error) {
      clearInterval(watchdog);
      console.warn("SSE fetch failed or aborted. Initiating fallback polling mechanism...", error);
      await runPollingFallback(runId, apiUrl);
    }
  };

  const handleRunFullAnalysis = async () => {
    setAnalysisData(null); // Force clear so new data loads
    setHasRun(false);
    setCurrentStep(1);
    setIsStreaming(true);
    await streamAnalysis();
  };

  const handleNextStep = async () => {
    if (currentStep === 0) {
      setHasRun(false);
      setIsStreaming(true);
      await streamAnalysis();
    } else {
      setCurrentStep(prev => {
        const next = prev < 7 ? prev + 1 : 7;
        if (next === 7) setHasRun(true);
        return next;
      });
    }
  };

  const handlePrevStep = () => {
    setCurrentStep(prev => {
      const next = prev > 1 ? prev - 1 : 1;
      setHasRun(false); // Can't be fully run if stepping back
      return next;
    });
  };

  // If user changes inputs, reset step state so they can start fresh
  const handleCompanyChange = (val) => {
    setCompany(val);
    if (currentStep > 0 || hasRun || apiFailed || analysisData) {
      setCurrentStep(0);
      setHasRun(false);
      setAnalysisData(null);
      setApiFailed(false);
    }
  };

  const handleDomainChange = (val) => {
    setDomain(val);
    if (currentStep > 0 || hasRun || apiFailed || analysisData) {
      setCurrentStep(0);
      setHasRun(false);
      setAnalysisData(null);
      setApiFailed(false);
    }
  };

  const activeReconciled = analysisData?.reconciled_profile || (apiFailed ? mockReconciled : null);
  const activeClaims = analysisData?.fact_checker_claims || (apiFailed ? mockClaims : []);
  const activeModifiers = analysisData?.modifiers || (apiFailed ? mockModifiers : []);
  const activeVerdict = analysisData?.final_verdict || (apiFailed ? mockVerdict : null);

  // Progressive disclosure
  const showWorkflow = currentStep > 0 || hasRun;
  const showReconciled = (analysisData || apiFailed) && (hasRun || currentStep >= 4);
  const showModifiers = (analysisData || apiFailed) && (hasRun || currentStep >= 6);
  const showVerdict = (analysisData || apiFailed) && (hasRun || currentStep >= 7);

  return (
    <div className="dashboard-container">

      <Header
        isLoading={isStreaming}
        apiFailed={apiFailed}
        isAdminMode={isAdminMode}
        setIsAdminMode={setIsAdminMode}
        setIsBatchModalOpen={setIsBatchModalOpen}
      />

      <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%', paddingTop: '32px' }}>
        <CompanyInput
          company={company}
          setCompany={handleCompanyChange}
          domain={domain}
          setDomain={handleDomainChange}
          onNextStep={handleNextStep}
          onPrevStep={handlePrevStep}
          onRunFullAnalysis={handleRunFullAnalysis}
          currentStep={currentStep}
          isAutoPlaying={isStreaming}
          hasRun={hasRun}
          apiFailed={apiFailed}
        />
      </div>

      {showWorkflow && (
        <div className="fade-in-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '32px', marginBottom: '32px' }}>
          <LiveAgentTelemetry
            currentStep={currentStep}
            isAutoPlaying={isStreaming}
            hasRun={hasRun}
          />
        </div>
      )}

      {showVerdict && (
        <div className="fade-in-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '32px', marginBottom: '32px' }}>
          <AgentResultCards
            reconciledProfile={activeReconciled}
            claims={activeClaims}
            modifiers={activeModifiers}
            verdict={activeVerdict}
          />
        </div>
      )}

      {showWorkflow && (
        <AgentWorkflow isLoading={isStreaming} hasRun={hasRun} currentStep={currentStep} collectorOutputs={analysisData?.collectorOutputs} />
      )}

      <ExecutionTimeline isLoading={isStreaming} hasRun={hasRun} currentStep={currentStep} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
        {showReconciled && (
          <ReconciledProfile data={activeReconciled} claims={activeClaims} verdict={activeVerdict} />
        )}

        {showModifiers && <ModifierTable data={activeModifiers} isAdminMode={isAdminMode} verdictData={activeVerdict ? { target_entity: analysisData?.target_entity, final_verdict: activeVerdict } : null} />}

        {showVerdict && (
          <div className="fade-in-slide-up">
            <VerdictCard data={activeVerdict} modifiers={activeModifiers} claims={activeClaims} />
          </div>
        )}

        {isAdminMode && showWorkflow && (
          <div className="fade-in-slide-up" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

            <AdminLogsPanel analysisData={analysisData || {}} />
          </div>
        )}
      </div>

      <ErrorBoundary>
        <BatchAnalysisModal isOpen={isBatchModalOpen} onClose={() => setIsBatchModalOpen(false)} />
      </ErrorBoundary>

      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast ${toast.type}`}>
            {toast.type === 'success' ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
            {toast.message}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
