import React from 'react';
import { motion } from 'framer-motion';
import { Download, Filter, GitBranch, Database, AlertTriangle } from 'lucide-react';
import { hierarchyApi } from '../../services/hierarchyApi';

interface NodeDetail {
  id: string;
  metadata: {
    path: string;
    filter_col: string;
    filter_val: string;
    inherited_filters: Record<string, string>;
    applied_filter: Record<string, string>;
    row_count: number;
    unique_compounds: number;
    is_leaf: boolean;
    level: number;
  };
  stats: {
    total_rows: number;
    missing_cells: number;
    numeric_cols: number;
    categorical_cols: number;
    unique_compounds: number;
    missing_pct: number;
  };
  export_formats: string[];
}

interface NodeMetaPanelProps {
  nodeDetail: NodeDetail | null;
  clientId: string;
}

export const NodeMetaPanel: React.FC<NodeMetaPanelProps> = ({ nodeDetail, clientId }) => {
  if (!nodeDetail) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-white/20 p-6">
        <Database className="w-10 h-10 mb-3 opacity-30" />
        <p className="text-xs text-center">Select a node to inspect its metadata</p>
      </div>
    );
  }

  const { metadata, stats, export_formats } = nodeDetail;

  // Parse path breadcrumbs
  const pathParts = metadata.path ? metadata.path.split(' > ') : ['Root'];

  const inheritedEntries = Object.entries(metadata.inherited_filters || {});
  const appliedEntries = Object.entries(metadata.applied_filter || {});

  const exportFormatIcons: Record<string, string> = {
    csv: '📄',
    xlsx: '📊',
    parquet: '⚡',
    sdf: '🧪',
    feather: '🪶',
    json: '{ }',
  };

  return (
    <motion.div
      key={nodeDetail.id}
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
      className="h-full overflow-y-auto custom-scrollbar p-5 space-y-5"
    >
      {/* Path breadcrumb */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-2">Path</p>
        <div className="flex flex-wrap items-center gap-1">
          {pathParts.map((part, i) => (
            <React.Fragment key={i}>
              <span
                className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                  i === pathParts.length - 1
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/20'
                    : 'text-white/40'
                }`}
              >
                {part}
              </span>
              {i < pathParts.length - 1 && (
                <span className="text-white/20 text-xs">›</span>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Stats pills */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: 'Rows', value: stats.total_rows?.toLocaleString() ?? '—', accent: 'text-cyan-400' },
          { label: 'Compounds', value: stats.unique_compounds?.toLocaleString() ?? '—', accent: 'text-violet-400' },
          { label: 'Missing %', value: `${stats.missing_pct?.toFixed(1) ?? 0}%`, accent: 'text-amber-400' },
          { label: 'Numeric', value: stats.numeric_cols ?? '—', accent: 'text-emerald-400' },
        ].map(s => (
          <div key={s.label} className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05]">
            <p className="text-[9px] uppercase tracking-wider text-white/30 font-bold">{s.label}</p>
            <p className={`text-lg font-bold ${s.accent} leading-tight mt-0.5`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Applied filter */}
      {appliedEntries.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1">
            <Filter className="w-3 h-3" /> Applied Filter
          </p>
          <div className="p-3 rounded-xl bg-cyan-500/[0.04] border border-cyan-500/20">
            {appliedEntries.map(([col, val]) => (
              <div key={col} className="flex items-center gap-2">
                <span className="text-cyan-400/70 text-xs font-mono">{col}</span>
                <span className="text-white/30 text-xs">=</span>
                <span className="text-white text-sm font-bold">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inherited filters */}
      {inheritedEntries.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1">
            <GitBranch className="w-3 h-3" /> Inherited Filters
          </p>
          <div className="space-y-1.5">
            {inheritedEntries.map(([col, val]) => (
              <div key={col} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-white/40 text-xs font-mono">{col}</span>
                <span className="text-white/20 text-xs">=</span>
                <span className="text-white/60 text-xs">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Leaf badge */}
      {metadata.is_leaf && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-violet-500/[0.08] border border-violet-500/20">
          <AlertTriangle className="w-3.5 h-3.5 text-violet-400" />
          <span className="text-xs text-violet-300 font-medium">Leaf node — no child splits</span>
        </div>
      )}

      {/* Export buttons */}
      {export_formats && export_formats.length > 0 && (
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-2 flex items-center gap-1">
            <Download className="w-3 h-3" /> Export Node Data
          </p>
          <div className="grid grid-cols-2 gap-2">
            {export_formats.map((fmt) => (
              <button
                key={fmt}
                onClick={() => hierarchyApi.exportNode(clientId, nodeDetail.id, fmt)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/[0.02] border border-white/[0.06]
                  text-white/60 text-xs font-medium hover:bg-white/[0.05] hover:text-white hover:border-white/[0.1]
                  transition-all"
              >
                <span>{exportFormatIcons[fmt] ?? '📁'}</span>
                <span className="uppercase font-bold">{fmt}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
};
