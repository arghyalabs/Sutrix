import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Cpu, Activity, Database, Network, BarChart3, Shield, GitBranch } from 'lucide-react';

const badges = [
  { label: 'WebSocket Streaming', icon: <Activity className="w-3.5 h-3.5" />, color: 'text-cyan-400', bg: 'bg-cyan-500/[0.07]', border: 'border-cyan-500/15' },
  { label: 'Parallel RDKit Engine', icon: <Cpu className="w-3.5 h-3.5" />, color: 'text-violet-400', bg: 'bg-violet-500/[0.07]', border: 'border-violet-500/15' },
  { label: 'React Virtualization', icon: <Zap className="w-3.5 h-3.5" />, color: 'text-amber-400', bg: 'bg-amber-500/[0.07]', border: 'border-amber-500/15' },
  { label: 'Plotly Analytics', icon: <BarChart3 className="w-3.5 h-3.5" />, color: 'text-blue-400', bg: 'bg-blue-500/[0.07]', border: 'border-blue-500/15' },
  { label: 'Parquet Optimization', icon: <Database className="w-3.5 h-3.5" />, color: 'text-emerald-400', bg: 'bg-emerald-500/[0.07]', border: 'border-emerald-500/15' },
  { label: 'Async Background Workers', icon: <Network className="w-3.5 h-3.5" />, color: 'text-pink-400', bg: 'bg-pink-500/[0.07]', border: 'border-pink-500/15' },
  { label: 'OECD Compliance Checks', icon: <Shield className="w-3.5 h-3.5" />, color: 'text-teal-400', bg: 'bg-teal-500/[0.07]', border: 'border-teal-500/15' },
  { label: 'DAG Lineage Engine', icon: <GitBranch className="w-3.5 h-3.5" />, color: 'text-rose-400', bg: 'bg-rose-500/[0.07]', border: 'border-rose-500/15' },
];

export const TechStrip: React.FC = () => (
  <section className="py-14 border-t border-white/[0.04] bg-[#03070f]">
    <p className="text-center text-[10px] font-bold uppercase tracking-widest text-white/20 mb-7">
      Powered By
    </p>
    <div className="flex gap-3 flex-wrap justify-center px-6 max-w-4xl mx-auto">
      {badges.map((b, i) => (
        <motion.div
          key={b.label}
          initial={{ opacity: 0, scale: 0.88 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: i * 0.05 }}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border ${b.border} ${b.bg} ${b.color}`}
        >
          {b.icon}
          <span className="text-xs font-semibold">{b.label}</span>
        </motion.div>
      ))}
    </div>
  </section>
);
