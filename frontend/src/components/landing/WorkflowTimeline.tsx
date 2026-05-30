import React, { useState, useRef } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import {
  Upload, Map, GitBranch, BarChart3, Zap, CheckCircle, Download,
  Layers, Filter, Database, Activity, ShieldCheck
} from 'lucide-react';

interface Step {
  id: number;
  icon: React.ReactNode;
  label: string;
  tag: string;
  color: string;
  textColor: string;
  borderColor: string;
  bgColor: string;
  purpose: string;
  operations: string[];
  outputs: string[];
  scientific: string;
}

const steps: Step[] = [
  {
    id: 1, label: 'Upload', tag: '01 — Ingestion',
    icon: <Upload className="w-5 h-5" />,
    color: 'rgba(52,211,153,0.5)', textColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/20', bgColor: 'bg-emerald-500/[0.06]',
    purpose: 'Securely ingest CSV, XLSX, or Parquet datasets with automatic schema detection and async background processing.',
    operations: ['Async multipart file upload', 'Automatic encoding detection', 'Schema profiling and column type profiling', 'Background job with WebSocket progress'],
    outputs: ['Compressed Parquet workspace file', 'Column type manifest', 'Inferred schema report'],
    scientific: 'Establishes the immutable source-of-truth dataset that all downstream operations inherit from.'
  },
  {
    id: 2, label: 'Mapping', tag: '02 — Semantic Binding',
    icon: <Map className="w-5 h-5" />,
    color: 'rgba(34,211,238,0.5)', textColor: 'text-cyan-400',
    borderColor: 'border-cyan-500/20', bgColor: 'bg-cyan-500/[0.06]',
    purpose: 'AI-powered fuzzy semantic mapping binds your column names to standardized universal scientific variables used by SUTRIX.',
    operations: ['Fuzzy text matching with RapidFuzz', 'Scientific ontology registry lookup', 'Fuzzy, exact and semantic matching checks', 'Confidence scoring (visual color codes)'],
    outputs: ['Binding manifest (JSON)', 'Confidence scores', 'Unmapped column warnings'],
    scientific: 'Ensures downstream scientific operations target the correct chemical/biological dimensions regardless of header name.'
  },
  {
    id: 3, label: 'Hierarchy Builder', tag: '03 — Lineage Engine',
    icon: <GitBranch className="w-5 h-5" />,
    color: 'rgba(167,139,250,0.5)', textColor: 'text-violet-400',
    borderColor: 'border-violet-500/20', bgColor: 'bg-violet-500/[0.06]',
    purpose: 'Recursively partitions the dataset into a lineage-aware DAG where each node inherits only the filtered rows of its parent.',
    operations: ['Species-level root partitioning', 'Endpoint-aware branching', 'Qualifier and test type filtering', 'Node-level Parquet generation'],
    outputs: ['Hierarchy DAG (JSON)', 'Per-node curated Parquets', 'Downloadable ZIP archive', 'Lineage trace metadata'],
    scientific: 'Prevents global dataframe contamination. Each branch maintains strict biological context.'
  },
  {
    id: 4, label: 'Data Analysis', tag: '04 — Quality Stats',
    icon: <BarChart3 className="w-5 h-5" />,
    color: 'rgba(96,165,250,0.5)', textColor: 'text-blue-400',
    borderColor: 'border-blue-500/20', bgColor: 'bg-blue-500/[0.06]',
    purpose: 'Node-level statistical exploration with interactive charts, distribution analysis, and data quality metrics.',
    operations: ['Endpoint value distributions', 'Duplicate compound detection', 'Missing value mapping', 'Class frequency analysis'],
    outputs: ['Distribution charts (PNG)', 'Statistical summary report', 'Data quality flags'],
    scientific: 'Identifies dataset biases, outliers, and structural weaknesses before enrichment. Critical for QSAR model validity.'
  },
  {
    id: 5, label: 'Descriptor Enrichment', tag: '05 — Parallel Calc',
    icon: <Zap className="w-5 h-5" />,
    color: 'rgba(251,191,36,0.5)', textColor: 'text-amber-400',
    borderColor: 'border-amber-500/20', bgColor: 'bg-amber-500/[0.06]',
    purpose: 'Multi-core parallel QSAR descriptor calculation using RDKit and Mordred with persistent SQLite caching.',
    operations: ['RDKit 2D/3D descriptor suite (~208)', 'Mordred full descriptor set (2,043)', 'Parallel ProcessPoolExecutor engine', 'Persistent SQLite hit-cache (90%+ hit rate)'],
    outputs: ['Enriched Parquet dataset', 'Descriptor matrix', 'Cache statistics'],
    scientific: 'Generates the molecular feature space required for QSAR modeling. Caching prevents redundant computation.'
  },
  {
    id: 6, label: 'Readiness Evaluation', tag: '06 — Modeling Checks',
    icon: <Activity className="w-5 h-5" />,
    color: 'rgba(244,114,182,0.5)', textColor: 'text-pink-400',
    borderColor: 'border-pink-500/20', bgColor: 'bg-pink-500/[0.06]',
    purpose: 'Assess dataset suitability for machine learning. Checks class balance, PCA embeddings, feature variance, and leakage.',
    operations: ['Class imbalance Shannon entropy', 'Feature variance threshold checks', 'Pearson correlation matrices', 'Leakage detection checks'],
    outputs: ['Readiness score (0-100)', 'Risk indicator report', 'Algorithm recommendations'],
    scientific: 'Validates dataset fitness for predictive modeling before training occurs, preventing modeling failures.'
  },
  {
    id: 7, label: 'Compound Explorer', tag: '07 — Interactive Search',
    icon: <Database className="w-5 h-5" />,
    color: 'rgba(96,165,250,0.5)', textColor: 'text-blue-400',
    borderColor: 'border-blue-500/20', bgColor: 'bg-blue-500/[0.06]',
    purpose: 'Interactively search, filter, and inspect every compound, its descriptors, and its RDKit structure.',
    operations: ['Google-style fast search', 'On-demand 2D chemical structure render', 'Categorized descriptor tables', 'Distribution density and histogram charts'],
    outputs: ['Individual compound profile', '2D molecular SVG', 'Interactive value distributions'],
    scientific: 'Enables quick manual verification of molecular structures and descriptor values for anomalous chemicals.'
  },
  {
    id: 8, label: 'OECD Assessment', tag: '08 — Regulatory Science',
    icon: <ShieldCheck className="w-5 h-5" />,
    color: 'rgba(167,139,250,0.5)', textColor: 'text-violet-400',
    borderColor: 'border-violet-500/20', bgColor: 'bg-violet-500/[0.06]',
    purpose: 'Comprehensive validation of dataset readiness against the 5 strict OECD principles for QSAR modeling.',
    operations: ['Defined endpoint audit', 'Unambiguous algorithm checks', 'Applicability domain analysis', 'Mechanistic basis evaluation'],
    outputs: ['OECD compliance score', 'Audit logs per principle', 'Regulatory readiness report'],
    scientific: 'Crucial for regulatory acceptance. Ensures QSAR datasets match international compliance standards.'
  },
  {
    id: 9, label: 'Export', tag: '09 — Downstream Output',
    icon: <Download className="w-5 h-5" />,
    color: 'rgba(45,212,191,0.5)', textColor: 'text-teal-400',
    borderColor: 'border-teal-500/20', bgColor: 'bg-teal-500/[0.06]',
    purpose: 'Generate model-ready exports in multiple formats with full hierarchy ZIP structure preservation.',
    operations: ['Snappy Parquet (ML-ready)', 'XLSX formatting', 'Hierarchical ZIP archive', 'PDF compliance report'],
    outputs: ['enriched.parquet', 'hierarchy.zip', 'compliance_report.pdf', 'curated.xlsx'],
    scientific: 'Produces exports directly compatible with sklearn, PyTorch, R, and KNIME modeling environments.'
  },
];

