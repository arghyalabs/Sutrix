import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';
import { hierarchyApi } from '../../services/hierarchyApi';
import { NodeVisualization } from './NodeVisualization';
import { NodeMetaPanel } from './NodeMetaPanel';
import { Activity, ChevronRight, Database, GitBranch, AlertCircle } from 'lucide-react';

interface HierarchyNodeMeta {
  id: string;
  parent_id: string | null;
  level: number;
  node_name: string;
  filter_col: string;
  filter_val: string;
  path: string;
  inherited_filters: Record<string, string>;
  applied_filter: Record<string, string>;
  row_count: number;
  unique_compounds: number;
  is_leaf: boolean;
  children: string[];
}

// Recursive Tree Node component
const TreeNode: React.FC<{
  node: HierarchyNodeMeta;
  nodeMap: Record<string, HierarchyNodeMeta>;
  selectedId: string;
  onSelect: (id: string) => void;
  depth?: number;
}> = ({ node, nodeMap, selectedId, onSelect, depth = 0 }) => {
  const [expanded, setExpanded] = useState(depth < 2);
  const isSelected = node.id === selectedId;
  const hasChildren = node.children && node.children.length > 0;
  
  const levelColors = ['text-emerald-400', 'text-cyan-400', 'text-violet-400', 'text-amber-400'];
  const accent = levelColors[Math.min(node.level, levelColors.length - 1)];

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, x: -6 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: depth * 0.05 }}
        onClick={() => onSelect(node.id)}
        className={`w-max min-w-full text-left flex items-center gap-2 px-3 py-2 rounded-xl transition-all text-xs group cursor-pointer pr-4
          ${isSelected
            ? 'bg-cyan-500/10 border border-cyan-500/30 shadow-[0_0_12px_rgba(34,211,238,0.15)]'
            : 'hover:bg-white/[0.03] border border-transparent'
          }`}
        style={{ paddingLeft: `${12 + depth * 16}px` }}
      >
        {/* Expand toggle */}
        {hasChildren ? (
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(v => !v); }}
            className="w-4 h-4 flex items-center justify-center shrink-0 text-white/30 hover:text-white/60"
          >
            <ChevronRight className={`w-3 h-3 transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </button>
        ) : (
          <span className="w-4 h-4 shrink-0" />
        )}

        {/* Icon */}
        {node.level === 0 ? (
          <Database className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
        ) : (
          <GitBranch className={`w-3.5 h-3.5 ${accent} shrink-0`} />
        )}

        {/* Label */}
        <div className="flex-1 whitespace-nowrap">
          {node.level === 0 ? (
            <span className="font-bold text-white pr-2">Root Dataset</span>
          ) : (
            <span className={`font-semibold ${isSelected ? 'text-white' : 'text-white/70'} whitespace-nowrap block pr-2`}>
              <span className="text-white/40">{node.filter_col}</span>
              <span className="text-white/20 mx-1">=</span>
              <span className={accent}>{node.filter_val}</span>
            </span>
          )}
        </div>

        {/* Row count badge */}
        {node.row_count > 0 && (
          <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full
            ${isSelected ? 'bg-cyan-500/20 text-cyan-300' : 'bg-white/[0.04] text-white/30'}`}>
            {node.row_count.toLocaleString()}
          </span>
        )}
      </motion.div>

      {/* Children */}
      <AnimatePresence>
        {hasChildren && expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="relative ml-6">
              {/* Connector line */}
              <div className="absolute left-2 top-0 bottom-2 w-px bg-white/[0.05]" />
              {node.children.map(childId => {
                const childNode = nodeMap[childId];
                if (!childNode) return null;
                return (
                  <TreeNode
                    key={childId}
                    node={childNode}
                    nodeMap={nodeMap}
                    selectedId={selectedId}
                    onSelect={onSelect}
                    depth={depth + 1}
                  />
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const DataAnalysisWorkspace: React.FC = () => {
  const {
    activeLineage,
    activeSegregationResult,
    activeNodeId,
    activeNodeDetail,
    workspaceId,
    setActiveNodeId,
    setActiveNodeDetail,
  } = useWorkspaceStore();

  const [isLoadingNode, setIsLoadingNode] = useState(false);

  // Build nodeMap for efficient lookup
  const lineage = activeLineage || (activeSegregationResult?.graph ? {
    nodes: activeSegregationResult.graph.nodes || [],
    edges: activeSegregationResult.graph.edges || [],
    root_id: 'root',
    total_nodes: activeSegregationResult.graph.nodes?.length || 0,
    max_depth: activeSegregationResult.graph.max_depth || 1,
  } : null);

  const nodeMap: Record<string, HierarchyNodeMeta> = {};
  if (lineage?.nodes) {
    lineage.nodes.forEach((n: HierarchyNodeMeta) => {
      nodeMap[n.id] = n;
    });
  }

  const rootNode = lineage ? nodeMap[lineage.root_id] || lineage.nodes?.[0] : null;

  const fetchNodeDetail = useCallback(async (nodeId: string) => {
    if (!workspaceId) return;
    setIsLoadingNode(true);
    try {
      const detail = await hierarchyApi.getNodeDetail(workspaceId, nodeId);
      setActiveNodeDetail(detail);
    } catch (e) {
      console.error('Failed to fetch node detail:', e);
    } finally {
      setIsLoadingNode(false);
    }
  }, [workspaceId, setActiveNodeDetail]);

  // Auto-select root on first load
  useEffect(() => {
    if (rootNode && !activeNodeId) {
      setActiveNodeId(rootNode.id);
      fetchNodeDetail(rootNode.id);
    }
  }, [rootNode, activeNodeId, setActiveNodeId, fetchNodeDetail]);

  const handleSelectNode = useCallback((id: string) => {
    setActiveNodeId(id);
    fetchNodeDetail(id);
  }, [setActiveNodeId, fetchNodeDetail]);

  // Empty state
  if (!lineage) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center h-full text-center px-6 py-20"
      >
        <div className="relative mb-8">
          <div className="w-24 h-24 rounded-3xl bg-cyan-500/5 border border-cyan-500/10 flex items-center justify-center mx-auto">
            <Activity className="w-12 h-12 text-cyan-500/30" />
          </div>
          <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
          </div>
        </div>
        <h3 className="text-white font-bold text-xl mb-3">No Hierarchy Available</h3>
        <p className="text-white/40 text-sm max-w-sm">
          Complete the Hierarchy Builder step to generate a DAG. The analysis workspace will auto-populate once the graph computation finishes.
        </p>
        <button
          onClick={() => useWorkspaceStore.getState().setActiveTab('hierarchy')}
          className="mt-8 flex items-center gap-2 px-6 py-3 rounded-xl bg-white text-black font-bold text-sm shadow-[0_4px_14px_rgba(255,255,255,0.15)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.25)] transition-all hover:-translate-y-0.5 active:translate-y-0"
        >
          Go to Hierarchy Builder <ChevronRight className="w-4 h-4" />
        </button>
      </motion.div>
    );
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* LEFT PANEL: Lineage Tree Navigator (25%) */}
      <div className="w-[25%] border-r border-white/[0.06] bg-[#080f1f] flex flex-col">
        <div className="px-4 py-4 border-b border-white/[0.06]">
          <h3 className="text-white font-bold text-sm flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            Lineage Navigator
          </h3>
          <div className="flex gap-3 mt-2 text-[10px] text-white/30">
            <span>{lineage.total_nodes || lineage.nodes?.length} nodes</span>
            <span>·</span>
            <span>depth {lineage.max_depth}</span>
          </div>
        </div>

        <div className="flex-1 overflow-auto custom-scrollbar p-3">
          <div className="w-max min-w-full">
            {rootNode ? (
              <TreeNode
                node={rootNode}
                nodeMap={nodeMap}
                selectedId={activeNodeId || ''}
                onSelect={handleSelectNode}
                depth={0}
              />
            ) : (
              <div className="py-8 text-center text-xs text-white/20">No nodes found</div>
            )}
          </div>
        </div>
      </div>

      {/* CENTER: Node Visualization (50%) */}
      <div className="w-[50%] border-r border-white/[0.06] flex flex-col">
        <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between shrink-0">
          <h3 className="text-white font-bold text-sm">Node Analytics</h3>
          {activeNodeId && (
            <span className="text-xs text-white/30 font-mono truncate max-w-[200px]">{activeNodeId}</span>
          )}
        </div>
        <div className="flex-1 overflow-hidden">
          <NodeVisualization nodeDetail={activeNodeDetail} isLoading={isLoadingNode} />
        </div>

        {/* Continue button */}
        <div className="shrink-0 p-4 border-t border-white/[0.06]">
          <button
            onClick={() => useWorkspaceStore.getState().setActiveTab('enrichment')}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-white text-black font-bold text-sm shadow-[0_4px_14px_rgba(255,255,255,0.15)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.25)] hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Continue to Descriptor Enrichment <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* RIGHT PANEL: NodeMetaPanel (25%) */}
      <div className="w-[25%] bg-[#080f1f] flex flex-col">
        <div className="px-4 py-4 border-b border-white/[0.06]">
          <h3 className="text-white font-bold text-sm flex items-center gap-2">
            <Database className="w-4 h-4 text-violet-400" />
            Node Inspector
          </h3>
        </div>
        <div className="flex-1 overflow-hidden">
          <NodeMetaPanel nodeDetail={activeNodeDetail} clientId={workspaceId} />
        </div>
      </div>
    </div>
  );
};
