import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { motion } from 'framer-motion';
import { Database, Plus, Users, FlaskConical } from 'lucide-react';

interface FilterNodeCardData {
  label: string;
  filterCol: string;
  filterVal: string;
  rowCount: number;
  uniqueCompounds: number;
  isRoot?: boolean;
  isLeaf?: boolean;
  level: number;
  onAddChild?: () => void;
}

interface FilterNodeCardProps {
  data: FilterNodeCardData;
  selected: boolean;
}

export const FilterNodeCard: React.FC<FilterNodeCardProps> = ({ data, selected }) => {
  const {
    label,
    filterCol,
    filterVal,
    rowCount,
    uniqueCompounds,
    isRoot,
    isLeaf,
    onAddChild
  } = data;

  const levelColors = [
    'from-emerald-500/20 to-emerald-600/5 border-emerald-500/30',
    'from-cyan-500/20 to-cyan-600/5 border-cyan-500/30',
    'from-violet-500/20 to-violet-600/5 border-violet-500/30',
    'from-amber-500/20 to-amber-600/5 border-amber-500/30',
  ];
  const levelAccents = ['text-emerald-400', 'text-cyan-400', 'text-violet-400', 'text-amber-400'];
  const colorIdx = Math.min(data.level, levelColors.length - 1);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`
        relative min-w-[180px] max-w-[220px] rounded-xl
        bg-[#0d1b35] border
        transition-all duration-200
        ${selected
          ? 'border-cyan-400/60 shadow-[0_0_30px_rgba(34,211,238,0.35)]'
          : `${levelColors[colorIdx]} shadow-[0_0_20px_rgba(34,211,238,0.08)] hover:shadow-[0_0_25px_rgba(34,211,238,0.18)]`
        }
      `}
    >
      {/* Active indicator stripe */}
      {selected && (
        <div className="absolute top-0 left-0 right-0 h-[2px] rounded-t-xl bg-gradient-to-r from-cyan-400 to-violet-400" />
      )}

      {!isRoot && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !bg-cyan-500/80 !border-2 !border-cyan-400/60 !rounded-full"
        />
      )}

      <div className="p-3">
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          {isRoot ? (
            <div className="w-6 h-6 rounded-md bg-emerald-500/20 flex items-center justify-center">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
            </div>
          ) : (
            <div className={`w-6 h-6 rounded-md bg-white/5 flex items-center justify-center`}>
              <FlaskConical className={`w-3.5 h-3.5 ${levelAccents[colorIdx]}`} />
            </div>
          )}
          <span className={`text-[10px] font-bold uppercase tracking-widest ${levelAccents[colorIdx]}`}>
            {isRoot ? 'Root' : `L${data.level}`}
          </span>
        </div>

        {/* Filter badge */}
        {!isRoot && (
          <div className="mb-2 px-2 py-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
            <span className="text-[10px] text-white/50">{filterCol}</span>
            <span className="text-[10px] text-white/30 mx-1">=</span>
            <span className="text-[11px] font-semibold text-white">{filterVal}</span>
          </div>
        )}

        {/* Label */}
        <div className="text-sm font-bold text-white truncate mb-2" title={label}>
          {label}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <Users className="w-3 h-3 text-white/30" />
            <span className="text-[10px] text-white/50 font-medium">
              {rowCount != null ? rowCount.toLocaleString() : '—'}
            </span>
          </div>
          {uniqueCompounds != null && uniqueCompounds > 0 && (
            <>
              <span className="text-white/10">·</span>
              <span className="text-[10px] text-cyan-400/60 font-medium">{uniqueCompounds} cpds</span>
            </>
          )}
        </div>

        {/* Leaf indicator */}
        {isLeaf && (
          <div className="mt-2 text-[9px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 font-bold uppercase tracking-widest inline-block">
            Leaf
          </div>
        )}

        {/* Add child button */}
        {onAddChild && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onAddChild();
            }}
            className="nodrag mt-3 w-full flex items-center justify-center gap-1 py-1.5 rounded-lg
              bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[10px] font-bold
              hover:bg-cyan-500/20 hover:border-cyan-400/40 transition-all"
          >
            <Plus className="w-3 h-3" /> Add Child
          </button>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-cyan-500/80 !border-2 !border-cyan-400/60 !rounded-full"
      />
    </motion.div>
  );
};
