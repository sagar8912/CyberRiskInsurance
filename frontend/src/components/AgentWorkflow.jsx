import React, { useState, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  MarkerType,
  Handle,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, CheckCircle, Target, Brain, FileText, Globe, Database, Building2, Search, Link, CheckSquare, Scale, BarChart } from 'lucide-react';

const CustomAgentNode = ({ data }) => {
  return (
    <div style={{
      background: '#FFFFFF',
      border: `1px solid ${data.color || '#E5E7EB'}`,
      borderRadius: '8px',
      padding: '16px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      boxShadow: data.isActive ? `0 0 0 2px ${data.color}, 0 8px 24px rgba(242, 106, 33, 0.15)` : '0 4px 12px rgba(0,0,0,0.04)',
      transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
      width: '320px',
      opacity: data.isFaded ? 0.4 : 1
    }}>
      <Handle type="target" position={Position.Top} style={{ background: data.color, width: '12px', height: '12px', border: '2px solid #FFFFFF' }} />
      
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
        <div style={{
          background: data.isDone ? (data.isSkipped ? 'rgba(148, 163, 184, 0.1)' : 'rgba(16, 185, 129, 0.1)') : (data.isError ? 'rgba(239, 68, 68, 0.1)' : `rgba(30, 64, 175, 0.05)`),
          padding: '12px',
          borderRadius: '6px',
          color: data.isDone ? (data.isSkipped ? '#64748B' : '#10B981') : (data.isError ? '#EF4444' : data.color),
          flexShrink: 0,
          fontSize: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '48px',
          height: '48px'
        }}>
          {data.isDone ? <CheckCircle size={24} /> : <span>{data.icon}</span>}
        </div>
        
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: '0.95rem', fontWeight: '800', color: '#1E293B', marginBottom: '4px' }}>{data.label}</div>
          <div style={{ fontSize: '0.75rem', color: '#64748B', lineHeight: '1.4' }}>
            {data.description}
          </div>
        </div>
      </div>

      {/* Live Interaction / Status Area */}
      <div style={{ 
        background: data.isDone ? (data.isError ? '#FEF2F2' : (data.isSkipped ? '#F1F5F9' : '#F0FDF4')) : (data.isActive ? '#FFF7ED' : '#F8FAFC'), 
        border: `1px solid ${data.isDone ? (data.isError ? '#FECACA' : (data.isSkipped ? '#E2E8F0' : '#BBF7D0')) : (data.isActive ? '#FED7AA' : '#E5E7EB')}`,
        padding: '8px 12px', 
        borderRadius: '6px', 
        fontSize: '0.75rem', 
        color: data.isDone ? (data.isError ? '#DC2626' : (data.isSkipped ? '#475569' : '#059669')) : (data.isActive ? '#C2410C' : '#94A3B8'), 
        fontWeight: '600',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        {data.isActive ? (
            <><div className="loader-small" style={{ width: '10px', height: '10px', borderWidth: '2px', borderColor: '#FED7AA', borderLeftColor: '#F26A21' }}></div> {data.activeMessage || "Processing..."}</>
        ) : (data.isDone ? (
            <>{data.isError ? "✖ " : (data.isSkipped ? "↷ " : "✔ ")}{data.doneMessage || "Completed"}</>
        ) : "Waiting for upstream input...")}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: data.color, width: '12px', height: '12px', border: '2px solid #FFFFFF' }} />
    </div>
  );
};

