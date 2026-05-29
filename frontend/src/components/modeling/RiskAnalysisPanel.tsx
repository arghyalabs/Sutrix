import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import Plot from 'react-plotly.js';
import { ChevronDown } from 'lucide-react';
import type { ModelingAnalysis, Risk } from '../../types';

const SEV = { CRITICAL: '#EF4444', HIGH: '#F59E0B', MEDIUM: '#3B82F6', LOW: '#6B7280' } as const;
const SEV_SIZE = { CRITICAL: 28, HIGH: 22, MEDIUM: 16, LOW: 12 } as const;
const SEV_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 } as const;

const RiskAnalysisPanel: React.FC<{ data: ModelingAnalysis }> = ({ data }) => {
  const risks = [...data.risks].sort((a, b) =>
    (SEV_ORDER[a.severity as keyof typeof SEV_ORDER] ?? 4) - (SEV_ORDER[b.severity as keyof typeof SEV_ORDER] ?? 4)
  );
  const [expanded, setExpanded] = useState<string | null>(null);

  const bubbleData = useMemo(() => [{
    type: 'scatter' as const,
    x: risks.map(r => r.probability),
    y: risks.map((_, i) => i + 1),
    mode: 'markers' as const,
    marker: {
      size: risks.map(r => SEV_SIZE[r.severity as keyof typeof SEV_SIZE] || 12),
      color: risks.map(r => SEV[r.severity as keyof typeof SEV] || '#6B7280'),
      opacity: 0.85,
      line: { color: 'rgba(255,255,255,0.1)', width: 1 },
    },
    text: risks.map(r => r.risk),
    hovertemplate: '<b>%{text}</b><br>Probability: %{x:.0%}<extra></extra>',
  }], [risks]);

  const counts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
  risks.forEach(r => { counts[r.severity as keyof typeof counts] = (counts[r.severity as keyof typeof counts] || 0) + 1; });

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Modeling Risk Analysis</h2>
          <p className="text-sm text-white/40 mt-1">Identified risks with probability estimates and mitigations</p>
        </div>
        <div className="flex gap-2">
          {(Object.entries(counts) as [keyof typeof counts, number][])
            .filter(([, c]) => c > 0)
            .map(([sev, c]) => (
              <span key={sev} className="text-[10px] font-bold px-2 py-1 rounded-full"
                style={{ color: SEV[sev], background: `${SEV[sev]}18`, border: `1px solid ${SEV[sev]}30` }}>
                {c} {sev}
              </span>
            ))
          }
        </div>
      </div>

      {risks.length === 0 ? (
        <div className="flex items-center gap-3 px-5 py-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] text-sm text-emerald-400">
          <span className="text-lg">✓</span> No significant modeling risks detected.
        </div>
      ) : (
        <>
          {/* Bubble chart */}
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
            <p className="text-xs text-white/30 mb-2">Risk Probability Distribution</p>
            <Plot
              data={bubbleData as any}
              layout={{
                paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
                height: 220,
                margin: { t: 10, b: 30, l: 30, r: 10 },
                xaxis: {
                  title: { text: 'Probability', font: { color: 'rgba(255,255,255,0.3)', size: 10 } },
                  tickformat: '.0%', range: [0, 1.05],
                  gridcolor: 'rgba(255,255,255,0.04)', tickfont: { color: 'rgba(255,255,255,0.3)', size: 9 },
                },
                yaxis: { visible: false },
                showlegend: false,
                font: { family: 'Inter, sans-serif' },
              } as any}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </div>

          {/* Risk cards */}
          <div className="space-y-3">
            {risks.map((risk) => {
              const isOpen = expanded === risk.risk;
              const color = SEV[risk.severity as keyof typeof SEV] || '#6B7280';
              return (
                <motion.div
                  key={risk.risk}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="rounded-xl border overflow-hidden"
                  style={{ borderColor: `${color}25`, background: `${color}06` }}
                >
                  <button
                    className="w-full flex items-center gap-4 px-5 py-4 text-left"
                    onClick={() => setExpanded(isOpen ? null : risk.risk)}
                  >
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                      style={{ color, background: `${color}18` }}>
                      {risk.severity}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-white/80">{risk.risk}</div>
                      <div className="text-xs text-white/40 mt-0.5">
                        {Math.round(risk.probability * 100)}% probability · {risk.affected_stage}
                      </div>
                    </div>
                    <ChevronDown className={`w-4 h-4 text-white/30 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                  </button>
                  {isOpen && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="border-t border-white/[0.06] px-5 py-4 space-y-3"
                    >
                      <div>
                        <div className="text-xs text-white/40 mb-1">Impact</div>
                        <p className="text-xs text-white/60 leading-relaxed">{risk.impact}</p>
                      </div>
                      <div>
                        <div className="text-xs text-white/40 mb-1">Mitigation Strategy</div>
                        <p className="text-xs text-cyan-300/70 leading-relaxed">{risk.mitigation}</p>
                      </div>
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default RiskAnalysisPanel;
