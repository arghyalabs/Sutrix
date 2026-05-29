import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Layers, Cpu, Shield, Database, Network, FlaskConical, Download, Activity, Zap } from 'lucide-react';

interface Feature {
  icon: React.ReactNode;
  title: string;
  desc: string;
  tag: string;
  color: string;
  bgColor: string;
  borderColor: string;
  textColor: string;
  detail: string;
}

const features: Feature[] = [
  {
    icon: <Layers className="w-5 h-5" />,
    title: 'Hierarchical Dataset Engineering',
    tag: 'Core Engine',
    desc: 'Recursive lineage-aware DAG partitioning. Each node inherits only its parent\'s filtered rows.',
    detail: 'Prevents global dataframe contamination. Enables per-node model training at any biological depth.',
    color: 'rgba(167,139,250,0.4)', textColor: 'text-violet-400',
    bgColor: 'bg-violet-500/[0.05]', borderColor: 'border-violet-500/[0.12]',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: 'AI Readiness Analysis',
    tag: 'Quality Gate',
    desc: 'OECD-inspired compliance checks including class imbalance, variance, and multicollinearity analysis.',
    detail: 'Produces a scored readiness report (0-100) with actionable model suitability recommendations.',
    color: 'rgba(244,114,182,0.4)', textColor: 'text-pink-400',
    bgColor: 'bg-pink-500/[0.05]', borderColor: 'border-pink-500/[0.12]',
  },
  {
    icon: <Zap className="w-5 h-5" />,
    title: 'Descriptor Enrichment',
    tag: 'Calculation Engine',
    desc: 'Multi-core RDKit and Mordred descriptor calculation with 90%+ SQLite cache hit rates.',
    detail: '208 RDKit descriptors and 2,043 Mordred descriptors calculated in parallel subprocess pools.',
    color: 'rgba(251,191,36,0.4)', textColor: 'text-amber-400',
    bgColor: 'bg-amber-500/[0.05]', borderColor: 'border-amber-500/[0.12]',
  },
  {
    icon: <Activity className="w-5 h-5" />,
    title: 'WebSocket Scientific Processing',
    tag: 'Real-Time',
    desc: 'Live telemetry streaming with per-job progress tracking, ETA, and worker log forwarding.',
    detail: 'Async background processing with full WebSocket broadcast. No polling required from the frontend.',
    color: 'rgba(34,211,238,0.4)', textColor: 'text-cyan-400',
    bgColor: 'bg-cyan-500/[0.05]', borderColor: 'border-cyan-500/[0.12]',
  },
  {
    icon: <Network className="w-5 h-5" />,
    title: 'Node-Aware Visualization',
    tag: 'Explorer',
    desc: 'Interactive hierarchy tree with row counts, data previews, and node-level chart generation.',
    detail: 'Navigate the full DAG and inspect any node\'s filtered dataset independently.',
    color: 'rgba(96,165,250,0.4)', textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/[0.05]', borderColor: 'border-blue-500/[0.12]',
  },
  {
    icon: <FlaskConical className="w-5 h-5" />,
    title: 'QSAR Preparation',
    tag: 'Scientific',
    desc: 'Full SMILES resolution via PubChem, Bemis-Murcko scaffold analysis, and chemical space mapping.',
    detail: 'Produces datasets directly compatible with sklearn, PyTorch, and R modeling environments.',
    color: 'rgba(52,211,153,0.4)', textColor: 'text-emerald-400',
    bgColor: 'bg-emerald-500/[0.05]', borderColor: 'border-emerald-500/[0.12]',
  },
  {
    icon: <Download className="w-5 h-5" />,
    title: 'Export Automation',
    tag: 'Output',
    desc: 'One-click export of enriched Parquet, curated XLSX, hierarchical ZIP, and PDF compliance reports.',
    detail: 'ZIP archives mirror the full DAG tree structure with per-node curated files.',
    color: 'rgba(45,212,191,0.4)', textColor: 'text-teal-400',
    bgColor: 'bg-teal-500/[0.05]', borderColor: 'border-teal-500/[0.12]',
  },
  {
    icon: <Database className="w-5 h-5" />,
    title: 'Predictive Modeling Intelligence',
    tag: 'AI Analytics',
    desc: 'Automated model type recommendations, feature importance previews, and training readiness scoring.',
    detail: 'Identifies regression vs classification tasks and flags structural dataset issues before training.',
    color: 'rgba(251,146,60,0.4)', textColor: 'text-orange-400',
    bgColor: 'bg-orange-500/[0.05]', borderColor: 'border-orange-500/[0.12]',
  },
];

const FeatureCard: React.FC<{ f: Feature; i: number; inView: boolean }> = ({ f, i, inView }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={inView ? { opacity: 1, y: 0 } : {}}
    transition={{ delay: i * 0.06, duration: 0.5 }}
    whileHover={{ y: -3 }}
    className={`group relative p-6 rounded-2xl border ${f.borderColor} ${f.bgColor} hover:border-opacity-50 transition-all cursor-default overflow-hidden`}
  >
    {/* Glow on hover */}
    <div
      className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 rounded-2xl"
      style={{ background: `radial-gradient(circle at 20% 20%, ${f.color.replace('0.4', '0.08')}, transparent 70%)` }}
    />
    <div className="relative z-10">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl ${f.bgColor} border ${f.borderColor} flex items-center justify-center ${f.textColor}`}>
          {f.icon}
        </div>
        <span className={`text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full ${f.bgColor} ${f.textColor} border ${f.borderColor}`}>
          {f.tag}
        </span>
      </div>
      <h3 className="text-sm font-bold text-white mb-2">{f.title}</h3>
      <p className="text-xs text-white/40 leading-relaxed mb-3">{f.desc}</p>
      <div className="pt-3 border-t border-white/[0.04]">
        <p className="text-[10px] text-white/25 leading-relaxed italic">{f.detail}</p>
      </div>
    </div>
  </motion.div>
);

export const FeatureExplorer: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="features" ref={ref} className="py-28 px-6 bg-[#03070f] border-t border-white/[0.04]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/[0.08] border border-emerald-500/20 text-xs font-semibold text-emerald-400 mb-5">
            <Cpu className="w-3 h-3" />
            Platform Capabilities
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">Built for Scientific Scale</h2>
          <p className="text-white/40 text-lg max-w-2xl mx-auto">
            Every component engineered specifically for computational toxicology data workflows.
          </p>
        </motion.div>
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => (
            <FeatureCard key={f.title} f={f} i={i} inView={inView} />
          ))}
        </div>
      </div>
    </section>
  );
};
