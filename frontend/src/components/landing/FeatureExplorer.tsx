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
    icon: <Cpu className="w-5 h-5" />,
    title: 'Scientific Variable Intelligence',
    tag: 'Ontology Engine',
    desc: 'Automatically maps thousands of scientific column variants.',
    detail: 'Resolves messy headers across pharmacology, drug discovery, chemistry, omics, and clinical research dynamically.',
    color: 'rgba(34,211,238,0.4)', textColor: 'text-cyan-400',
    bgColor: 'bg-cyan-500/[0.05]', borderColor: 'border-cyan-500/[0.12]',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: 'QSAR Readiness Engine',
    tag: 'Validation',
    desc: 'Evaluates dataset suitability before model development.',
    detail: 'Flags structural duplicates, missing SMILES, and severe data gaps before machine learning pipelines are run.',
    color: 'rgba(244,114,182,0.4)', textColor: 'text-pink-400',
    bgColor: 'bg-pink-500/[0.05]', borderColor: 'border-pink-500/[0.12]',
  },
  {
    icon: <Layers className="w-5 h-5" />,
    title: 'OECD Compliance Evaluation',
    tag: 'Regulatory',
    desc: 'Checks readiness against QSAR best practices.',
    detail: 'Generates detailed audit checklists against the 5 OECD principles, including defined endpoints and mechanistic basis.',
    color: 'rgba(167,139,250,0.4)', textColor: 'text-violet-400',
    bgColor: 'bg-violet-500/[0.05]', borderColor: 'border-violet-500/[0.12]',
  },
  {
    icon: <Database className="w-5 h-5" />,
    title: 'Compound Explorer',
    tag: 'Interactive',
    desc: 'Search and inspect every compound interactively.',
    detail: 'Google-style live search and on-demand 2D chemical structure rendering using RDKit backend engines.',
    color: 'rgba(96,165,250,0.4)', textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/[0.05]', borderColor: 'border-blue-500/[0.12]',
  },
  {
    icon: <Zap className="w-5 h-5" />,
    title: 'Descriptor Intelligence',
    tag: 'Calculation',
    desc: 'Identify generated and missing descriptor families.',
    detail: 'Groups molecular features into Constitutional, Physicochemical, Topological, Electronic, and Fingerprints.',
    color: 'rgba(251,191,36,0.4)', textColor: 'text-amber-400',
    bgColor: 'bg-amber-500/[0.05]', borderColor: 'border-amber-500/[0.12]',
  },
  {
    icon: <Activity className="w-5 h-5" />,
    title: 'Predictive Modeling Readiness',
    tag: 'AI/Modeling',
    desc: 'Assess data quality, diversity, imbalance, variance and modeling feasibility.',
    detail: 'Analyzes class balance entropy, checks feature variance threshold, and recommends optimal modeling algorithms.',
    color: 'rgba(251,146,60,0.4)', textColor: 'text-orange-400',
    bgColor: 'bg-orange-500/[0.05]', borderColor: 'border-orange-500/[0.12]',
  },
  {
    icon: <Network className="w-5 h-5" />,
    title: 'Hierarchical Dataset Segregation',
    tag: 'Lineage',
    desc: 'Recursive lineage-aware DAG partitioning.',
    detail: 'Prevents dataframe contamination by maintaining parent-child lineage logic through filtered sub-nodes.',
    color: 'rgba(45,212,191,0.4)', textColor: 'text-teal-400',
    bgColor: 'bg-teal-500/[0.05]', borderColor: 'border-teal-500/[0.12]',
  },
  {
    icon: <Download className="w-5 h-5" />,
    title: 'Export Automation',
    tag: 'Output',
    desc: 'One-click download of Parquet, curated XLSX, and ZIP structure archives.',
    detail: 'Ensures structured export packages mirror the exact lineage hierarchy nodes for regulatory review.',
    color: 'rgba(52,211,153,0.4)', textColor: 'text-emerald-400',
    bgColor: 'bg-emerald-500/[0.05]', borderColor: 'border-emerald-500/[0.12]',
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
