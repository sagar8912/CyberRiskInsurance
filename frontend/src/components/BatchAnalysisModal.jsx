import React, { useState, useRef } from 'react';
import { UploadCloud, X, Play, FileText, AlertTriangle, Loader2, Download, Square, Edit2, Trash2, ArrowLeft, FileOutput, Printer } from 'lucide-react';
import * as XLSX from 'xlsx';

import AgentResultCards from './AgentResultCards';
import ReconciledProfile from './ReconciledProfile';
import ModifierTable from './ModifierTable';
import VerdictCard from './VerdictCard';
import { downloadReportHtml, printReportPdf } from './EvidenceReportGenerator';

// Constants for alias matching
const COMPANY_ALIASES = ['company_name', 'company', 'companyname', 'name', 'insuredname', 'accountname', 'clientname', 'organization', 'entityname'];
const DOMAIN_ALIASES = ['domain_url', 'domain', 'website', 'url', 'company_url', 'webaddress', 'site', 'homepage'];

function normalizeHeader(h) {
  return h.toLowerCase().replace(/[\s_\-]/g, '');
}

function normalizeDomain(d) {
  if (!d) return '';
  let clean = d.trim().toLowerCase();
  clean = clean.replace(/^(https?:\/\/)?(www\.)?/, '');
  clean = clean.replace(/\/.*$/, ''); // remove paths
  return clean;
}

const getSummary = (rawData) => {
  if (!rawData) return {};
  const profile = rawData.reconciled_profile || {};
  const claims = rawData.fact_checker_claims || [];
  
  return {
    revenue: profile.financials?.revenue || 'N/A',
    country: profile.headquarters?.country || 'N/A',
    industry: profile.firmographics?.industry || 'N/A',
    naics: profile.firmographics?.naics_code || 'N/A',
    subsidiaries: profile.firmographics?.subsidiaries?.length || 0,
    privacy: profile.digital_presence?.privacy_policy_present ? 'Yes' : 'No',
    ecommerce: profile.digital_presence?.ecommerce_capabilities ? 'Yes' : 'No',
    customerType: profile.digital_presence?.primary_customer_type || 'N/A',
    sources: claims.length
  };
};

