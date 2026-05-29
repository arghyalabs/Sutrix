import React, { useState, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import { Download, Folder, FolderOpen, File, ChevronRight } from 'lucide-react';

interface FileNode {
  name: string;
  type: 'folder' | 'file';
  ext?: string;
  size?: string;
  children?: FileNode[];
}

const EXPORT_TREE: FileNode[] = [
  {
    name: 'hierarchy_export/', type: 'folder',
    children: [
      {
        name: 'Fish/', type: 'folder',
        children: [
          {
            name: 'LC50/', type: 'folder',
            children: [
              {
                name: '96h/', type: 'folder',
                children: [
                  { name: 'curated.parquet', type: 'file', ext: 'parquet', size: '12 KB' },
                  { name: 'curated.xlsx', type: 'file', ext: 'xlsx', size: '24 KB' },
                ]
              },
              {
                name: '48h/', type: 'folder',
                children: [
                  { name: 'curated.parquet', type: 'file', ext: 'parquet', size: '8 KB' },
                ]
              },
            ]
          },
          {
            name: 'NOEC/', type: 'folder',
            children: [
              { name: 'curated.parquet', type: 'file', ext: 'parquet', size: '18 KB' },
            ]
          },
        ]
      },
      {
        name: 'Daphnia_magna/', type: 'folder',
        children: [
          {
            name: 'EC50/', type: 'folder',
            children: [
              { name: 'curated.parquet', type: 'file', ext: 'parquet', size: '22 KB' },
              { name: 'curated.xlsx', type: 'file', ext: 'xlsx', size: '41 KB' },
            ]
          },
        ]
      },
      { name: 'enriched_dataset.parquet', type: 'file', ext: 'parquet', size: '2.1 MB' },
      { name: 'compliance_report.pdf', type: 'file', ext: 'pdf', size: '340 KB' },
    ]
  }
];

const extColor: Record<string, string> = {
  parquet: 'text-amber-400',
  xlsx: 'text-emerald-400',
  pdf: 'text-red-400',
};

const FNode: React.FC<{ node: FileNode; depth: number; delay: number; inView: boolean }> = ({
  node, depth, delay, inView
}) => {
  const [open, setOpen] = useState(depth < 2);
  const isFolder = node.type === 'folder';
  const color = node.ext ? (extColor[node.ext] || 'text-white/40') : 'text-violet-400';

  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ delay, duration: 0.4 }}
    >
      <div
        className="flex items-center gap-2 py-1 rounded-lg cursor-pointer hover:bg-white/[0.03] transition-colors"
        style={{ paddingLeft: depth * 16 + 8, paddingRight: 8 }}
        onClick={() => isFolder && setOpen(v => !v)}
      >
        {isFolder
          ? (open
              ? <FolderOpen className="w-3.5 h-3.5 text-violet-400 shrink-0" />
              : <Folder className="w-3.5 h-3.5 text-violet-400/60 shrink-0" />)
          : <File className={`w-3.5 h-3.5 ${color} shrink-0`} />
        }
        <span className={`text-xs font-mono ${isFolder ? 'text-white/60 font-semibold' : color}`}>
          {node.name}
        </span>
        {node.size && (
          <span className="ml-auto text-[9px] text-white/20 font-mono">{node.size}</span>
        )}
        {isFolder && (
          <ChevronRight className={`w-3 h-3 text-white/20 transition-transform ml-1 ${open ? 'rotate-90' : ''}`} />
        )}
      </div>
      <AnimatePresence>
        {isFolder && open && node.children && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            {node.children.map((child, i) => (
              <FNode
                key={child.name + i}
                node={child}
                depth={depth + 1}
                delay={delay + 0.03 * i}
                inView={inView}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const formats = [
  {
    ext: 'Parquet', desc: 'Snappy-compressed, ML-ready',
    color: 'text-amber-400', bg: 'bg-amber-500/[0.06]', border: 'border-amber-500/15',
    note: 'sklearn / PyTorch compatible'
  },
  {
    ext: 'XLSX', desc: 'Formatted spreadsheet export',
    color: 'text-emerald-400', bg: 'bg-emerald-500/[0.06]', border: 'border-emerald-500/15',
    note: 'Human-readable, formatted'
  },
  {
    ext: 'ZIP', desc: 'Full hierarchy archive',
    color: 'text-violet-400', bg: 'bg-violet-500/[0.06]', border: 'border-violet-500/15',
    note: 'Mirrors the full DAG tree structure'
  },
  {
    ext: 'PDF', desc: 'Compliance audit report',
    color: 'text-red-400', bg: 'bg-red-500/[0.06]', border: 'border-red-500/15',
    note: 'OECD readiness documentation'
  },
];

export const ExportVisualization: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section ref={ref} className="py-28 px-6 bg-[#020610] border-t border-white/[0.04]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-500/[0.08] border border-teal-500/20 text-xs font-semibold text-teal-400 mb-5">
            <Download className="w-3 h-3" />
            Export Engine
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">Hierarchical Export Structure</h2>
          <p className="text-white/40 text-lg max-w-2xl mx-auto">
            Exports mirror the full DAG tree. Each node generates its own curated files, preserving the biological hierarchy.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-6">
          {/* File tree */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.1 }}
            className="rounded-2xl bg-white/[0.02] border border-white/[0.06] overflow-hidden"
          >
            <div className="px-5 py-4 border-b border-white/[0.05] flex items-center gap-2">
              <Folder className="w-4 h-4 text-violet-400" />
              <span className="text-sm font-bold text-white">Export Directory</span>
              <span className="ml-auto text-[10px] text-white/30">Click folders to expand</span>
            </div>
            <div className="p-4">
              {EXPORT_TREE.map((node, i) => (
                <FNode key={node.name} node={node} depth={0} delay={0.1 + i * 0.05} inView={inView} />
              ))}
            </div>
          </motion.div>

          {/* Format cards */}
          <div className="space-y-4">
            <motion.p
              initial={{ opacity: 0 }}
              animate={inView ? { opacity: 1 } : {}}
              transition={{ delay: 0.1 }}
              className="text-xs font-bold uppercase tracking-widest text-white/30"
            >
              Export Formats
            </motion.p>
            {formats.map((f, i) => (
              <motion.div
                key={f.ext}
                initial={{ opacity: 0, x: 16 }}
                animate={inView ? { opacity: 1, x: 0 } : {}}
                transition={{ delay: 0.15 + i * 0.08 }}
                className={`flex items-center gap-4 p-4 rounded-2xl border ${f.border} ${f.bg}`}
              >
                <div className={`px-3 py-1.5 rounded-lg text-sm font-extrabold font-mono ${f.color} ${f.bg} border ${f.border} shrink-0`}>
                  .{f.ext.toLowerCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white/70">{f.desc}</p>
                  <p className="text-xs text-white/30">{f.note}</p>
                </div>
                <Download className={`w-4 h-4 ${f.color} opacity-40 shrink-0`} />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
