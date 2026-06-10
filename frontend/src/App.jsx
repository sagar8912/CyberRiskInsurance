import React, { useState } from 'react';
import Header from './components/Header';
import CompanyInput from './components/CompanyInput';
import VerdictCard from './components/VerdictCard';
import ReconciledProfile from './components/ReconciledProfile';
import AgentWorkflow from './components/AgentWorkflow';
import FactCheckerTable from './components/FactCheckerTable';
import ModifierTable from './components/ModifierTable';
import ExecutionTimeline from './components/ExecutionTimeline';
import EvidenceSources from './components/EvidenceSources';
import './components.css';

import { 
  reconciledProfile as mockReconciled, 
  factCheckerClaims as mockClaims, 
  modifiers as mockModifiers, 
  finalVerdict as mockVerdict 
} from './data/mockData';

function App() {
  const [company, setCompany] = useState('');
  const [domain, setDomain] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [apiFailed, setApiFailed] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);

  const handleRunAnalysis = async () => {
    setIsLoading(true);
    setHasRun(false);
    setApiFailed(false);
    setAnalysisData(null);
    
    try {
      const response = await fetch('http://localhost:8000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company, domain })
      });
      
      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }
      
      const data = await response.json();
      setAnalysisData(data);
      setHasRun(true);
      setIsLoading(false);
    } catch (error) {
      console.error("Backend fetch failed. Falling back to mock data.", error);
      setApiFailed(true);
      
      // Simulate processing delay for mock fallback
      setTimeout(() => {
        setHasRun(true);
        setIsLoading(false);
      }, 5000); // Increased slightly to show timeline animation
    }
  };

  const activeReconciled = analysisData ? analysisData.reconciled_profile : mockReconciled;
  const activeClaims = analysisData ? analysisData.fact_checker_claims : mockClaims;
  const activeModifiers = analysisData ? analysisData.modifiers : mockModifiers;
  const activeVerdict = analysisData ? analysisData.final_verdict : mockVerdict;

  return (
    <div className="dashboard-container">
      <Header isLoading={isLoading} apiFailed={apiFailed} />
      
      <div className="top-deck">
        <CompanyInput 
          company={company} 
          setCompany={setCompany} 
          domain={domain} 
          setDomain={setDomain} 
          onRunAnalysis={handleRunAnalysis}
          isLoading={isLoading}
          apiFailed={apiFailed}
        />
        <VerdictCard data={hasRun && !isLoading ? activeVerdict : null} />
      </div>

      <ExecutionTimeline isLoading={isLoading} hasRun={hasRun} />

      {/* Workflow Visualization is always visible, but animated state depends on isLoading */}
      <AgentWorkflow isLoading={isLoading} hasRun={hasRun} />
      
      {hasRun && !isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <EvidenceSources hasRun={hasRun} />
          <div className="data-deck">
            <ReconciledProfile data={activeReconciled} />
            <FactCheckerTable data={activeClaims} />
          </div>
          <ModifierTable data={activeModifiers} />
        </div>
      )}
    </div>
  );
}

export default App;
