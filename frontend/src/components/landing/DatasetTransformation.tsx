import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import { AlertTriangle, CheckCircle, Layers, Zap, BarChart3 } from 'lucide-react';

const stages = [
  { id: 0, label: 'Raw Dataset', sublabel: 'CSV with mixed formats', color: 'text-red-400', icon: <AlertTriangle className="w-4 h-4" /> },
  { id: 1, label: 'Column Detection', sublabel: 'Schema profiling', color: 'text-amber-400', icon: <Layers className="w-4 h-4" /> },
  { id: 2, label: 'Smart Mapping', sublabel: 'Semantic binding', color: 'text-cyan-400', icon: <CheckCircle className="w-4 h-4" /> },
  { id: 3, label: 'Hierarchy Filtering', sublabel: 'Lineage DAG', color: 'text-violet-400', icon: <Layers className="w-4 h-4" /> },
  { id: 4, label: 'Descriptor Enrichment', sublabel: 'QSAR features added', color: 'text-amber-400', icon: <Zap className="w-4 h-4" /> },
  { id: 5, label: 'AI-Ready Dataset', sublabel: 'Model-ready export', color: 'text-emerald-400', icon: <BarChart3 className="w-4 h-4" /> },
];

// Simulated raw data rows
const rawRows = [
  { species: 'Daphnia magna', endpoint: 'EC50', value: '2.3', unit: 'mg/L', smiles: 'CCO', test_type: 'acute' },
  { species: 'Oncorhynchus mykiss', endpoint: 'LC50', value: '??', unit: 'ug/L', smiles: '', test_type: '' },
  { species: 'Daphnia magna', endpoint: 'EC50', value: '2.3', unit: 'mg/L', smiles: 'CCO', test_type: 'acute' },
  { species: 'Pimephales promelas', endpoint: 'NOEC', value: '0.8', unit: 'mg/L', smiles: 'c1ccccc1', test_type: 'chronic' },
  { species: '', endpoint: 'LC50', value: '-999', unit: '?', smiles: 'INVALID', test_type: 'N/A' },
];

const mappedRows = [
  { species: 'Daphnia magna', endpoint: 'EC50', value: '2.3', smiles: 'CCO', status: 'ok' },
  { species: 'Oncorhynchus mykiss', endpoint: 'LC50', value: 'resolved', smiles: 'CC(=O)O', status: 'resolved' },
  { species: 'Pimephales promelas', endpoint: 'NOEC', value: '0.8', smiles: 'c1ccccc1', status: 'ok' },
];

const enrichedRows = [
  { species: 'Daphnia magna', MolWt: '46.07', LogP: '-0.31', TPSA: '20.23', QED: '0.40' },
  { species: 'Oncorhynchus mykiss', MolWt: '60.05', LogP: '-0.17', TPSA: '37.30', QED: '0.55' },
  { species: 'Pimephales promelas', MolWt: '78.11', LogP: '1.69', TPSA: '0.00', QED: '0.61' },
];

