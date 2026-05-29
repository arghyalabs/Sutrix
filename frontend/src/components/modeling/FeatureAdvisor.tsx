import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Code2, CheckSquare } from 'lucide-react';
import type { ModelingAnalysis, FeatureRecommendation } from '../../types';

const SEVERITY_CFG = {
  CRITICAL: { color: '#EF4444', bg: 'rgba(239,68,68,0.10)', border: 'rgba(239,68,68,0.20)', label: 'CRITICAL' },
  HIGH:     { color: '#F59E0B', bg: 'rgba(245,158,11,0.10)', border: 'rgba(245,158,11,0.20)', label: 'HIGH' },
  MEDIUM:   { color: '#3B82F6', bg: 'rgba(59,130,246,0.10)', border: 'rgba(59,130,246,0.20)', label: 'MEDIUM' },
  LOW:      { color: '#6B7280', bg: 'rgba(107,114,128,0.10)', border: 'rgba(107,114,128,0.20)', label: 'LOW' },
} as const;

const FeatureCard: React.FC<{ rec: FeatureRecommendation; index: number }> = ({ rec, index }) => {
  const [expanded, setExpanded] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const cfg = SEVERITY_CFG[rec.severity] || SEVERITY_CFG.LOW;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`rounded-xl border overflow-hidden transition-opacity ${reviewed ? 'opacity-40' : ''}`}
      style={{ borderColor: cfg.border, background: cfg.bg }}
    >
      <button
        className="w-full flex items-start gap-4 px-5 py-4 text-left"
        onClick={() => setExpanded(p => !p)}
      >
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-full mt-0.5 shrink-0"
          style={{ color: cfg.color, background: `${cfg.color}18`, border: `1px solid ${cfg.border}` }}
        >
          {cfg.label}
        </span>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-white/80">{rec.action}</div>
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {rec.affected_columns.slice(0, 4).map(col => (
              <span key={col} className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-white/40">{col}</span>
            ))}
            {rec.affected_count > 4 && (
              <span className="text-[10px] text-white/30">+{rec.affected_count - 4} more</span>
            )}
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-white/30 shrink-0 transition-transform mt-0.5 ${expanded ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden border-t border-white/[0.06]"
          >
            <div className="px-5 py-4 space-y-3">
              <div>
                <div className="text-xs text-white/40 mb-1">Scientific Reasoning</div>
                <p className="text-xs text-white/60 leading-relaxed">{rec.reasoning}</p>
              </div>
              <div>
                <div className="text-xs text-white/40 mb-1">Expected Impact</div>
                <p className="text-xs text-white/60">{rec.expected_impact}</p>
              </div>
              {rec.code_hint && (
                <div>
                  <div className="text-xs text-white/40 mb-1.5 flex items-center gap-1.5">
                    <Code2 className="w-3 h-3" /> Code Hint
                  </div>
                  <pre className="text-[10px] font-mono p-3 rounded-lg bg-black/30 text-cyan-300 overflow-x-auto whitespace-pre-wrap">
                    {rec.code_hint}
                  </pre>
                </div>
              )}
              <button
                onClick={(e) => { e.stopPropagation(); setReviewed(p => !p); }}
                className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg transition-colors ${reviewed ? 'text-emerald-400 bg-emerald-500/10' : 'text-white/40 hover:text-white/60 bg-white/[0.04]'}`}
              >
                <CheckSquare className="w-3.5 h-3.5" />
                {reviewed ? 'Marked as Reviewed' : 'Mark as Reviewed'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const FeatureAdvisor: React.FC<{ data: ModelingAnalysis }> = ({ data }) => {
  const features = data.features;
  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  features.forEach(f => { counts[f.severity] = (counts[f.severity] || 0) + 1; });

  if (features.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-white/40">
        <p className="text-sm">No feature engineering recommendations.</p>
        <p className="text-xs mt-1">Your dataset appears well-prepared for modeling.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Feature Engineering Advisor</h2>
          <p className="text-sm text-white/40 mt-1">Automated preprocessing recommendations, priority-ordered</p>
        </div>
        <div className="flex gap-2">
          {(Object.entries(counts) as [keyof typeof counts, number][])
            .filter(([, c]) => c > 0)
            .map(([sev, c]) => (
              <span
                key={sev}
                className="text-[10px] font-bold px-2 py-1 rounded-full"
                style={{
                  color: SEVERITY_CFG[sev].color,
                  background: SEVERITY_CFG[sev].bg,
                  border: `1px solid ${SEVERITY_CFG[sev].border}`,
                }}
              >
                {c} {sev}
              </span>
            ))
          }
        </div>
      </div>
      <div className="space-y-3">
        {features.map((rec, i) => (
          <FeatureCard key={rec.id} rec={rec} index={i} />
        ))}
      </div>
    </div>
  );
};

export default FeatureAdvisor;
