import React, { useState, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  MarkerType,
  Handle,
  Position
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, Database, Globe, Building2, BookOpen, ShieldCheck, Scale, Cpu, Play, Gavel } from 'lucide-react';

const CustomAgentNode = ({ data }) => {
  return (
    <div style={{
      background: 'rgba(16, 23, 42, 0.95)',
      border: `1px solid ${data.color || 'var(--border-color)'}`,
      borderRadius: '12px',
      padding: '16px',
      display: 'flex',
      alignItems: 'flex-start',
      gap: '14px',
      boxShadow: data.isActive ? `0 0 24px ${data.color}` : '0 6px 16px rgba(0,0,0,0.4)',
      transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
      width: '300px',
      opacity: data.isFaded ? 0.3 : 1
    }}>
      <Handle type="target" position={Position.Top} style={{ background: data.color, width: '12px', height: '12px' }} />
      <div style={{
        background: `rgba(${data.rgb}, 0.15)`,
        padding: '12px',
        borderRadius: '10px',
        color: data.color,
        flexShrink: 0
      }}>
        {data.icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '0.95rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '4px' }}>{data.label}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.3', marginBottom: '8px' }}>
          {data.description}
        </div>
        <div style={{ display: 'inline-flex', alignItems: 'center', background: data.isActive ? `rgba(${data.rgb}, 0.1)` : 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '4px', fontSize: '0.65rem', textTransform: 'uppercase', color: data.isActive ? data.color : 'var(--text-secondary)', fontWeight: '600', letterSpacing: '0.05em' }}>
          {data.isActive ? (
             <><div className="loader-small" style={{ width: '10px', height: '10px', borderWidth: '1px', marginRight: '6px', borderColor: `rgba(${data.rgb}, 0.3)`, borderLeftColor: data.color }}></div> Running</>
          ) : (data.isDone ? 'Completed' : 'Waiting')}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: data.color, width: '12px', height: '12px' }} />
    </div>
  );
};