export default function BatchAnalysisModal({ isOpen, onClose }) {
  const [file, setFile] = useState(null);
  const [rawHeaders, setRawHeaders] = useState([]);
  const [rawDataState, setRawDataState] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCancelled, setIsCancelled] = useState(false);
  
  // Mapping state
  const [needsMapping, setNeedsMapping] = useState(false);
  const [selectedCompanyCol, setSelectedCompanyCol] = useState('');
  const [selectedDomainCol, setSelectedDomainCol] = useState('');

  // Editing state
  const [editingRowId, setEditingRowId] = useState(null);
  const [editDomainValue, setEditDomainValue] = useState('');

  // Detail View State
  const [viewingRowId, setViewingRowId] = useState(null);

  // Ref for cancellation
  const cancelRef = useRef(false);

  if (!isOpen) return null;

  const reset = () => {
    setFile(null);
    setRawHeaders([]);
    setRawDataState([]);
    setRows([]);
    setError(null);
    setIsProcessing(false);
    setIsCancelled(false);
    setNeedsMapping(false);
    setSelectedCompanyCol('');
    setSelectedDomainCol('');
    setViewingRowId(null);
    cancelRef.current = false;
  };

  const handleClose = () => {
    if (isProcessing) return; 
    reset();
    onClose();
  };

  const processData = (data, compCol, domCol) => {
    const newRows = data.map((r, i) => {
      const company = r[compCol] ? String(r[compCol]).trim() : '';
      const rawDomain = r[domCol] ? String(r[domCol]).trim() : '';
      const domain = normalizeDomain(rawDomain);
      
      let status = 'Ready';
      let errorMsg = '';
      
      if (!company) {
        status = 'Invalid';
        errorMsg = 'Missing company';
      } else if (!domain) {
        status = 'Missing Domain';
        errorMsg = 'Needs domain / search required';
      }

      return {
        id: i,
        company,
        domain,
        status, 
        errorMsg,
        confidence: null,
        verdict: null,
        originalRow: r,
        rawData: null,
        executionTime: null
      };
    });
    setRows(newRows);
  };

  const handleFileUpload = (e) => {
    const uploadedFile = e.target.files[0];
    if (!uploadedFile) return;

    const name = uploadedFile.name.toLowerCase();
    
    if (name.endsWith('.pdf') || name.endsWith('.doc') || name.endsWith('.docx')) {
      setFile(uploadedFile);
      setError('Document uploaded. Extracting company/domain from documents requires backend extraction support.');
      setRows([]);
      return;
    }

    if (!name.endsWith('.csv') && !name.endsWith('.xlsx') && !name.endsWith('.xls')) {
      setError('Unsupported file type. Please upload CSV, XLSX, or XLS.');
      return;
    }

    setFile(uploadedFile);
    setError(null);
    setNeedsMapping(false);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = event.target.result;
        const workbook = XLSX.read(data, { type: 'binary' });
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        const json = XLSX.utils.sheet_to_json(worksheet, { defval: '' });
        if (json.length === 0) {
          setError('File is empty.');
          return;
        }

        const headers = Object.keys(json[0]);
        setRawHeaders(headers);
        setRawDataState(json);

        let compCol = headers.find(h => COMPANY_ALIASES.includes(normalizeHeader(h)));
        let domCol = headers.find(h => DOMAIN_ALIASES.includes(normalizeHeader(h)));

        if (!compCol || !domCol) {
          setNeedsMapping(true);
          if (!compCol) {
            setError('Could not detect company column. Please map a column.');
          } else if (!domCol) {
            setError('Domain column not detected. You can manually map a domain column.');
            setSelectedCompanyCol(compCol);
          }
          return;
        }

        processData(json, compCol, domCol);
      } catch (err) {
        console.error(err);
        setError('Error reading file. Ensure it is a valid CSV or Excel file.');
      }
    };
    reader.readAsBinaryString(uploadedFile);
  };

  const applyMapping = () => {
    if (!selectedCompanyCol) {
      setError('Company column must be selected.');
      return;
    }
    setError(null);
    setNeedsMapping(false);
    processData(rawDataState, selectedCompanyCol, selectedDomainCol);
  };

  const startEditDomain = (id, currentDomain) => {
    setEditingRowId(id);
    setEditDomainValue(currentDomain);
  };

  const saveEditDomain = (id) => {
    setRows(prev => prev.map(r => {
      if (r.id === id) {
        const newDomain = normalizeDomain(editDomainValue);
        let status = 'Ready';
        let errorMsg = '';
        if (!r.company) {
          status = 'Invalid';
          errorMsg = 'Missing company';
        } else if (!newDomain) {
          status = 'Missing Domain';
          errorMsg = 'Needs domain / search required';
        }
        return { ...r, domain: newDomain, status, errorMsg };
      }
      return r;
    }));
    setEditingRowId(null);
  };

  const removeRow = (id) => {
    setRows(prev => prev.filter(r => r.id !== id));
  };

  const runBatch = async () => {
    setIsProcessing(true);
    setIsCancelled(false);
    cancelRef.current = false;

    setRows(prev => prev.map(r => 
      ['Ready', 'Completed', 'Failed'].includes(r.status) ? { ...r, status: 'Pending' } : r
    ));

    for (let i = 0; i < rows.length; i++) {
      if (cancelRef.current) break; 

      const row = rows[i];
      if (row.status === 'Invalid' || row.status === 'Missing Domain') continue;

      setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Running', errorMsg: '' } : r));

      const startTime = Date.now();
      const runId = 'batch_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      const apiUrl = (import.meta.env.VITE_API_URL !== undefined && import.meta.env.VITE_API_URL !== '')
        ? import.meta.env.VITE_API_URL
        : (import.meta.env.PROD ? '' : 'http://localhost:8000');

      let sseActive = true;
      let lastEventTime = Date.now();
      const abortController = new AbortController();

      const watchdog = setInterval(() => {
        if (sseActive && Date.now() - lastEventTime > 6000) {
          console.warn(`[Batch Resiliency] SSE watchdog timed out for ${row.company}. Aborting stream and falling back to polling...`);
          sseActive = false;
          abortController.abort();
        }
      }, 2000);

      try {
        const response = await fetch(`${apiUrl}/api/analyze/stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ company: row.company, domain: row.domain, run_id: runId }),
          signal: abortController.signal
        });

        if (!response.ok) throw new Error(`API Error: ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let finalData = null;
        let hasError = false;
        let errorStr = '';

        while (sseActive) {
          if (cancelRef.current) {
            reader.cancel();
            break;
          }
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
                  if (event.type === 'result') {
                    finalData = event.data;
                  } else if (event.type === 'error') {
                    hasError = true;
                    errorStr = event.message;
                  }
                } catch (e) {
                  // ignore
                }
              }
            }
          }
        }
        
        clearInterval(watchdog);

        if (!sseActive && !cancelRef.current) {
          throw new Error("SSE aborted by watchdog. Initiating fallback polling...");
        }

        const executionTime = ((Date.now() - startTime) / 1000).toFixed(1);

        if (cancelRef.current) {
          setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Pending' } : r));
          break;
        }

        if (hasError) {
          setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Failed', errorMsg: errorStr, executionTime } : r));
        } else if (finalData) {
          const verdict = finalData.final_verdict?.verdict || 'Unknown';
          const confidence = finalData.final_verdict?.confidence_score || 0;
          setRows(prev => prev.map(r => r.id === row.id ? { 
            ...r, status: 'Completed', verdict, confidence, errorMsg: '', rawData: finalData, executionTime 
          } : r));
        } else {
          setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Failed', errorMsg: 'No final data received.', executionTime } : r));
        }

      } catch (err) {
        clearInterval(watchdog);
        if (cancelRef.current) {
          setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Pending' } : r));
          break;
        }
        console.warn(`[Batch Resiliency] SSE failed for ${row.company}. Switching to polling /api/run-status/${runId} every 2s...`, err);
        let polledComplete = false;
        let attempts = 0;
        while (attempts < 60 && !cancelRef.current) {
          attempts++;
          try {
            const res = await fetch(`${apiUrl}/api/run-status/${runId}`);
            if (res.ok) {
              const statusData = await res.json();
              const executionTime = ((Date.now() - startTime) / 1000).toFixed(1);
              if (statusData.status === 'completed' && statusData.result) {
                console.info("[Polling] Stopped because run completed");
                const finalData = statusData.result;
                const verdict = finalData.final_verdict?.verdict || 'Unknown';
                const confidence = finalData.final_verdict?.confidence_score || 0;
                setRows(prev => prev.map(r => r.id === row.id ? {
                  ...r, status: 'Completed', verdict, confidence, errorMsg: '', rawData: finalData, executionTime
                } : r));
                polledComplete = true;
                break;
              } else if (statusData.status === 'failed') {
                setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Failed', errorMsg: statusData.error || 'Workflow failed', executionTime } : r));
                polledComplete = true;
                break;
              }
            } else if (res.status === 404 && attempts > 5) {
              break;
            }
          } catch (pErr) {
            console.error("[Batch Polling] Error checking run status:", pErr);
          }
          await new Promise(r => setTimeout(r, 2000));
        }
        if (!polledComplete && !cancelRef.current) {
          const executionTime = ((Date.now() - startTime) / 1000).toFixed(1);
          setRows(prev => prev.map(r => r.id === row.id ? { ...r, status: 'Failed', errorMsg: "Polling fallback timeout.", executionTime } : r));
        }
      }
    }

    setIsProcessing(false);
    if (cancelRef.current) {
      setIsCancelled(true);
    }
  };

  const cancelBatch = () => {
    cancelRef.current = true;
  };

  const exportCSV = () => {
    const ws = XLSX.utils.json_to_sheet(rows.map(r => {
      const summary = getSummary(r.rawData);
      return {
        Company: r.company,
        Domain: r.domain,
        Status: r.status,
        Revenue: summary.revenue,
        Country: summary.country,
        Industry: summary.industry,
        NAICS: summary.naics,
        'Customer Type': summary.customerType,
        'Privacy Policy': summary.privacy,
        Ecommerce: summary.ecommerce,
        Subsidiaries: summary.subsidiaries,
        'Overall Verdict': r.verdict,
        Confidence: r.confidence,
        'Execution Time': r.executionTime ? `${r.executionTime}s` : '',
        Error: r.errorMsg
      };
    }));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, "BatchResults.csv");
  };

  const exportJSON = () => {
    const dataStr = JSON.stringify(rows.map(r => ({
      company: r.company,
      domain: r.domain,
      status: r.status,
      verdict: r.verdict,
      confidence: r.confidence,
      executionTime: r.executionTime,
      errorMsg: r.errorMsg,
      rawData: r.rawData
    })), null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'BatchResults.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  // RENDER DETAIL VIEW
  if (viewingRowId !== null) {
    const row = rows.find(r => r.id === viewingRowId);
    if (!row || !row.rawData) return null;
    
    const activeReconciled = row.rawData.reconciled_profile;
    const activeClaims = row.rawData.fact_checker_claims;
    const activeModifiers = row.rawData.modifiers;
    const activeVerdict = row.rawData.final_verdict;
    const targetEntity = row.rawData.target_entity;

    return (
      <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: '#F8FAFC', zIndex: 100, display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <div style={{ padding: '20px 24px', background: '#FFFFFF', borderBottom: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, zIndex: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button onClick={() => setViewingRowId(null)} style={{ background: '#F1F5F9', border: '1px solid #E2E8F0', padding: '8px 12px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: '600', color: '#475569' }}>
              <ArrowLeft size={16} /> Back to Batch
            </button>
            <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#0F172A', display: 'flex', alignItems: 'center', gap: '12px' }}>
              {row.company} 
              <span style={{ fontSize: '0.8rem', background: '#E2E8F0', padding: '2px 8px', borderRadius: '12px', fontWeight: '500' }}>{row.domain}</span>
            </h2>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
             <button onClick={() => downloadReportHtml(activeModifiers, targetEntity?.name, activeVerdict)} style={{ background: '#FFF', border: '1px solid #CBD5E1', padding: '8px 16px', borderRadius: '6px', color: '#0F172A', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
               <FileOutput size={16} /> Download HTML
             </button>
             <button onClick={() => printReportPdf(activeModifiers, targetEntity?.name, activeVerdict)} style={{ background: 'var(--accent-orange)', border: 'none', padding: '8px 16px', borderRadius: '6px', color: '#FFF', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
               <Printer size={16} /> Download PDF
             </button>
          </div>
        </div>
        <div style={{ padding: '32px', maxWidth: '1200px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '32px' }}>
            <AgentResultCards 
              reconciledProfile={activeReconciled}
              claims={activeClaims}
              modifiers={activeModifiers}
              verdict={activeVerdict}
            />
            <ReconciledProfile data={activeReconciled} claims={activeClaims} verdict={activeVerdict} />
            <ModifierTable data={activeModifiers} isAdminMode={false} verdictData={{ target_entity: targetEntity, final_verdict: activeVerdict }} />
            <VerdictCard data={activeVerdict} modifiers={activeModifiers} claims={activeClaims} />
        </div>
      </div>
    );
  }

  // RENDER BATCH MODAL TABLE
  const validRowCount = rows.filter(r => r.status !== 'Invalid' && r.status !== 'Missing Domain').length;
  const showBatchWarning = validRowCount > 10;
  const isFinished = rows.length > 0 && !isProcessing && !needsMapping && rows.every(r => ['Completed', 'Failed', 'Invalid', 'Missing Domain'].includes(r.status)) && !isCancelled;

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(15, 23, 42, 0.7)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', backdropFilter: 'blur(4px)' }}>
      <div style={{ background: '#FFFFFF', borderRadius: '12px', width: '95%', maxWidth: '1400px', maxHeight: '90vh', overflowY: 'hidden', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)', border: '1px solid #E2E8F0', display: 'flex', flexDirection: 'column' }}>
        
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid #E2E8F0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#FFFFFF' }}>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px', fontSize: '1.2rem', color: '#0F172A' }}>
            <UploadCloud size={20} color="var(--accent-orange)" /> Batch Analysis
          </h2>
          <button onClick={handleClose} disabled={isProcessing} style={{ background: 'transparent', border: 'none', cursor: isProcessing ? 'not-allowed' : 'pointer', padding: '4px', display: 'flex', alignItems: 'center', color: '#64748B', opacity: isProcessing ? 0.5 : 1 }}>
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto' }}>
          {!file && (
            <div style={{ border: '2px dashed #CBD5E1', borderRadius: '8px', padding: '48px', textAlign: 'center', background: '#F8FAFC', cursor: 'pointer' }}
                 onClick={() => document.getElementById('csv-upload').click()}>
              <FileText size={48} color="#94A3B8" style={{ marginBottom: '16px' }} />
              <div style={{ color: '#0F172A', fontWeight: '600', fontSize: '1.1rem', marginBottom: '8px' }}>Click to upload file</div>
              <div style={{ color: '#64748B', fontSize: '0.85rem' }}>Supports .csv, .xlsx, .xls</div>
              <input id="csv-upload" type="file" accept=".csv, .xlsx, .xls, .pdf, .doc, .docx" style={{ display: 'none' }} onChange={handleFileUpload} />
            </div>
          )}

          {error && (
            <div style={{ padding: '12px', background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '6px', color: '#DC2626', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: '600' }}>
              <AlertTriangle size={16} /> {error}
              {file && !needsMapping && <button onClick={reset} style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: '#DC2626', textDecoration: 'underline', cursor: 'pointer', fontSize: '0.8rem' }}>Try Another File</button>}
            </div>
          )}

          {needsMapping && (
            <div style={{ background: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '8px', padding: '16px' }}>
              <h3 style={{ fontSize: '1rem', marginTop: 0, marginBottom: '16px', color: '#0F172A' }}>Manual Column Mapping</h3>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: '#475569', marginBottom: '4px' }}>Company Column *</label>
                  <select value={selectedCompanyCol} onChange={e => setSelectedCompanyCol(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #CBD5E1' }}>
                    <option value="">-- Select --</option>
                    {rawHeaders.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: '#475569', marginBottom: '4px' }}>Domain Column (Optional)</label>
                  <select value={selectedDomainCol} onChange={e => setSelectedDomainCol(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #CBD5E1' }}>
                    <option value="">-- Select --</option>
                    {rawHeaders.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
                <button onClick={applyMapping} style={{ background: 'var(--accent-orange)', color: '#FFF', border: 'none', padding: '8px 16px', borderRadius: '4px', fontWeight: '600', cursor: 'pointer', height: '35px' }}>Apply</button>
              </div>
            </div>
          )}

          {file && !needsMapping && rows.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#F8FAFC', padding: '12px 16px', borderRadius: '6px', border: '1px solid #E2E8F0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <FileText size={20} color="#3B82F6" />
                  <span style={{ fontWeight: '600', color: '#0F172A' }}>{file.name}</span>
                  <span style={{ fontSize: '0.8rem', color: '#64748B', background: '#E2E8F0', padding: '2px 8px', borderRadius: '12px' }}>{rows.length} rows</span>
                </div>
                {!isProcessing && <button onClick={reset} style={{ background: 'transparent', border: 'none', color: '#64748B', cursor: 'pointer', fontSize: '0.8rem', fontWeight: '500' }}>Change File</button>}
              </div>

              {showBatchWarning && (
                <div style={{ background: '#FFF7ED', border: '1px solid #FFEDD5', color: '#C2410C', padding: '12px', borderRadius: '6px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={16} /> Large batch may take time because each company is processed one by one.
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ fontSize: '0.9rem', color: '#475569', margin: 0 }}>Batch Results</h3>
                {(isFinished || rows.some(r => r.status === 'Completed')) && (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={exportCSV} style={{ background: '#F1F5F9', border: '1px solid #E2E8F0', padding: '4px 12px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600', color: '#475569', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                      <Download size={14} /> Export CSV
                    </button>
                    <button onClick={exportJSON} style={{ background: '#F1F5F9', border: '1px solid #E2E8F0', padding: '4px 12px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600', color: '#475569', display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer' }}>
                      <FileText size={14} /> Export JSON
                    </button>
                  </div>
                )}
              </div>
              
              <div style={{ width: '100%', overflowX: 'auto', border: '1px solid #E2E8F0', borderRadius: '6px', flex: 1 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left', minWidth: '1200px' }}>
                  <thead style={{ background: '#F1F5F9', position: 'sticky', top: 0, zIndex: 5 }}>
                    <tr>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600', minWidth: '150px' }}>Company</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600', minWidth: '150px' }}>Domain</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600', minWidth: '100px' }}>Status</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600', minWidth: '120px' }}>Final Verdict</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600' }}>Revenue</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600' }}>Country</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600' }}>Industry</th>
                      <th style={{ padding: '12px', borderBottom: '1px solid #E2E8F0', color: '#64748B', fontWeight: '600', minWidth: '220px' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(row => {
                      const summary = getSummary(row.rawData);
                      return (
                      <tr key={row.id} style={{ borderBottom: '1px solid #F1F5F9', background: row.status === 'Running' ? '#F0FDF4' : 'transparent' }}>
                        <td style={{ padding: '12px', color: '#334155', fontWeight: '500' }}>{row.company}</td>
                        <td style={{ padding: '12px', color: '#334155' }}>
                          {editingRowId === row.id ? (
                            <div style={{ display: 'flex', gap: '4px' }}>
                              <input 
                                autoFocus
                                value={editDomainValue} 
                                onChange={e => setEditDomainValue(e.target.value)}
                                style={{ width: '120px', padding: '4px', border: '1px solid #CBD5E1', borderRadius: '4px', fontSize: '0.8rem' }}
                                onKeyDown={e => { if (e.key === 'Enter') saveEditDomain(row.id); }}
                              />
                              <button onClick={() => saveEditDomain(row.id)} style={{ background: '#3B82F6', color: '#FFF', border: 'none', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '0.7rem' }}>Save</button>
                            </div>
                          ) : (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {row.domain || <span style={{ color: '#94A3B8', fontStyle: 'italic' }}>Blank</span>}
                              {!isProcessing && !isFinished && (
                                <button onClick={() => startEditDomain(row.id, row.domain)} style={{ background: 'transparent', border: 'none', color: '#94A3B8', cursor: 'pointer', padding: 0 }} title="Edit domain">
                                  <Edit2 size={12} />
                                </button>
                              )}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '12px' }}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span style={{ 
                              padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 'bold', width: 'fit-content',
                              background: row.status === 'Completed' ? '#ECFDF5' : row.status === 'Failed' || row.status === 'Invalid' ? '#FEF2F2' : row.status === 'Missing Domain' ? '#FFFBEB' : row.status === 'Running' ? '#EFF6FF' : '#F1F5F9',
                              color: row.status === 'Completed' ? '#059669' : row.status === 'Failed' || row.status === 'Invalid' ? '#DC2626' : row.status === 'Missing Domain' ? '#D97706' : row.status === 'Running' ? '#2563EB' : '#64748B',
                              display: 'inline-flex', alignItems: 'center', gap: '4px'
                            }}>
                              {row.status === 'Running' && <Loader2 size={10} className="spin" />}
                              {row.status}
                            </span>
                            {row.executionTime && <span style={{ fontSize: '0.7rem', color: '#94A3B8' }}>{row.executionTime}s</span>}
                          </div>
                        </td>
                        <td style={{ padding: '12px' }}>
                          {row.status === 'Completed' && (
                            <div>
                              <div style={{ color: '#0F172A', fontWeight: '600' }}>{row.verdict}</div>
                              <div style={{ color: '#64748B', fontSize: '0.75rem' }}>{row.confidence}% Conf.</div>
                            </div>
                          )}
                          {row.errorMsg && <div style={{ color: '#DC2626', fontSize: '0.75rem', maxWidth: '200px' }}>{row.errorMsg}</div>}
                        </td>
                        <td style={{ padding: '12px', color: '#475569' }}>{summary.revenue || '-'}</td>
                        <td style={{ padding: '12px', color: '#475569' }}>{summary.country || '-'}</td>
                        <td style={{ padding: '12px', color: '#475569' }}>{summary.industry || '-'}</td>
                        <td style={{ padding: '12px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {row.status === 'Completed' && row.rawData && (
                              <>
                                <button onClick={() => setViewingRowId(row.id)} style={{ background: '#F1F5F9', border: '1px solid #E2E8F0', color: '#0F172A', padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', cursor: 'pointer', fontWeight: '500' }}>View Full Result</button>
                                <button onClick={() => downloadReportHtml(row.rawData.modifiers, row.rawData.target_entity?.name, row.rawData.final_verdict)} title="Download HTML" style={{ background: 'transparent', border: 'none', color: '#3B82F6', cursor: 'pointer', padding: '2px' }}><FileOutput size={16} /></button>
                                <button onClick={() => printReportPdf(row.rawData.modifiers, row.rawData.target_entity?.name, row.rawData.final_verdict)} title="Download PDF" style={{ background: 'transparent', border: 'none', color: '#D97706', cursor: 'pointer', padding: '2px' }}><Printer size={16} /></button>
                              </>
                            )}
                            {!isProcessing && !isFinished && (
                              <button onClick={() => removeRow(row.id)} style={{ background: 'transparent', border: 'none', color: '#EF4444', cursor: 'pointer', padding: '4px', marginLeft: 'auto' }} title="Remove row">
                                <Trash2 size={16} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )})}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ padding: '16px 24px', borderTop: '1px solid #E2E8F0', background: '#F8FAFC', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          {!isProcessing && (
             <button onClick={handleClose} style={{ background: 'transparent', border: '1px solid #CBD5E1', padding: '8px 16px', borderRadius: '6px', color: '#475569', fontWeight: '600', cursor: 'pointer' }}>
               {isFinished ? 'Close' : 'Cancel'}
             </button>
          )}
          
          {file && !needsMapping && rows.length > 0 && !isFinished && (
            isProcessing ? (
              <button 
                onClick={cancelBatch}
                style={{ 
                  background: '#EF4444', 
                  color: '#FFF', border: 'none', padding: '8px 16px', borderRadius: '6px', 
                  fontWeight: '600', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: '8px'
                }}
              >
                <Square size={16} /> Stop Batch
              </button>
            ) : (
              <button 
                onClick={runBatch}
                disabled={validRowCount === 0}
                style={{ 
                  background: validRowCount > 0 ? 'var(--accent-orange)' : '#94A3B8', 
                  color: '#FFF', border: 'none', padding: '8px 16px', borderRadius: '6px', 
                  fontWeight: '600', cursor: validRowCount > 0 ? 'pointer' : 'not-allowed',
                  display: 'flex', alignItems: 'center', gap: '8px'
                }}
              >
                <Play size={16} /> Run Batch Analysis ({validRowCount})
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}