const StepDetail: React.FC<{ step: Step; onClose: () => void }> = ({ step, onClose }) => (
  <motion.div
    initial={{ opacity: 0, y: -12, height: 0 }}
    animate={{ opacity: 1, y: 0, height: 'auto' }}
    exit={{ opacity: 0, y: -8, height: 0 }}
    transition={{ duration: 0.35, ease: 'easeOut' }}
    className={`overflow-hidden mt-4 rounded-2xl border ${step.borderColor} ${step.bgColor} p-6`}
  >
    <div className="grid md:grid-cols-3 gap-6">
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-2">Purpose</p>
        <p className="text-sm text-white/70 leading-relaxed">{step.purpose}</p>
        <div className="mt-4 p-3 rounded-xl bg-white/[0.03] border border-white/[0.04]">
          <p className="text-[10px] font-bold uppercase tracking-widest text-white/20 mb-1.5">Scientific Importance</p>
          <p className="text-xs text-white/40 leading-relaxed italic">{step.scientific}</p>
        </div>
      </div>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-2">Operations</p>
        <ul className="space-y-1.5">
          {step.operations.map(op => (
            <li key={op} className="flex items-start gap-2">
              <span className={`w-1 h-1 rounded-full mt-1.5 shrink-0 ${step.textColor} opacity-60`} />
              <span className="text-xs text-white/50">{op}</span>
            </li>
          ))}
        </ul>
      </div>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-2">Outputs</p>
        <ul className="space-y-2">
          {step.outputs.map(out => (
            <li key={out} className={`text-xs font-mono px-2.5 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.05] ${step.textColor} opacity-80`}>
              {out}
            </li>
          ))}
        </ul>
      </div>
    </div>
  </motion.div>
);