const StageIndicator: React.FC<{ stages: typeof stages; current: number }> = ({ stages, current }) => (
  <div className="flex items-center gap-1 flex-wrap justify-center mb-8">
    {stages.map((s, i) => (
      <React.Fragment key={s.id}>
        <motion.div
          animate={{ opacity: i <= current ? 1 : 0.3, scale: i === current ? 1.05 : 1 }}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold border ${
            i === current
              ? 'bg-white/[0.06] border-white/[0.12] text-white'
              : i < current
                ? 'bg-white/[0.02] border-white/[0.04] text-white/30'
                : 'bg-transparent border-white/[0.04] text-white/20'
          }`}
        >
          <span className={i <= current ? s.color : 'text-white/20'}>{s.icon}</span>
          {s.label}
        </motion.div>
        {i < stages.length - 1 && (
          <motion.div
            animate={{ opacity: i < current ? 0.4 : 0.1 }}
            className="w-4 h-px bg-white/30 hidden sm:block"
          />
        )}
      </React.Fragment>
    ))}
  </div>
);

const DataTable: React.FC<{ stage: number }> = ({ stage }) => {
  if (stage === 0) return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-white/[0.06]">
            {['species', 'endpoint', 'value', 'unit', 'smiles', 'test_type'].map(h => (
              <th key={h} className="py-2 px-3 text-left text-white/30 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rawRows.map((row, i) => {
            const hasProblem = !row.species || row.value === '??' || row.value === '-999' || !row.smiles || row.smiles === 'INVALID';
            return (
              <motion.tr
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`border-b border-white/[0.03] ${ hasProblem ? 'bg-red-500/[0.04]' : ''}`}
              >
                {Object.values(row).map((val, j) => {
                  const isBad = !val || val === '??' || val === '-999' || val === 'INVALID' || val === 'N/A';
                  return (
                    <td key={j} className={`py-2 px-3 ${ isBad ? 'text-red-400/80' : 'text-white/50'}`}>
                      {isBad && <AlertTriangle className="w-3 h-3 inline mr-1" />}
                      {val || '—'}
                    </td>
                  );
                })}
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );

  if (stage <= 2) return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-white/[0.06]">
            {['species', 'endpoint', 'value', 'smiles', 'status'].map(h => (
              <th key={h} className="py-2 px-3 text-left text-cyan-400/50 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {mappedRows.map((row, i) => (
            <motion.tr
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.1 }}
              className="border-b border-white/[0.03]"
            >
              <td className="py-2 px-3 text-white/70">{row.species}</td>
              <td className="py-2 px-3 text-cyan-400/70">{row.endpoint}</td>
              <td className="py-2 px-3 text-white/70">{row.value}</td>
              <td className="py-2 px-3 text-white/40">{row.smiles}</td>
              <td className="py-2 px-3">
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${ row.status === 'ok' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>
                  {row.status}
                </span>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  if (stage === 3) return (
    <div className="space-y-2">
      {[{label:'Fish / LC50 / 96h', rows: 12, depth: 3}, {label:'Daphnia magna / EC50', rows: 27, depth: 2}, {label:'Pimephales promelas / NOEC / chronic', rows: 8, depth: 3}].map((node, i) => (
        <motion.div
          key={node.label}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.1 }}
          style={{ paddingLeft: node.depth * 12 }}
          className="flex items-center gap-3 p-3 rounded-xl bg-violet-500/[0.05] border border-violet-500/[0.1]"
        >
          <Layers className="w-3.5 h-3.5 text-violet-400 shrink-0" />
          <span className="text-xs text-white/70 font-mono">{node.label}</span>
          <span className="ml-auto text-[10px] text-violet-400/60 font-semibold">{node.rows} rows</span>
        </motion.div>
      ))}
    </div>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-white/[0.06]">
            {['species', 'MolWt', 'LogP', 'TPSA', 'QED'].map(h => (
              <th key={h} className="py-2 px-3 text-left text-amber-400/50 font-semibold">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {enrichedRows.map((row, i) => (
            <motion.tr
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.1 }}
              className="border-b border-white/[0.03]"
            >
              {Object.values(row).map((val, j) => (
                <td key={j} className={`py-2 px-3 ${ j > 0 ? 'text-amber-400/70' : 'text-white/70'}`}>{val}</td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const DatasetTransformation: React.FC = () => {
  const [stage, setStage] = useState(0);
  const [autoPlay, setAutoPlay] = useState(true);
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  useEffect(() => {
    if (!autoPlay || !inView) return;
    const t = setInterval(() => {
      setStage(v => {
        if (v >= stages.length - 1) { setAutoPlay(false); return v; }
        return v + 1;
      });
    }, 2200);
    return () => clearInterval(t);
  }, [autoPlay, inView]);

  return (
    <section ref={ref} className="py-28 px-6 bg-[#020610] border-t border-white/[0.04]">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-14"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-500/[0.08] border border-amber-500/20 text-xs font-semibold text-amber-400 mb-5">
            <Zap className="w-3 h-3" />
            Live Transformation
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">Dataset Engineering in Real-Time</h2>
          <p className="text-white/40 text-lg max-w-2xl mx-auto">
            Watch how the platform transforms raw, noisy toxicology data into a clean, enriched, AI-ready dataset.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2 }}
          className="rounded-3xl bg-white/[0.02] border border-white/[0.06] overflow-hidden"
        >
          {/* Stage header */}
          <div className="px-6 pt-6">
            <StageIndicator stages={stages} current={stage} />
          </div>

          {/* Current stage label */}
          <div className="px-6 pb-3 flex items-center justify-between">
            <AnimatePresence mode="wait">
              <motion.div
                key={stage}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="flex items-center gap-2"
              >
                <span className={stages[stage].color}>{stages[stage].icon}</span>
                <span className="text-sm font-bold text-white">{stages[stage].label}</span>
                <span className="text-xs text-white/30">— {stages[stage].sublabel}</span>
              </motion.div>
            </AnimatePresence>
            <div className="flex items-center gap-1">
              {stages.map((_, i) => (
                <button
                  key={i}
                  onClick={() => { setStage(i); setAutoPlay(false); }}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${ i === stage ? 'bg-white/60 w-4' : 'bg-white/20'}`}
                />
              ))}
            </div>
          </div>

          {/* Table area */}
          <div className="px-6 pb-6">
            <div className="rounded-2xl bg-white/[0.02] border border-white/[0.04] overflow-hidden p-4 min-h-[220px]">
              <AnimatePresence mode="wait">
                <motion.div
                  key={stage}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <DataTable stage={stage} />
                </motion.div>
              </AnimatePresence>
            </div>
          </div>

          {/* Navigation */}
          <div className="px-6 pb-6 flex items-center justify-between">
            <button
              onClick={() => { setStage(v => Math.max(0, v - 1)); setAutoPlay(false); }}
              disabled={stage === 0}
              className="px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-white/50 text-xs font-semibold disabled:opacity-30 hover:bg-white/[0.07] transition-colors"
            >
              ← Previous
            </button>
            <span className="text-xs text-white/20">{stage + 1} / {stages.length}</span>
            <button
              onClick={() => { setStage(v => Math.min(stages.length - 1, v + 1)); setAutoPlay(false); }}
              disabled={stage === stages.length - 1}
              className="px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.06] text-white/50 text-xs font-semibold disabled:opacity-30 hover:bg-white/[0.07] transition-colors"
            >
              Next →
            </button>
          </div>
        </motion.div>
      </div>
    </section>
  );
};