export default function AgentWorkflow({ isLoading, hasRun, currentStep = 0, collectorOutputs = null }) {
  const [internalStepId, setInternalStepId] = useState(0);

  useEffect(() => {
    if (hasRun) {
      setInternalStepId(7);
    } else if (isLoading || currentStep > 0) {
      setInternalStepId(currentStep);
    } else {
      setInternalStepId(0);
    }
  }, [isLoading, hasRun, currentStep]);

  const nodeTypes = useMemo(() => ({ agent: CustomAgentNode }), []);

  const getStatus = (stepRequired, baseColor, activeMessage, doneMessage, isError = false) => {
    const isDone = internalStepId > stepRequired || hasRun;
    const isActive = internalStepId === stepRequired && !hasRun;
    return {
      isActive,
      isDone,
      isError: isDone && isError,
      isFaded: internalStepId < stepRequired && !hasRun && internalStepId !== 0,
      color: isDone ? (isError ? '#EF4444' : '#10B981') : (isActive ? '#F26A21' : baseColor),
      activeMessage,
      doneMessage
    };
  };

  const getCollectorStatus = (collectorKey, baseColor, activeMessage, defaultDoneMessage, getCustomDoneMessageFn) => {
    const defaultStatus = getStatus(3, baseColor, activeMessage, defaultDoneMessage);
    if (!hasRun || !collectorOutputs) {
      if (defaultStatus.isDone) {
        return {
          ...defaultStatus,
          doneMessage: "Evidence harvested"
        };
      }
      return defaultStatus;
    }
    const report = collectorOutputs[collectorKey];
    if (!report) {
      return defaultStatus;
    }
    const status = report.status || 'success';
    if (status === 'skipped') {
      return {
        isActive: false,
        isDone: true,
        isError: false,
        isSkipped: true,
        isFaded: false,
        color: '#64748B', // Slate gray for skipped
        activeMessage,
        doneMessage: report.message || 'Bypassed (Non-SEC)'
      };
    } else if (status === 'error') {
      return {
        isActive: false,
        isDone: true,
        isError: true,
        isSkipped: false,
        isFaded: false,
        color: '#EF4444',
        activeMessage,
        doneMessage: report.message || 'Collection failed'
      };
    } else {
      return {
        isActive: false,
        isDone: true,
        isError: false,
        isSkipped: false,
        isFaded: false,
        color: '#10B981',
        activeMessage,
        doneMessage: getCustomDoneMessageFn ? getCustomDoneMessageFn(report.findings) : defaultDoneMessage
      };
    }
  };

  const initialNodes = [
    { id: '1', position: { x: 740, y: 0 }, type: 'agent', data: { label: 'Input Parameter', description: 'Company and domain targets', icon: <Target size={24} />, ...getStatus(1, '#94A3B8', 'Initializing System...', 'Input parameters validated') } },
    { id: '2', position: { x: 740, y: 150 }, type: 'agent', data: { label: 'Supervisor Agent', description: 'Validates target context before routing.', icon: <Brain size={24} />, ...getStatus(2, '#3B82F6', 'Routing to collectors...', 'Context verified. Dispatched agents.') } },
    
    // Parallel Collectors (Row 1: 3 nodes)
    { 
      id: '3', 
      position: { x: 360, y: 320 }, 
      type: 'agent', 
      data: { 
        label: 'SEC Collector', 
        description: 'Fetches financial evidence', 
        icon: <FileText size={24} />, 
        ...getCollectorStatus(
          'SECCollector', 
          '#3B82F6', 
          'Scraping EDGAR filings...', 
          'Revenue: $16B extracted',
          (findings) => {
            const rev = findings?.revenue;
            if (rev) return `Revenue: $${(rev/1e9).toFixed(1)}B extracted`;
            return 'Revenue and reports extracted';
          }
        ) 
      } 
    },
    { 
      id: '4', 
      position: { x: 740, y: 320 }, 
      type: 'agent', 
      data: { 
        label: 'Wikipedia Collector', 
        description: 'Fetches public profile', 
        icon: <Globe size={24} />, 
        ...getCollectorStatus(
          'Wikipedia', 
          '#3B82F6', 
          'Parsing infoboxes...', 
          'Subsidiaries: 1 found',
          (findings) => {
            const subs = findings?.subsidiaries || [];
            return `Subsidiaries: ${subs.length} found`;
          }
        ) 
      } 
    },
    { 
      id: '5', 
      position: { x: 1120, y: 320 }, 
      type: 'agent', 
      data: { 
        label: 'Wikidata Collector', 
        description: 'Fetches entity facts', 
        icon: <Database size={24} />, 
        ...getCollectorStatus(
          'Wikidata', 
          '#3B82F6', 
          'Querying SPARQL...', 
          'Countries of Op: 2',
          (findings) => {
            const countries = findings?.countries_of_operation || [];
            return `Countries of Op: ${countries.length}`;
          }
        ) 
      } 
    },
    
    // Parallel Collectors (Row 2: 2 nodes)
    { 
      id: '6', 
      position: { x: 550, y: 490 }, 
      type: 'agent', 
      data: { 
        label: 'DB Collector', 
        description: 'Fetches business metadata', 
        icon: <Building2 size={24} />, 
        ...getCollectorStatus(
          'DBCollector', 
          '#3B82F6', 
          'Mapping NAICS...', 
          'NAICS: 511210 (Software)',
          (findings) => {
            const naics = findings?.legal_form?.description || findings?.naics_code || 'Resolved';
            return `Type: ${naics}`;
          }
        ) 
      } 
    },
    { 
      id: '7', 
      position: { x: 930, y: 490 }, 
      type: 'agent', 
      data: { 
        label: 'Domain Scraper', 
        description: 'Checks website security signals', 
        icon: <Search size={24} />, 
        ...getCollectorStatus(
          'DomainScraper', 
          '#3B82F6', 
          'Analyzing headers...', 
          'Missing privacy policy (Flagged)',
          (findings) => {
            const hasPolicy = findings?.privacy_policy_published;
            return hasPolicy ? 'Privacy policy discovered' : 'Missing privacy policy (Flagged)';
          }
        ) 
      } 
    },
    
    // Post-Collection Processing Pipeline
    { id: '8', position: { x: 740, y: 680 }, type: 'agent', data: { label: 'Coordinator Agent', description: 'Merges raw evidence into normalized profile', icon: <Link size={24} />, ...getStatus(4, '#3B82F6', 'Reconciling conflicts...', 'Entity profile normalized.') } },
    { id: '9', position: { x: 740, y: 840 }, type: 'agent', data: { label: 'Fact Checker Agent', description: 'Verifies claims against evidence.', icon: <CheckSquare size={24} />, ...getStatus(5, '#3B82F6', 'Cross-referencing claims...', '4 verified, 1 unsupported') } },
    { id: '10', position: { x: 740, y: 1000 }, type: 'agent', data: { label: 'Underwriter Agent', description: 'Applies actuarial models', icon: <Scale size={24} />, ...getStatus(6, '#3B82F6', 'Calculating risk scores...', '14 modifiers applied') } },
    { id: '11', position: { x: 740, y: 1160 }, type: 'agent', data: { label: 'Final Verdict', description: 'Generates final risk output', icon: <BarChart size={24} />, ...getStatus(7, '#10B981', 'Generating...', 'Verdict complete') } },
  ];

  const getEdgeStyle = (stepRequired, isErrorEdge = false) => {
    const isActive = internalStepId === stepRequired && !hasRun;
    const isDone = internalStepId > stepRequired || hasRun;
    const color = isDone ? (isErrorEdge ? '#EF4444' : '#10B981') : (isActive ? '#F26A21' : '#CBD5E1');
    return {
      animated: isActive || (isLoading && internalStepId < 7),
      style: { 
        stroke: color, 
        strokeWidth: isActive ? 4 : (isDone ? 3 : 2), 
        transition: 'all 0.4s', 
        opacity: isActive || isDone ? 1 : 0.6,
        ...(isActive ? { strokeDasharray: '8, 12', animationDuration: '0.8s' } : {})
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: color }
    };
  };

  const initialEdges = [
    { id: 'e1-2', source: '1', target: '2', ...getEdgeStyle(2) },
    { id: 'e2-3', source: '2', target: '3', ...getEdgeStyle(3) },
    { id: 'e2-4', source: '2', target: '4', ...getEdgeStyle(3) },
    { id: 'e2-5', source: '2', target: '5', ...getEdgeStyle(3) },
    { id: 'e2-6', source: '2', target: '6', ...getEdgeStyle(3) },
    { id: 'e2-7', source: '2', target: '7', ...getEdgeStyle(3) },
    { id: 'e3-8', source: '3', target: '8', ...getEdgeStyle(4) },
    { id: 'e4-8', source: '4', target: '8', ...getEdgeStyle(4) },
    { id: 'e5-8', source: '5', target: '8', ...getEdgeStyle(4) },
    { id: 'e6-8', source: '6', target: '8', ...getEdgeStyle(4) },
    { id: 'e7-8', source: '7', target: '8', ...getEdgeStyle(4, true) }, // Propagate the red error edge
    { id: 'e8-9', source: '8', target: '9', ...getEdgeStyle(5) },
    { id: 'e9-10', source: '9', target: '10', ...getEdgeStyle(6) },
    { id: 'e10-11', source: '10', target: '11', ...getEdgeStyle(7) },
  ];

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ marginBottom: '16px', color: 'var(--text-primary)' }}><Network size={20} color="var(--accent-orange)" /> Live Multi-Agent Execution Graph</h2>
      <div style={{ height: '1100px', border: '1px solid var(--border-color)', borderRadius: '8px', overflow: 'hidden', background: '#F8FAFC' }}>
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1 }}
          colorMode="light"
          nodesDraggable={false}
          panOnDrag={false}
          zoomOnScroll={false}
        >
          <Background color="#CBD5E1" gap={20} size={1} />
        </ReactFlow>
      </div>

      {internalStepId > 0 && !hasRun && (
        <div style={{ marginTop: '24px', padding: '16px 20px', background: '#F8FAFC', borderRadius: '8px', borderLeft: '4px solid var(--accent-orange)' }}>
          <div style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--accent-orange)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Live Execution Detail</div>
          <div style={{ color: 'var(--text-primary)', fontSize: '0.95rem', lineHeight: '1.5' }}>
            {internalStepId === 1 && "Input submitted. Waiting to initialize..."}
            {internalStepId === 2 && "Validates company name and domain before routing to collectors."}
            {internalStepId === 3 && "Collect evidence from SEC, Wikipedia, Wikidata, DB, and website sources."}
            {internalStepId === 4 && "Coordinator Agent is aggregating and deduplicating raw scraped data into a single normalized entity profile."}
            {internalStepId === 5 && "Verifies claims against collected evidence."}
            {internalStepId === 6 && "Underwriter Agent is executing 13 actuarial risk models against the fact-checked profile to generate score modifiers."}
            {internalStepId === 7 && "Execution complete. Final Underwriting Verdict has been rendered based on aggregated agent consensus."}
          </div>
        </div>
      )}
    </div>
  );
}
