import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ChevronDown, Check } from 'lucide-react';

interface FilterEditorPanelProps {
  columns: string[];
  onConfirm: (filter: { column: string; operator: string; value: string }) => void;
  onCancel: () => void;
  parentLabel?: string;
}

const OPERATORS = [
  { value: 'equals', label: 'equals (=)' },
  { value: 'not_equals', label: 'not equals (≠)' },
  { value: 'contains', label: 'contains' },
  { value: 'in_list', label: 'in list' },
  { value: 'greater_than', label: 'greater than (>)' },
  { value: 'less_than', label: 'less than (<)' },
  { value: 'between', label: 'between' },
  { value: 'is_null', label: 'is null' },
  { value: 'not_null', label: 'not null' },
];

const NO_VALUE_OPS = ['is_null', 'not_null'];

export const FilterEditorPanel: React.FC<FilterEditorPanelProps> = ({
  columns,
  onConfirm,
  onCancel,
  parentLabel,
}) => {
  const [column, setColumn] = useState(columns[0] || '');
  const [operator, setOperator] = useState('equals');
  const [value, setValue] = useState('');
  const [colOpen, setColOpen] = useState(false);
  const [opOpen, setOpOpen] = useState(false);

  const noValue = NO_VALUE_OPS.includes(operator);

  const handleConfirm = () => {
    if (!column) return;
    if (!noValue && !value.trim()) return;
    onConfirm({ column, operator, value: noValue ? '' : value.trim() });
  };

  return (
    <AnimatePresence>
      <motion.div
        key="filter-editor-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-end"
        style={{ background: 'rgba(11,19,43,0.7)', backdropFilter: 'blur(4px)' }}
        onClick={onCancel}
      >
        <motion.div
          key="filter-editor-panel"
          initial={{ x: '100%', opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="h-full w-[360px] bg-[#0d1a30] border-l border-white/[0.06] flex flex-col shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-white/[0.06]">
            <div>
              <h3 className="text-white font-bold text-lg">Add Filter Branch</h3>
              {parentLabel && (
                <p className="text-xs text-white/40 mt-0.5">
                  Child of: <span className="text-cyan-400">{parentLabel}</span>
                </p>
              )}
            </div>
            <button
              onClick={onCancel}
              className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-center text-white/50 hover:text-white hover:bg-white/[0.08] transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5">
            {/* Column selector */}
            <div>
              <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                Column
              </label>
              <div className="relative">
                <button
                  onClick={() => { setColOpen(!colOpen); setOpOpen(false); }}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white text-sm hover:bg-white/[0.06] transition-all"
                >
                  <span className="font-medium text-cyan-300">{column || 'Select column...'}</span>
                  <ChevronDown className={`w-4 h-4 text-white/40 transition-transform ${colOpen ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {colOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="absolute top-full mt-1 left-0 right-0 z-10 bg-[#0d1a30] border border-white/[0.08] rounded-xl shadow-2xl overflow-hidden max-h-48 overflow-y-auto"
                    >
                      {columns.map((col) => (
                        <button
                          key={col}
                          onClick={() => { setColumn(col); setColOpen(false); }}
                          className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center justify-between ${
                            column === col
                              ? 'bg-cyan-500/10 text-cyan-300'
                              : 'text-white/70 hover:bg-white/[0.04] hover:text-white'
                          }`}
                        >
                          {col}
                          {column === col && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Operator selector */}
            <div>
              <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                Operator
              </label>
              <div className="relative">
                <button
                  onClick={() => { setOpOpen(!opOpen); setColOpen(false); }}
                  className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white text-sm hover:bg-white/[0.06] transition-all"
                >
                  <span className="text-violet-300">
                    {OPERATORS.find(o => o.value === operator)?.label}
                  </span>
                  <ChevronDown className={`w-4 h-4 text-white/40 transition-transform ${opOpen ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                  {opOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="absolute top-full mt-1 left-0 right-0 z-10 bg-[#0d1a30] border border-white/[0.08] rounded-xl shadow-2xl overflow-hidden"
                    >
                      {OPERATORS.map((op) => (
                        <button
                          key={op.value}
                          onClick={() => { setOperator(op.value); setOpOpen(false); }}
                          className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center justify-between ${
                            operator === op.value
                              ? 'bg-violet-500/10 text-violet-300'
                              : 'text-white/70 hover:bg-white/[0.04] hover:text-white'
                          }`}
                        >
                          {op.label}
                          {operator === op.value && <Check className="w-3.5 h-3.5 text-violet-400" />}
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Value input */}
            {!noValue && (
              <div>
                <label className="block text-xs font-bold text-white/50 uppercase tracking-wider mb-2">
                  Value
                  {operator === 'in_list' && (
                    <span className="ml-2 text-white/30 normal-case font-normal">(comma-separated)</span>
                  )}
                  {operator === 'between' && (
                    <span className="ml-2 text-white/30 normal-case font-normal">(e.g. 1,100)</span>
                  )}
                </label>
                <input
                  type="text"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder={
                    operator === 'in_list' ? 'Fish, Mammal, Bird' :
                    operator === 'between' ? '1, 100' :
                    'Enter value...'
                  }
                  className="w-full px-4 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white text-sm placeholder-white/20
                    focus:outline-none focus:border-cyan-500/50 focus:bg-white/[0.05] transition-all"
                />
              </div>
            )}

            {/* Preview */}
            {column && (noValue || value.trim()) && (
              <div className="p-3 rounded-xl bg-cyan-500/[0.04] border border-cyan-500/20">
                <p className="text-[10px] font-bold text-cyan-500/60 uppercase tracking-wider mb-1">Preview</p>
                <p className="text-sm text-white font-mono">
                  <span className="text-cyan-300">{column}</span>
                  <span className="text-white/40 mx-1">{OPERATORS.find(o => o.value === operator)?.label.split(' ')[0]}</span>
                  {!noValue && <span className="text-emerald-300">"{value}"</span>}
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-white/[0.06] flex gap-3">
            <button
              onClick={onCancel}
              className="flex-1 py-3 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white/60 text-sm font-medium hover:bg-white/[0.06] hover:text-white transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!column || (!noValue && !value.trim())}
              className="flex-1 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 text-white text-sm font-bold
                hover:from-cyan-400 hover:to-violet-400 transition-all disabled:opacity-40 disabled:cursor-not-allowed
                shadow-[0_0_20px_rgba(34,211,238,0.25)]"
            >
              Confirm Filter
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
