import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Layers } from 'lucide-react';
import { VisualizationWorkspace } from '../charts/VisualizationWorkspace';

interface ReadinessDashboardProps {
  score: number;
  tier: string;
  deductions: string[];
  findings: string[];
  isRecalculating: boolean;
  handleRecalculate: () => Promise<void>;
  pcaData: any;
}

export const ReadinessDashboard: React.FC<ReadinessDashboardProps> = ({
  score,
  tier,
  deductions,
  findings,
  isRecalculating,
  handleRecalculate,
  pcaData
}) => {
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  
  const getScoreColor = (s: number) => {
    if (s >= 90) return '#10B981'; // emerald
    if (s >= 70) return '#F59E0B'; // amber
    return '#F43F5E'; // rose
  };

  return (
    <div className="py-2">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-3">Model Readiness</h1>
        <p className="text-secondary text-sm max-w-lg mx-auto">
          Final OECD-compliant topological assessment before downstream 3D visualization.
        </p>
      </div>

      <div className="grid md:grid-cols-12 gap-6 mb-8">
        
        {/* Left: Score Gauge */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="md:col-span-5 glass p-8 rounded-3xl flex flex-col items-center justify-center text-center relative"
        >
          <h3 className="text-white font-medium mb-6">Readiness Score</h3>
          
          <div className="relative w-48 h-48 flex items-center justify-center mb-6">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 140 140">
              <circle
                cx="70" cy="70" r={radius}
                className="stroke-white/[0.04] fill-none" strokeWidth="8"
              />
              <motion.circle
                cx="70" cy="70" r={radius}
                className="fill-none drop-shadow-[0_0_15px_rgba(255,255,255,0.1)]"
                strokeWidth="8"
                strokeLinecap="round"
                stroke={getScoreColor(score)}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 1.5, ease: "easeOut" }}
                style={{ strokeDasharray: circumference }}
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-5xl font-extrabold text-white tracking-tighter">{score}</span>
              <span className="text-xs text-muted font-medium mt-1">/ 100</span>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/[0.03] border border-white/[0.06] mb-6">
            <span className="text-xs text-secondary uppercase tracking-wider font-semibold">Tier</span>
            <span className="text-sm font-bold text-white">{tier}</span>
          </div>

          <button
            onClick={handleRecalculate}
            disabled={isRecalculating}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white text-xs font-semibold hover:bg-white/[0.08] disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRecalculating ? 'animate-spin' : ''}`} />
            Recalculate Audit
          </button>
        </motion.div>

        {/* Right: Findings list */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="md:col-span-7 glass p-8 rounded-3xl flex flex-col"
        >
          <div className="flex items-center gap-3 mb-6 pb-6 border-b border-white/[0.06]">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-white font-medium">Diagnostic Findings</h3>
              <p className="text-xs text-muted">Issues impacting model readiness</p>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto pr-2 space-y-3">
            {deductions.length === 0 && findings.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mb-4" />
                <p className="text-white font-medium">Perfect Score</p>
                <p className="text-xs text-secondary">No multicollinearity or sparsity detected.</p>
              </div>
            ) : (
              <>
                {deductions.map((d, i) => (
                  <div key={`d-${i}`} className="flex items-start gap-3 p-3 rounded-xl bg-rose-500/[0.02] border border-rose-500/10">
                    <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-secondary leading-relaxed">{d}</p>
                  </div>
                ))}
                {findings.map((f, i) => (
                  <div key={`f-${i}`} className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/[0.02] border border-amber-500/10">
                    <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <p className="text-sm text-secondary leading-relaxed">{f}</p>
                  </div>
                ))}
              </>
            )}
          </div>
        </motion.div>
      </div>

      <div className="mt-12">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center text-cyan-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-white font-medium">Data Visualization</h3>
            <p className="text-xs text-muted">Interactive topology exploration</p>
          </div>
        </div>
        
        <div className="glass rounded-3xl overflow-hidden p-1">
          <VisualizationWorkspace pcaData={pcaData} />
        </div>
      </div>
    </div>
  );
};
