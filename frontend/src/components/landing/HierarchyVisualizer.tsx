import React, { useState, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import { GitBranch, Database, ChevronRight, ChevronDown, Layers } from 'lucide-react';

interface TreeNode {
  id: string;
  label: string;
  rows: number;
  children?: TreeNode[];
  depth: number;
  color: string;
  textColor: string;
}

const TREE: TreeNode = {
  id: 'root', label: 'Full Dataset', rows: 412, depth: 0,
  color: 'border-white/[0.12] bg-white/[0.03]', textColor: 'text-white',
  children: [
    {
      id: 'fish', label: 'Fish (Pisces)', rows: 187, depth: 1,
      color: 'border-cyan-500/20 bg-cyan-500/[0.04]', textColor: 'text-cyan-400',
      children: [
        {
          id: 'fish-lc50', label: 'Endpoint: LC50', rows: 94, depth: 2,
          color: 'border-cyan-500/15 bg-cyan-500/[0.03]', textColor: 'text-cyan-300',
          children: [
            { id: 'fish-lc50-96h', label: 'Duration: 96h', rows: 61, depth: 3, color: 'border-cyan-500/10 bg-transparent', textColor: 'text-cyan-200', children: [] },
            { id: 'fish-lc50-48h', label: 'Duration: 48h', rows: 33, depth: 3, color: 'border-cyan-500/10 bg-transparent', textColor: 'text-cyan-200', children: [] },
          ]
        },
        { id: 'fish-noec', label: 'Endpoint: NOEC', rows: 93, depth: 2, color: 'border-cyan-500/15 bg-transparent', textColor: 'text-cyan-300', children: [] },
      ]
    },
    {
      id: 'daphnia', label: 'Daphnia magna', rows: 142, depth: 1,
      color: 'border-violet-500/20 bg-violet-500/[0.04]', textColor: 'text-violet-400',
      children: [
        { id: 'daphnia-ec50', label: 'Endpoint: EC50', rows: 89, depth: 2, color: 'border-violet-500/15 bg-transparent', textColor: 'text-violet-300', children: [] },
        { id: 'daphnia-lcx', label: 'Endpoint: LCx', rows: 53, depth: 2, color: 'border-violet-500/15 bg-transparent', textColor: 'text-violet-300', children: [] },
      ]
    },
    {
      id: 'algae', label: 'Algae & Plants', rows: 83, depth: 1,
      color: 'border-emerald-500/20 bg-emerald-500/[0.04]', textColor: 'text-emerald-400',
      children: [
        { id: 'algae-ec50', label: 'Endpoint: EC50', rows: 83, depth: 2, color: 'border-emerald-500/15 bg-transparent', textColor: 'text-emerald-300', children: [] },
      ]
    },
  ]
};

const TreeNodeComponent: React.FC<{ node: TreeNode; selectedId: string | null; onSelect: (id: string) => void }> = ({ node, selectedId, onSelect }) => {
  const [expanded, setExpanded] = useState(node.depth <= 1);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;

  return (
    <div>
      <motion.div
        whileHover={{ x: 2 }}
        onClick={() => { onSelect(node.id); if (hasChildren) setExpanded(v => !v); }}
        className={`flex items-center gap-2 p-2.5 rounded-xl cursor-pointer border transition-all mb-1 ${
          isSelected ? node.color + ' ring-1 ring-white/10' : 'border-transparent hover:bg-white/[0.03]'
        }`}
        style={{ marginLeft: node.depth * 16 }}
      >
        <div className={`w-5 h-5 flex items-center justify-center shrink-0 ${ hasChildren ? 'text-white/30' : 'text-white/10'}`}>
          {hasChildren ? (expanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />) : <div className="w-1.5 h-1.5 rounded-full bg-white/10" />}
        </div>
        <div className={`w-6 h-6 rounded-lg flex items-center justify-center ${ node.color.split(' ')[1] || 'bg-white/[0.03]'}`}>
          {node.depth === 0 ? <Database className={`w-3 h-3 ${node.textColor}`} /> : <Layers className={`w-3 h-3 ${node.textColor}`} />}
        </div>
        <span className={`text-xs font-semibold ${isSelected ? node.textColor : 'text-white/50'}`}>{node.label}</span>
        <span className={`ml-auto text-[10px] font-mono ${ isSelected ? node.textColor : 'text-white/20'}`}>{node.rows.toLocaleString()} rows</span>
      </motion.div>

      <AnimatePresence>
        {expanded && hasChildren && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            {node.children!.map(child => (
              <TreeNodeComponent key={child.id} node={child} selectedId={selectedId} onSelect={onSelect} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const findNode = (node: TreeNode, id: string): TreeNode | null => {
  if (node.id === id) return node;
  for (const child of (node.children || [])) {
    const found = findNode(child, id);
    if (found) return found;
  }
  return null;
};

export const HierarchyVisualizer: React.FC = () => {
  const [selectedId, setSelectedId] = useState<string>('root');
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });
  const selectedNode = findNode(TREE, selectedId);

  return (
    <section id="hierarchy" ref={ref} className="py-28 px-6 bg-[#020610] border-t border-white/[0.04]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/[0.08] border border-violet-500/20 text-xs font-semibold text-violet-400 mb-5">
            <GitBranch className="w-3 h-3" />
            Hierarchy Engine
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">Recursive Lineage DAG</h2>
          <p className="text-white/40 text-lg max-w-2xl mx-auto">
            Each node contains <em className="text-white/60 not-italic">only its parent\'s filtered rows</em>. 
            Navigate the tree and see how the dataset partitions at each biological level.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.15 }}
          className="grid lg:grid-cols-2 gap-6"
        >
          {/* Tree panel */}
          <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-5">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/[0.05]">
              <GitBranch className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-bold text-white">Dataset Hierarchy</span>
              <span className="ml-auto text-[10px] text-white/30">Click to inspect node</span>
            </div>
            <TreeNodeComponent node={TREE} selectedId={selectedId} onSelect={setSelectedId} />
          </div>

          {/* Node detail panel */}
          <AnimatePresence mode="wait">
            {selectedNode && (
              <motion.div
                key={selectedId}
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.3 }}
                className={`rounded-2xl border ${selectedNode.color} p-5 flex flex-col gap-5`}
              >
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-1">Selected Node</p>
                  <h3 className={`text-xl font-extrabold ${selectedNode.textColor}`}>{selectedNode.label}</h3>
                  <p className="text-white/40 text-sm mt-1">Depth level {selectedNode.depth} — {selectedNode.rows.toLocaleString()} inherited rows</p>
                </div>

                {/* Row inheritance visualization */}
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-2">Row Inheritance</p>
                  <div className="flex items-center gap-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(selectedNode.rows / TREE.rows) * 100}%` }}
                      transition={{ duration: 0.6, ease: 'easeOut' }}
                      className={`h-2 rounded-full ${ selectedNode.depth === 0 ? 'bg-white/30' : selectedNode.depth === 1 ? 'bg-gradient-to-r from-cyan-500 to-violet-500' : selectedNode.depth === 2 ? 'bg-gradient-to-r from-violet-500 to-pink-500' : 'bg-gradient-to-r from-pink-500 to-rose-500'}`}
                      style={{ minWidth: 4 }}
                    />
                    <span className={`text-xs font-bold ${selectedNode.textColor}`}>
                      {Math.round((selectedNode.rows / TREE.rows) * 100)}%
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-white/[0.04] -mt-2" />
                  <p className="text-[10px] text-white/30 mt-2">{selectedNode.rows} of {TREE.rows} total rows inherited</p>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'Node Rows', val: selectedNode.rows.toLocaleString() },
                    { label: 'Depth Level', val: `Level ${selectedNode.depth}` },
                    { label: 'Child Nodes', val: (selectedNode.children?.length || 0).toString() },
                    { label: 'Parent Coverage', val: `${Math.round((selectedNode.rows / TREE.rows) * 100)}%` },
                  ].map(s => (
                    <div key={s.label} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-[9px] font-bold uppercase tracking-widest text-white/20 mb-1">{s.label}</p>
                      <p className={`text-sm font-extrabold ${selectedNode.textColor}`}>{s.val}</p>
                    </div>
                  ))}
                </div>

                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-[9px] font-bold uppercase tracking-widest text-white/20 mb-1.5">Scientific Context</p>
                  <p className="text-xs text-white/40 leading-relaxed">
                    This node contains a strictly filtered subset of the parent dataset. 
                    All descriptors and model training performed at this node are biologically scoped 
                    and cannot contaminate sibling branches.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </section>
  );
};