export const WorkflowTimeline: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-100px' });

  return (
    <section id="workflow" ref={ref} className="py-28 px-6 bg-[#03070f] border-t border-white/[0.04]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-violet-500/[0.08] border border-violet-500/20 text-xs font-semibold text-violet-400 mb-5">
            <Layers className="w-3 h-3" />
            Scientific Workflow
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">9-Step Research Pipeline</h2>
          <p className="text-white/40 text-lg max-w-2xl mx-auto">
            From ingestion and mapping to regulatory verification and ML-ready export. Click a step to explore.
          </p>
        </motion.div>

        {/* Horizontal step indicators */}
        <div className="relative mb-6">
          <div className="absolute top-5 left-0 right-0 h-px bg-white/[0.05] hidden md:block" />
          <div className="grid grid-cols-3 md:grid-cols-9 gap-4 md:gap-2">
            {steps.map((step, idx) => {
              const isActive = activeStep === step.id;
              return (
                <motion.button
                  key={step.id}
                  initial={{ opacity: 0, y: 14 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{ delay: idx * 0.05, duration: 0.5 }}
                  onClick={() => setActiveStep(isActive ? null : step.id)}
                  className="flex flex-col items-center text-center group relative"
                >
                  <motion.div
                    whileHover={{ scale: 1.06 }}
                    animate={isActive ? { scale: 1.08 } : { scale: 1 }}
                    className={`w-10 h-10 rounded-2xl flex items-center justify-center mb-2 border transition-all ${
                      isActive
                        ? `${step.bgColor} ${step.borderColor} ${step.textColor} shadow-[0_0_20px_${step.color}]`
                        : 'bg-white/[0.03] border-white/[0.06] text-white/30 group-hover:text-white/60 group-hover:bg-white/[0.06]'
                    }`}
                  >
                    {step.icon}
                  </motion.div>
                  <span className={`text-[9px] font-bold uppercase tracking-widest mb-0.5 ${
                    isActive ? step.textColor : 'text-white/20'
                  }`}>0{idx + 1}</span>
                  <span className={`text-[10px] font-semibold leading-tight hidden md:block ${
                    isActive ? 'text-white' : 'text-white/30 group-hover:text-white/50'
                  }`}>{step.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="step-indicator"
                      className={`absolute -bottom-2 w-1 h-1 rounded-full ${step.textColor.replace('text-', 'bg-')}`}
                    />
                  )}
                </motion.button>
              );
            })}
          </div>
        </div>

        {/* Detail panel */}
        <AnimatePresence mode="wait">
          {activeStep !== null && (
            <StepDetail
              key={activeStep}
              step={steps.find(s => s.id === activeStep)!}
              onClose={() => setActiveStep(null)}
            />
          )}
        </AnimatePresence>

        {!activeStep && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center text-white/20 text-xs mt-6"
          >
            ↑ Click any step above to explore its scientific role
          </motion.p>
        )}
      </div>
    </section>
  );
};
