import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  BackgroundVariant,
  MarkerType,
  type Node,
  type Edge,
  type Connection,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Network, Play, Layers, ChevronDown, ChevronUp, Activity, GitBranch, RotateCcw, Download, ChevronRight } from 'lucide-react';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';
import { hierarchyApi } from '../../services/hierarchyApi';
import { apiClient } from '../../services/apiClient';
import { FilterNodeCard } from './FilterNodeCard';
import { FilterEditorPanel } from '../hierarchy/FilterEditorPanel';
import { SturixLogo } from '../ui/SturixLogo';

interface HierarchyBuilderProps {
  clientId: string;
  socket: any;
}

interface FilterNodeData {
  id: string;
  parentId: string | null;
  column: string;
  value: string;
  operator: string;
}

let nodeIdCounter = 1;
const genId = () => `fnode_${Date.now()}_${nodeIdCounter++}`;

const NODE_TYPES = { filterNode: FilterNodeCard };

// Build RF nodes/edges from filterNodes tree
function buildFlowGraph(
  filterNodes: FilterNodeData[],
  selectedNodeId: string | null,
  onAddChild: (parentId: string, parentLabel: string) => void
): { nodes: Node[], edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Root node
  nodes.push({
    id: 'root',
    type: 'filterNode',
    position: { x: 300, y: 40 },
    data: {
      label: 'Full Dataset',
      filterCol: '',
      filterVal: '',
      rowCount: 0,
      uniqueCompounds: 0,
      isRoot: true,
      isLeaf: filterNodes.filter(n => n.parentId === 'root').length === 0,
      level: 0,
      onAddChild: () => onAddChild('root', 'Root'),
    },
    selected: selectedNodeId === 'root',
  });

  // Layout nodes by level using BFS
  const levelMap: Record<string, number> = { root: 0 };
  const childMap: Record<string, FilterNodeData[]> = { root: [] };
  filterNodes.forEach(fn => {
    childMap[fn.id] = [];
    const parentId = fn.parentId || 'root';
    if (!childMap[parentId]) childMap[parentId] = [];
    childMap[parentId].push(fn);
  });

  // BFS to assign positions
  const queue: { id: string; depth: number; siblingIndex: number; siblingCount: number }[] = [
    { id: 'root', depth: 0, siblingIndex: 0, siblingCount: 1 }
  ];
  const posMap: Record<string, { x: number; y: number }> = { root: { x: 300, y: 40 } };

  while (queue.length) {
    const { id, depth } = queue.shift()!;
    const children = childMap[id] || [];
    const spacing = Math.max(240, 600 / (children.length + 1));
    const totalWidth = (children.length - 1) * spacing;
    const parentX = posMap[id]?.x ?? 300;

    children.forEach((child, i) => {
      const x = parentX - totalWidth / 2 + i * spacing;
      const y = 40 + (depth + 1) * 180;
      posMap[child.id] = { x, y };
      levelMap[child.id] = depth + 1;
      queue.push({ id: child.id, depth: depth + 1, siblingIndex: i, siblingCount: children.length });

      const hasChildren = (childMap[child.id] || []).length > 0;
      nodes.push({
        id: child.id,
        type: 'filterNode',
        position: { x, y },
        data: {
          label: `${child.column} = ${child.value}`,
          filterCol: child.column,
          filterVal: child.value,
          rowCount: 0,
          uniqueCompounds: 0,
          isRoot: false,
          isLeaf: !hasChildren,
          level: depth + 1,
          onAddChild: () => onAddChild(child.id, `${child.column} = ${child.value}`),
        },
        selected: selectedNodeId === child.id,
      });

      edges.push({
        id: `e_${id}_${child.id}`,
        source: id,
        target: child.id,
        type: 'smoothstep',
        animated: true,
        style: { stroke: 'rgba(34, 211, 238, 0.4)', strokeWidth: 2, strokeDasharray: '6 3' },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(34, 211, 238, 0.6)' },
      });
    });
  }

  return { nodes, edges };
}

