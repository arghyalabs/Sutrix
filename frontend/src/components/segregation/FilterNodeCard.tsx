import React, { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Plus, Database, GitBranch, Leaf } from 'lucide-react';

export interface FilterNodeCardData {
  label: string;
  filterCol: string;
  filterVal: string;
  rowCount: number;
  uniqueCompounds: number;
  isRoot: boolean;
  isLeaf: boolean;
  level: number;
  onAddChild: () => void;
  [key: string]: unknown; // satisfy Record<string, unknown>
}

const levelAccents: Record<number, { border: string; glow: string; badge: string; text: string }> = {
  0: { border: 'border-emerald-500/40', glow: 'shadow-[0_0_20px_rgba(16,185,129,0.2)]', badge: 'bg-emerald-500/20 text-emerald-300', text: 'text-emerald-400' },
  1: { border: 'border-cyan-500/40',    glow: 'shadow-[0_0_20px_rgba(34,211,238,0.2)]',  badge: 'bg-cyan-500/20 text-cyan-300',    text: 'text-cyan-400' },
  2: { border: 'border-violet-500/40',  glow: 'shadow-[0_0_20px_rgba(139,92,246,0.2)]',  badge: 'bg-violet-500/20 text-violet-300', text: 'text-violet-400' },
  3: { border: 'border-amber-500/40',   glow: 'shadow-[0_0_20px_rgba(245,158,11,0.2)]',  badge: 'bg-amber-500/20 text-amber-300',   text: 'text-amber-400' },
};

const getAccent = (level: number) => levelAccents[Math.min(level, 3)];

export const FilterNodeCard: React.FC<NodeProps> = memo(({ data, selected }) => {
  const d = data as FilterNodeCardData;
  const accent = getAccent(d.level);

  return (
    <div
      className={`
        relative flex flex-col bg-[#0a1628] rounded-2xl border transition-all duration-200 min-w-[180px]
        ${selected
          ? `${accent.border} ${accent.glow} border-opacity-80`
          : 'border-white/[0.08] hover:border-white/20'
        }
      `}
      style={{ boxShadow: selected ? undefined : '0 4px 24px rgba(0,0,0,0.4)' }}
    >
      {/* Target handle (top) */}
      {!d.isRoot && (
        <Handle
          type="target"
          position={Position.Top}
          style={{
            background: 'rgba(34,211,238,0.4)',
            border: '2px solid rgba(34,211,238,0.6)',
            width: 10,
            height: 10,
          }}
        />
      )}

      <div className="px-4 pt-4 pb-3">
        {/* Header: icon + filter label */}
        <div className="flex items-center gap-2.5 mb-3">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${accent.badge}`}>
            {d.isRoot
              ? <Database className="w-4 h-4" />
              : d.isLeaf
                ? <Leaf className="w-4 h-4" />
                : <GitBranch className="w-4 h-4" />
            }
          </div>
          <div className="min-w-0">
            {d.isRoot ? (
              <p className={`text-sm font-bold ${accent.text} truncate`}>Root Dataset</p>
            ) : (
              <>
                <p className="text-[10px] text-white/30 font-medium uppercase tracking-wider truncate">{d.filterCol}</p>
                <p className={`text-sm font-bold ${accent.text} truncate`}>{d.filterVal}</p>
              </>
            )}
          </div>
        </div>

        {/* Stats row */}
        {(d.rowCount > 0 || d.uniqueCompounds > 0) && (
          <div className="flex items-center gap-2 mb-3">
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-[10px] text-white/50">
              <span className="text-white/70 font-bold">{d.rowCount.toLocaleString()}</span>
              <span>rows</span>
            </span>
            {d.uniqueCompounds > 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.06] text-[10px] text-white/50">
                <span className="text-white/70 font-bold">{d.uniqueCompounds.toLocaleString()}</span>
                <span>cpds</span>
              </span>
            )}
          </div>
        )}

        {/* Add child button */}
        <button
          onClick={(e) => { e.stopPropagation(); d.onAddChild(); }}
          className="w-full flex items-center justify-center gap-1.5 py-1.5 rounded-xl
            bg-white/[0.02] border border-dashed border-white/[0.1]
            text-white/30 hover:text-white/70 hover:border-white/20 hover:bg-white/[0.04]
            transition-all text-[10px] font-medium group"
        >
          <Plus className="w-3 h-3 group-hover:rotate-90 transition-transform duration-200" />
          Add Child
        </button>
      </div>

      {/* Source handle (bottom) */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{
          background: 'rgba(34,211,238,0.4)',
          border: '2px solid rgba(34,211,238,0.6)',
          width: 10,
          height: 10,
        }}
      />
    </div>
  );
});

FilterNodeCard.displayName = 'FilterNodeCard';
