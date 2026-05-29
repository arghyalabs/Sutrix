import React, { useRef, useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { CheckCircle, AlertTriangle, TrendingUp, Shield } from 'lucide-react';

const readinessScore = 78;

const indicators = [
  { label: 'Class Balance', score: 72, status: 'warn', icon: <TrendingUp className="w-3.5 h-3.5" />, detail: 'Moderate imbalance (3.2:1 ratio)' },
  { label: 'Feature Variance', score: 91, status: 'ok', icon: <CheckCircle className="w-3.5 h-3.5" />, detail: 'All features above 0.01 threshold' },
  { label: 'Multicollinearity', score: 63, status: 'warn', icon: <AlertTriangle className="w-3.5 h-3.5" />, detail: '14 correlated pairs (r > 0.90)' },
  { label: 'Sample Size', score: 89, status: 'ok', icon: <CheckCircle className="w-3.5 h-3.5" />, detail: '412 samples — adequate for QSAR' },
  { label: 'Scaffold Diversity', score: 84, status: 'ok', icon: <CheckCircle className="w-3.5 h-3.5" />, detail: 'BM scaffold diversity: 78%' },
  { label: 'Missing Values', score: 95, status: 'ok', icon: <CheckCircle className="w-3.5 h-3.5" />, detail: '< 2% missing across all features' },
];

const modelSuggestions = [
  { type: 'Random Forest', fit: 'Excellent', reason: 'Handles feature correlation, large descriptor spaces', color: 'text-emerald-400', bg: 'bg-emerald-500/[0.06]', border: 'border-emerald-500/15' },
  { type: 'Ridge Regression', fit: 'Good', reason: 'Effective with multicollinear RDKit descriptors', color: 'text-cyan-400', bg: 'bg-cyan-500/[0.06]', border: 'border-cyan-500/15' },
  { type: 'XGBoost', fit: 'Excellent', reason: 'Robust to class imbalance with sample weighting', color: 'text-emerald-400', bg: 'bg-emerald-500/[0.06]', border: 'border-emerald-500/15' },
  { type: 'SVM (RBF)', fit: 'Moderate', reason: 'Consider dimensionality reduction first', color: 'text-amber-400', bg: 'bg-amber-500/[0.06]', border: 'border-amber-500/15' },
];

const GaugeArc: React.FC<{ score: number; inView: boolean }> = ({ score, inView }) => {
  const radius = 54;
  const circumference = Math.PI * radius; // half circle
  const progress = inView ? (score / 100) * circumference : 0;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div className="relative flex items-center justify-center">
      <svg width="160" height="90" viewBox="0 0 160 90">
        {/* Track */}
        <path
          d="M 16 84 A 64 64 0 0 1 144 84"
          fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10" strokeLinecap="round"
        />
        {/* Progress */}
        <motion.path
          d="M 16 84 A 64 64 0 0 1 144 84"
          fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: inView ? circumference - progress : circumference }}
          transition={{ duration: 1.5, delay: 0.3, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute bottom-0 flex flex-col items-center">
        <motion.span
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 0.5 }}
          className="text-3xl font-extrabold"
          style={{ color }}
        >
          {inView ? score : 0}
        </motion.span>
        <span className="text-[9px] font-bold uppercase tracking-widest text-white/30 mt-0.5">Readiness</span>
      </div>
    </div>
  );
};

export const AIReadinessPreview: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section ref={ref} className="py-28 px-6 bg-[#03070f] border-t border-white/[0.04]">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-pink-500/[0.08] border border-pink-500/20 text-xs font-semibold text-pink-400 mb-5">
            <Shield className="w-3 h-3" />
            AI Readiness Engine
          </div>
          <h2 className="text-4xl font-extrabold text-white mb-4">QSAR Modeling Readiness Analysis</h2>
          <p className="text-white/40 text-lg max-w-2xl mx-auto">
            Before any model training, the platform evaluates dataset fitness with OECD-inspired quality checks.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Gauge card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.1 }}
            className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-6 flex flex-col items-center gap-4"
          >
            <p className="text-[10px] font-bold uppercase tracking-widest text-white/30">Overall Score</p>
            <GaugeArc score={readinessScore} inView={inView} />
            <div className="w-full p-3 rounded-xl bg-amber-500/[0.06] border border-amber-500/15">
              <p className="text-[10px] font-bold uppercase tracking-widest text-amber-400/70 mb-1">Verdict</p>
              <p className="text-xs text-white/60">Dataset is <span className="text-amber-400 font-semibold">conditionally suitable</span> for QSAR. Address multicollinearity before training.</p>
            </div>
          </motion.div>

          {/* Indicator bars */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.15 }}
            className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-6"
          >
            <p className="text-xs font-bold text-white/50 mb-4">Quality Indicators</p>
            <div className="space-y-3">
              {indicators.map((ind, i) => (
                <motion.div
                  key={ind.label}
                  initial={{ opacity: 0, x: -10 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: 0.2 + i * 0.07 }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className={`flex items-center gap-1.5 ${ ind.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {ind.icon}
                      <span className="text-[10px] font-semibold text-white/60">{ind.label}</span>
                    </div>
                    <span className={`text-[10px] font-bold ${ ind.status === 'ok' ? 'text-emerald-400' : 'text-amber-400'}`}>{ind.score}</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/[0.04] overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={inView ? { width: `${ind.score}%` } : {}}
                      transition={{ delay: 0.3 + i * 0.07, duration: 0.8, ease: 'easeOut' }}
                      className={`h-full rounded-full ${ ind.status === 'ok' ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : 'bg-gradient-to-r from-amber-500 to-amber-400'}`}
                    />
                  </div>
                  <p className="text-[9px] text-white/25 mt-0.5">{ind.detail}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Model suggestions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: 0.2 }}
            className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-6"
          >
            <p className="text-xs font-bold text-white/50 mb-4">Model Recommendations</p>
            <div className="space-y-3">
              {modelSuggestions.map((m, i) => (
                <motion.div
                  key={m.type}
                  initial={{ opacity: 0, y: 8 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{ delay: 0.3 + i * 0.1 }}
                  className={`p-3 rounded-xl border ${m.border} ${m.bg}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-white/70">{m.type}</span>
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${m.bg} ${m.color} border ${m.border}`}>{m.fit}</span>
                  </div>
                  <p className="text-[10px] text-white/30 leading-relaxed">{m.reason}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