export const HierarchyBuilder: React.FC<HierarchyBuilderProps> = ({ clientId, socket }) => {
  const { columns, mappings, setActiveJobId, setActiveJobType } = useWorkspaceStore();
  const [isBuilding, setIsBuilding] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [filterNodes, setFilterNodes] = useState<FilterNodeData[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>('root');
  const [editorParentId, setEditorParentId] = useState<string | null>(null);
  const [editorParentLabel, setEditorParentLabel] = useState<string>('');
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [enableDedup, setEnableDedup] = useState(true);
  const [enableVariancePruning, setEnableVariancePruning] = useState(true);

  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node>([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownloadZip = async () => {
    try {
      setIsDownloading(true);
      await hierarchyApi.exportAll(clientId);
    } catch (err) {
      console.error("Failed to download ZIP:", err);
    } finally {
      setIsDownloading(false);
    }
  };

  // Get candidate columns from mappings
  const candidateColumns = useMemo(() => {
    if (columns.length > 0) return columns;
    return Object.keys(mappings);
  }, [columns, mappings]);

  // When socket completes, show completion state
  useEffect(() => {
    if (socket.jobStatus === 'COMPLETED') {
      setIsBuilding(false);
      setIsComplete(true);
    }
    if (socket.jobStatus === 'FAILED' || socket.jobStatus === 'CANCELLED') {
      setIsBuilding(false);
      setIsComplete(false);
    }
  }, [socket.jobStatus]);

  const handleOpenEditor = useCallback((parentId: string, parentLabel: string) => {
    setEditorParentId(parentId);
    setEditorParentLabel(parentLabel);
  }, []);

  // Rebuild flow whenever filterNodes or selectedNodeId changes
  useEffect(() => {
    const { nodes, edges } = buildFlowGraph(filterNodes, selectedNodeId, handleOpenEditor);
    setFlowNodes(nodes);
    setFlowEdges(edges);
  }, [filterNodes, selectedNodeId, handleOpenEditor, setFlowNodes, setFlowEdges]);

  const handleConfirmFilter = (filter: { column: string; operator: string; value: string }) => {
    const newNode: FilterNodeData = {
      id: genId(),
      parentId: editorParentId,
      column: filter.column,
      value: filter.value,
      operator: filter.operator,
    };
    setFilterNodes(prev => [...prev, newNode]);
    setEditorParentId(null);
  };

  const handleNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNodeId(node.id);
  }, []);

  const handleConnect = useCallback((connection: Connection) => {
    setFlowEdges(eds => addEdge(connection, eds));
  }, [setFlowEdges]);

  const handleExecute = async () => {
    const hierarchyCols = filterNodes.length > 0
      ? [...new Set(filterNodes.map(n => n.column))]
      : selectedColumns;

    if (hierarchyCols.length === 0) return;

    setIsBuilding(true);
    try {
      const response = await apiClient.post('/api/segregate', {
        client_id: clientId,
        enable_dedup: enableDedup,
        enable_variance_pruning: enableVariancePruning,
        prune_high_variance: false,
        selected_hierarchy: hierarchyCols,
      });

      if (response.data.job_id) {
        setActiveJobId(response.data.job_id);
        setActiveJobType('segregation');
        socket.connectToJob(response.data.job_id);
      }
    } catch (e) {
      console.error(e);
      setIsBuilding(false);
    }
  };

  const handleReset = () => {
    setFilterNodes([]);
    setSelectedNodeId('root');
    setSelectedColumns([]);
  };

  const toggleColumn = (col: string) => {
    setSelectedColumns(prev =>
      prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
    );
  };

  const hasConfig = filterNodes.length > 0 || selectedColumns.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Top Stats Bar */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-4 px-6 py-3 bg-white/[0.02] border-b border-white/[0.06] shrink-0"
      >
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-cyan-400" />
          <span className="text-white font-bold text-sm">Hierarchy Graph Builder</span>
        </div>
        <div className="h-4 w-px bg-white/10" />
        <div className="flex items-center gap-4 text-xs">
          <span className="text-white/40">Nodes: <span className="text-cyan-400 font-bold">{filterNodes.length + 1}</span></span>
          <span className="text-white/40">Branches: <span className="text-violet-400 font-bold">{filterNodes.length}</span></span>
          <span className="text-white/40">Columns: <span className="text-emerald-400 font-bold">{candidateColumns.length}</span></span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {filterNodes.length > 0 && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white/50 text-xs hover:text-white hover:bg-white/[0.06] transition-all"
            >
              <RotateCcw className="w-3 h-3" /> Reset
            </button>
          )}
        </div>
      </motion.div>

      {/* Main 3-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* LEFT PANEL */}
        <motion.div
          initial={{ width: leftPanelOpen ? 280 : 0 }}
          animate={{ width: leftPanelOpen ? 280 : 48 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="border-r border-white/[0.06] bg-[#080f1f] shrink-0 overflow-hidden flex flex-col"
        >
          {/* Toggle button */}
          <button
            onClick={() => setLeftPanelOpen(v => !v)}
            className="flex items-center gap-2 p-3 border-b border-white/[0.06] text-white/50 hover:text-white transition-colors w-full"
          >
            <Layers className="w-4 h-4 text-cyan-400 shrink-0" />
            <AnimatePresence>
              {leftPanelOpen && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="text-xs font-bold text-white uppercase tracking-wider flex-1 text-left"
                >
                  Columns
                </motion.span>
              )}
            </AnimatePresence>
            {leftPanelOpen ? <ChevronUp className="w-3 h-3 shrink-0" /> : <ChevronDown className="w-3 h-3 shrink-0" />}
          </button>

          {leftPanelOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex-1 overflow-y-auto p-4 space-y-2"
            >
              <p className="text-[10px] text-white/30 uppercase tracking-wider font-bold mb-3">
                Select hierarchy columns (sequential)
              </p>
              {candidateColumns.length === 0 ? (
                <p className="text-xs text-white/30 text-center py-8">No columns available. Upload a dataset first.</p>
              ) : (
                candidateColumns.map((col) => {
                  const isSelected = selectedColumns.includes(col);
                  const idx = selectedColumns.indexOf(col);
                  return (
                    <button
                      key={col}
                      onClick={() => toggleColumn(col)}
                      className={`w-full flex items-center justify-between p-3 rounded-xl text-left text-sm transition-all
                        ${isSelected
                          ? 'bg-cyan-500/10 border border-cyan-500/30 text-white'
                          : 'bg-white/[0.02] border border-white/[0.05] text-white/50 hover:text-white hover:bg-white/[0.05]'
                        }`}
                    >
                      <span className="font-medium truncate">{col}</span>
                      {isSelected && (
                        <span className="ml-2 shrink-0 w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 text-[10px] font-bold flex items-center justify-center">
                          {idx + 1}
                        </span>
                      )}
                    </button>
                  );
                })
              )}

              {selectedColumns.length > 0 && (
                <div className="pt-4">
                  <p className="text-[10px] text-white/30 uppercase tracking-wider font-bold mb-2">Order</p>
                  {selectedColumns.map((col, i) => (
                    <div key={col} className="flex items-center gap-2 py-1.5 text-xs">
                      <span className="w-4 h-4 rounded-full bg-violet-500/20 text-violet-400 text-[10px] flex items-center justify-center font-bold">
                        {i + 1}
                      </span>
                      <span className="text-white/70">{col}</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </motion.div>

        {/* CENTER: React Flow Canvas */}
        <div className="flex-1 relative overflow-hidden" style={{ background: '#070d1c' }}>
          <ReactFlow
            nodes={flowNodes}
            edges={flowEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={handleConnect}
            onNodeClick={handleNodeClick}
            nodeTypes={NODE_TYPES}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            proOptions={{ hideAttribution: true }}
            style={{ background: 'transparent' }}
            defaultEdgeOptions={{
              type: 'smoothstep',
              animated: true,
              style: { stroke: 'rgba(34,211,238,0.35)', strokeWidth: 2 },
            }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="rgba(34,211,238,0.07)"
            />

            {/* React Flow Controls — fully overridden for dark theme visibility */}
            <style>{`
              .react-flow__controls {
                background: #0d1a30 !important;
                border: 1px solid rgba(34, 211, 238, 0.2) !important;
                border-radius: 12px !important;
                box-shadow: 0 0 20px rgba(0,0,0,0.6), 0 0 8px rgba(34,211,238,0.08) !important;
                padding: 2px !important;
                overflow: hidden;
              }
              .react-flow__controls-button {
                background: #0d1a30 !important;
                border: none !important;
                border-bottom: 1px solid rgba(255,255,255,0.06) !important;
                color: rgba(255,255,255,0.7) !important;
                fill: rgba(255,255,255,0.7) !important;
                width: 32px !important;
                height: 32px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: background 0.15s, color 0.15s !important;
              }
              .react-flow__controls-button:last-child {
                border-bottom: none !important;
              }
              .react-flow__controls-button:hover {
                background: rgba(34, 211, 238, 0.12) !important;
                color: #22d3ee !important;
                fill: #22d3ee !important;
              }
              .react-flow__controls-button svg {
                fill: currentColor !important;
                color: inherit !important;
                width: 14px !important;
                height: 14px !important;
              }
            `}</style>

            <Controls showInteractive={false} />

            <MiniMap
              style={{ background: '#070d1c', border: '1px solid rgba(34,211,238,0.15)', borderRadius: '10px' }}
              nodeColor={() => 'rgba(34,211,238,0.4)'}
              maskColor="rgba(7,13,28,0.85)"
            />
          </ReactFlow>

          {/* Empty state overlay */}
          {filterNodes.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="absolute inset-0 pointer-events-none flex items-center justify-center"
            >
              <div className="text-center">
                <GitBranch className="w-12 h-12 text-white/10 mx-auto mb-4" />
                <p className="text-sm text-white/20 font-medium">Click <span className="text-cyan-400/50">+ Add Child</span> on the root node to build the hierarchy</p>
                <p className="text-xs text-white/10 mt-2">Or select columns in the left panel for sequential splitting</p>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* BOTTOM: Execute Bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="shrink-0 border-t border-white/[0.06] bg-[#080f1f] px-6 py-4"
      >
        {isBuilding ? (
          <div className="flex flex-col gap-3 w-full">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                <div className="relative flex items-center justify-center">
                  <div className="absolute inset-0 bg-cyan-400/20 blur-md rounded-full animate-pulse" />
                  <SturixLogo className="w-5 h-5 relative z-10" isSpinning3D />
                </div>
                <span className="text-white font-bold text-sm tracking-wide">Building Hierarchy Graph...</span>
              </div>
              
              <div className="flex-1 flex justify-end items-center gap-6">
                <div className="flex items-center gap-2 text-xs text-white/60 bg-white/[0.03] px-3 py-1.5 rounded-lg border border-white/[0.05]">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Phase: <span className="text-cyan-300 font-medium">{socket.phase || 'Initializing...'}</span></span>
                </div>

                <div className="flex items-center gap-2 text-xs text-white/60 bg-white/[0.03] px-3 py-1.5 rounded-lg border border-white/[0.05]">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Progress: <span className="text-emerald-400 font-bold ml-1">{Math.round(socket.progress || 0)}%</span></span>
                </div>

                <div className="flex items-center gap-2 text-xs text-white/60 bg-white/[0.03] px-3 py-1.5 rounded-lg border border-white/[0.05]">
                  <span>ETA:</span>
                  <span className="text-amber-400 font-bold ml-1">
                    {socket.eta > 0 ? `${socket.eta}s` : 'Calculating...'}
                  </span>
                </div>
              </div>
            </div>

            {/* Progress bar */}
            <div className="relative w-full h-2 rounded-full bg-white/[0.05] overflow-hidden shadow-inner">
              <motion.div
                className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 overflow-hidden"
                animate={{ width: `${socket.progress || 0}%` }}
                transition={{ duration: 0.3 }}
              >
                {/* Sweeping shimmer overlay */}
                <div className="absolute top-0 left-[-100%] w-[100%] h-full bg-gradient-to-r from-transparent via-white/30 to-transparent skew-x-12 animate-[shimmer_1.5s_infinite]" />
              </motion.div>
            </div>
          </div>
        ) : isComplete ? (
          <div className="flex items-center gap-4 w-full">
            <div className="text-emerald-400 font-bold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Segregation Complete
            </div>
            <div className="flex-1" />
            <button
              onClick={handleDownloadZip}
              disabled={isDownloading}
              className="flex items-center gap-2 px-6 py-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-white transition-colors text-sm font-medium border border-white/[0.1] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDownloading ? (
                <>
                  <SturixLogo className="w-4 h-4" isSpinning3D />
                  Generating ZIP...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  Download ZIP
                </>
              )}
            </button>
            <button
              onClick={() => useWorkspaceStore.getState().setActiveTab('analysis')}
              className="flex items-center gap-2 px-8 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-void font-bold text-sm shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all"
            >
              Continue to Analysis
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-4">
            <div className="text-xs text-white/30">
              {hasConfig
                ? `${filterNodes.length > 0 ? filterNodes.length + 1 : selectedColumns.length} node${filterNodes.length > 0 || selectedColumns.length > 1 ? 's' : ''} configured`
                : 'No hierarchy configured yet'
              }
            </div>
            
            <div className="flex-1" />
            
            {/* Smart Duplication & Pruning Options */}
            <div className="flex items-center gap-3 bg-white/[0.02] border border-white/[0.05] rounded-xl px-3 py-2 mr-2">
              <span className="text-[10px] font-bold text-white/40 uppercase tracking-wider mr-2">Options</span>
              
              <button
                onClick={() => setEnableDedup(!enableDedup)}
                className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg transition-all ${
                  enableDedup ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'text-white/40 hover:text-white/60 border border-transparent'
                }`}
                title="Remove exact duplicate rows across all columns before building the graph"
              >
                <div className={`w-2 h-2 rounded-full ${enableDedup ? 'bg-emerald-400' : 'bg-white/20'}`} />
                Smart Deduplication
              </button>
              
              <button
                onClick={() => setEnableVariancePruning(!enableVariancePruning)}
                className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1.5 rounded-lg transition-all ${
                  enableVariancePruning ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20' : 'text-white/40 hover:text-white/60 border border-transparent'
                }`}
                title="Identify and warn about groups with unacceptably high variance in endpoint values"
              >
                <div className={`w-2 h-2 rounded-full ${enableVariancePruning ? 'bg-cyan-400' : 'bg-white/20'}`} />
                Variance Pruning
              </button>
            </div>

            <button
              onClick={() => {
                setIsComplete(false);
                handleExecute();
              }}
              disabled={!hasConfig}
              className={`relative flex items-center gap-3 px-10 py-3.5 rounded-xl font-bold text-sm transition-all overflow-hidden
                ${hasConfig
                  ? 'bg-gradient-to-r from-cyan-500 to-violet-500 hover:from-cyan-400 hover:to-violet-400 text-white shadow-[0_0_30px_rgba(34,211,238,0.35)] hover:shadow-[0_0_40px_rgba(34,211,238,0.5)]'
                  : 'bg-white/[0.03] border border-white/[0.06] text-white/20 cursor-not-allowed'
                }`}
            >
              {hasConfig && (
                <div className="absolute inset-0 bg-gradient-to-r from-white/10 to-transparent opacity-0 hover:opacity-100 transition-opacity" />
              )}
              <Play className="w-4 h-4 fill-current relative z-10" />
              <span className="relative z-10">Execute Graph Generation</span>
            </button>
          </div>
        )}
      </motion.div>

      {/* Filter Editor Panel (slide-in from right) */}
      <AnimatePresence>
        {editorParentId !== null && (
          <FilterEditorPanel
            columns={candidateColumns}
            onConfirm={handleConfirmFilter}
            onCancel={() => setEditorParentId(null)}
            parentLabel={editorParentLabel}
          />
        )}
      </AnimatePresence>
    </div>
  );
};
