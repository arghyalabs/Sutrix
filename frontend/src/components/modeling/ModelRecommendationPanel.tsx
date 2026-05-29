import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, AlertCircle, ChevronDown } from 'lucide-react';
import * as Accordion from '@radix-ui/react-accordion';
import type { ModelingAnalysis, ModelRecommendation } from '../../types';

const ROBUSTNESS_COLOR = { HIGH: '#10B981', MEDIUM: '#F59E0B', LOW: '#EF4444' } as const;

const ModelCard: React.FC<{ model: ModelRecommendation; index: number }> = ({ model, index }) => {
  const robColor = ROBUSTNESS_COLOR[model.expected_robustness] || '#6B7280';
  const r = model.suitability_score;
  const circ = 2 * Math.PI * 28;
  const dash = (r / 100) * circ;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07 }}
      className={`rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden ${r >= 70 ? 'ring-1 ring-cyan-500/20' : ''}`}
    >
      {r >= 70 && (
        <div className="px-4 py-1.5 bg-cyan-500/10 border-b border-cyan-500/10">
          <span className="text-[10px] font-semibold text-cyan-400 tracking-wide">✦ RECOMMENDED FOR THIS DATASET</span>
        </div>
      )}
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Score ring */}
          <div className="shrink-0">
            <svg width="68" height="68" className="rotate-[-90deg]">
              <circle cx="34" cy="34" r="28" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
              <motion.circle
                cx="34" cy="34" r="28" fill="none"
                stroke={robColor} strokeWidth="6" strokeLinecap="round"
                strokeDasharray={circ}
                initial={{ strokeDashoffset: circ }}
                animate={{ strokeDashoffset: circ - dash }}
                transition={{ duration: 1, delay: index * 0.07 }}
              />
            </svg>
            <div className="relative" style={{ marginTop: -68 + 6 }}>
              <div className="flex flex-col items-center justify-center" style={{ height: 68 }}>
                <span className="text-lg font-bold" style={{ color: robColor }}>{r}</span>
              </div>
            </div>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h3 className="text-base font-semibold text-white">{model.algorithm}</h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/[0.06] text-white/40 font-medium">{model.category}</span>
              {model.unsupervised && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/10 text-violet-400 font-medium">Unsupervised</span>
              )}
            </div>
            <span
              className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
              style={{ color: robColor, background: `${robColor}18` }}
            >
              {model.expected_robustness} ROBUSTNESS
            </span>
          </div>
        </div>

        <Accordion.Root type="single" collapsible className="mt-4">
          <Accordion.Item value="details">
            <Accordion.Trigger className="w-full flex items-center justify-between text-xs text-white/40 hover:text-white/60 transition-colors group">
              <span>View Details</span>
              <ChevronDown className="w-3.5 h-3.5 group-data-[state=open]:rotate-180 transition-transform" />
            </Accordion.Trigger>
            <Accordion.Content className="overflow-hidden data-[state=open]:animate-in data-[state=closed]:animate-out">
              <div className="pt-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-white/40 mb-2">Advantages</div>
                    <ul className="space-y-1.5">
                      {model.pros.map((p, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-xs text-white/60">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5 shrink-0" />{p}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <div className="text-xs text-white/40 mb-2">Limitations</div>
                    <ul className="space-y-1.5">
                      {model.cons.map((c, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-xs text-white/60">
                          <AlertCircle className="w-3 h-3 text-rose-400 mt-0.5 shrink-0" />{c}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <div className="rounded-lg bg-white/[0.03] p-3 border border-white/[0.04]">
                  <div className="text-xs text-white/40 mb-1">Scientific Reasoning</div>
                  <p className="text-xs text-white/55 leading-relaxed">{model.scientific_reasoning}</p>
                </div>
              </div>
            </Accordion.Content>
          </Accordion.Item>
        </Accordion.Root>
      </div>
    </motion.div>
  );
};

const ModelRecommendationPanel: React.FC<{ data: ModelingAnalysis }> = ({ data }) => (
  <div className="p-6 space-y-6">
    <div>
      <h2 className="text-lg font-semibold text-white">Model Recommendation Engine</h2>
      <p className="text-sm text-white/40 mt-1">Rule-based algorithm selection for your dataset characteristics</p>
    </div>
    {data.models.length === 0 ? (
      <div className="flex items-center justify-center h-48 text-white/40 text-sm">
        No model recommendations available. Ensure your dataset has a target value column mapped.
      </div>
    ) : (
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {data.models.map((m, i) => <ModelCard key={m.algorithm} model={m} index={i} />)}
      </div>
    )}
  </div>
);

export default ModelRecommendationPanel;