export default function AgentWorkflow({ isLoading, hasRun }) {
  const [activeStepId, setActiveStepId] = useState(0);

  useEffect(() => {
    if (isLoading) {
      setActiveStepId(1);
      const interval = setInterval(() => {
        setActiveStepId(prev => (prev < 6 ? prev + 1 : prev));
      }, 800);
      return () => clearInterval(interval);
    } else if (hasRun) {
      setActiveStepId(7); // All complete
    } else {
      setActiveStepId(0);
    }
  }, [isLoading, hasRun]);

  const nodeTypes = useMemo(() => ({ agent: CustomAgentNode }), []);

  const getStatus = (stepRequired) => {
    return {
      isActive: activeStepId === stepRequired,
      isDone: activeStepId > stepRequired || hasRun,
      isFaded: activeStepId < stepRequired && !hasRun && activeStepId !== 0
    };
  };

  const initialNodes = [
    { id: '1', position: { x: 700, y: 0 }, type: 'agent', data: { label: 'Input', description: 'Company and domain submitted', icon: <Play size={24} />, color: 'var(--accent-slate)', rgb: '100, 116, 139', ...getStatus(1) } },
    { id: '2', position: { x: 700, y: 110 }, type: 'agent', data: { label: 'Supervisor Agent', description: 'Validates input and prepares workflow state', icon: <Cpu size={24} />, color: 'var(--accent-cyan)', rgb: '34, 211, 238', ...getStatus(1) } },
    
    // Parallel Collectors (tightened horizontal spacing)
    { id: '3', position: { x: 100, y: 220 }, type: 'agent', data: { label: 'SEC Collector', description: 'Fetches filing and financial evidence', icon: <Building2 size={24} />, color: 'var(--accent-blue)', rgb: '59, 130, 246', ...getStatus(2) } },
    { id: '4', position: { x: 400, y: 220 }, type: 'agent', data: { label: 'Wikipedia Collector', description: 'Fetches public company profile', icon: <BookOpen size={24} />, color: 'var(--accent-blue)', rgb: '59, 130, 246', ...getStatus(2) } },
    { id: '5', position: { x: 700, y: 220 }, type: 'agent', data: { label: 'Wikidata Collector', description: 'Fetches structured entity facts', icon: <Database size={24} />, color: 'var(--accent-blue)', rgb: '59, 130, 246', ...getStatus(2) } },
    { id: '6', position: { x: 1000, y: 220 }, type: 'agent', data: { label: 'DB Collector', description: 'Fetches business metadata', icon: <Database size={24} />, color: 'var(--accent-blue)', rgb: '59, 130, 246', ...getStatus(2) } },
    { id: '7', position: { x: 1300, y: 220 }, type: 'agent', data: { label: 'Domain Scraper', description: 'Checks domain, HTTPS, privacy/ecommerce signals', icon: <Globe size={24} />, color: 'var(--accent-blue)', rgb: '59, 130, 246', ...getStatus(2) } },
    
    { id: '8', position: { x: 700, y: 330 }, type: 'agent', data: { label: 'Coordinator Agent', description: 'Merges and reconciles collector evidence', icon: <Network size={24} />, color: 'var(--accent-teal)', rgb: '20, 184, 166', ...getStatus(3) } },
    { id: '9', position: { x: 700, y: 440 }, type: 'agent', data: { label: 'Fact Checker Agent', description: 'Corroborates key underwriting claims', icon: <ShieldCheck size={24} />, color: 'var(--accent-amber)', rgb: '245, 158, 11', ...getStatus(4) } },
    { id: '10', position: { x: 700, y: 550 }, type: 'agent', data: { label: 'Underwriter Agent', description: 'Applies 13 modifier rules', icon: <Scale size={24} />, color: 'var(--accent-purple)', rgb: '139, 92, 246', ...getStatus(5) } },
    { id: '11', position: { x: 700, y: 660 }, type: 'agent', data: { label: 'Final Verdict', description: 'Generates risk category and escalation flag', icon: <Gavel size={24} />, color: 'var(--accent-emerald)', rgb: '16, 185, 129', ...getStatus(6) } },
  ];

  const getEdgeStyle = (stepRequired) => {
    const isActive = activeStepId === stepRequired;
    const isDone = activeStepId > stepRequired || hasRun;
    const color = isActive ? 'var(--accent-cyan)' : (isDone ? 'rgba(34, 211, 238, 0.4)' : 'rgba(255,255,255,0.05)');
    return {
      animated: isActive || (isLoading && activeStepId < 6),
      style: { stroke: color, strokeWidth: isActive ? 3 : 2, transition: 'all 0.4s' },
      markerEnd: { type: MarkerType.ArrowClosed, color: color }
    };
  };

  const initialEdges = [
    { id: 'e1-2', source: '1', target: '2', ...getEdgeStyle(1) },
    { id: 'e2-3', source: '2', target: '3', ...getEdgeStyle(2) },
    { id: 'e2-4', source: '2', target: '4', ...getEdgeStyle(2) },
    { id: 'e2-5', source: '2', target: '5', ...getEdgeStyle(2) },
    { id: 'e2-6', source: '2', target: '6', ...getEdgeStyle(2) },
    { id: 'e2-7', source: '2', target: '7', ...getEdgeStyle(2) },
    { id: 'e3-8', source: '3', target: '8', ...getEdgeStyle(3) },
    { id: 'e4-8', source: '4', target: '8', ...getEdgeStyle(3) },
    { id: 'e5-8', source: '5', target: '8', ...getEdgeStyle(3) },
    { id: 'e6-8', source: '6', target: '8', ...getEdgeStyle(3) },
    { id: 'e7-8', source: '7', target: '8', ...getEdgeStyle(3) },
    { id: 'e8-9', source: '8', target: '9', ...getEdgeStyle(4) },
    { id: 'e9-10', source: '9', target: '10', ...getEdgeStyle(5) },
    { id: 'e10-11', source: '10', target: '11', ...getEdgeStyle(6) },
  ];

  return (
    <div className="glass-panel" style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ marginBottom: '16px' }}><Network size={20} color="var(--accent-cyan)" /> Live Multi-Agent Execution Graph</h2>
      <div style={{ flex: 1, border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', overflow: 'hidden', background: '#05070a' }}>
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1 }}
          colorMode="dark"
          nodesDraggable={false}
          panOnDrag={false}
          zoomOnScroll={false}
        >
          <Background color="rgba(34, 211, 238, 0.03)" gap={20} size={1} />
        </ReactFlow>
      </div>
    </div>
  );
}
