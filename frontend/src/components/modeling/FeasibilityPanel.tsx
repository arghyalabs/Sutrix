import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import Plot from 'react-plotly.js';
import type { ModelingAnalysis } from '../../types';

const FeasibilityPanel: React.FC<{ data: ModelingAnalysis }> = ({ data }) => {
  const { axes, values, confidence_lower, confidence_upper, interpretation, mean_score } = data.feasibility;

  const scoreColor = mean_score >= 70 ? '#10B981' : mean_score >= 50 ? '#F59E0B' : '#EF4444';

  const plotData = useMemo(() => [
    // Confidence band (upper)
    {
      type: 'scatterpolar' as const,
      r: [...confidence_upper, confidence_upper[0]],
      theta: [...axes, axes[0]],
      fill: 'toself',
      fillcolor: 'rgba(34,211,238,0.05)',
      line: { color: 'transparent' },
      name: 'Confidence Band',
      showlegend: false,
      hoverinfo: 'skip' as const,
    },
    // Confidence band (lower)
    {
      type: 'scatterpolar' as const,
      r: [...confidence_lower, confidence_lower[0]],
      theta: [...axes, axes[0]],
      fill: 'toself',
      fillcolor: 'rgba(10,15,30,1)',
      line: { color: 'transparent' },
      showlegend: false,
      hoverinfo: 'skip' as const,
    },
    // Main values
    {
      type: 'scatterpolar' as const,
      r: [...values, values[0]],
      theta: [...axes, axes[0]],
      fill: 'toself',
      fillcolor: 'rgba(34,211,238,0.15)',
      line: { color: '#22D3EE', width: 2 },
      name: 'Feasibility',
      marker: { color: '#22D3EE', size: 6 },
      hovertemplate: '<b>%{theta}</b><br>Score: %{r}<extra></extra>',
    },
  ], [axes, values, confidence_lower, confidence_upper]);

  const layout = useMemo(() => ({
    polar: {
      bgcolor: 'transparent',
      radialaxis: {
        visible: true,
        range: [0, 100],
        tickfont: { color: 'rgba(255,255,255,0.3)', size: 10 },
        gridcolor: 'rgba(255,255,255,0.06)',
        linecolor: 'rgba(255,255,255,0.06)',
      },
      angularaxis: {
        tickfont: { color: 'rgba(255,255,255,0.6)', size: 11 },
        gridcolor: 'rgba(255,255,255,0.06)',
        linecolor: 'rgba(255,255,255,0.06)',
      },
    },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    showlegend: false,
    margin: { t: 20, b: 20, l: 40, r: 40 },
    height: 380,
    font: { family: 'Inter, sans-serif' },
  }), []);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Predictive Modeling Feasibility</h2>
        <p className="text-sm text-white/40 mt-1">Heuristic-based assessment — not a validated ML accuracy estimate</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {axes.map((axis, i) => {
          const v = values[i];
          const col = v >= 70 ? '#10B981' : v >= 50 ? '#F59E0B' : '#EF4444';
          return (
            <motion.div
              key={axis}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3"
            >
              <div className="text-xs text-white/40 mb-1">{axis}</div>
              <div className="text-xl font-bold" style={{ color: col }}>{v}</div>
              <div className="h-1 mt-2 rounded-full bg-white/[0.06]">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: col }}
                  initial={{ width: 0 }}
                  animate={{ width: `${v}%` }}
                  transition={{ duration: 0.8, delay: i * 0.08 }}
                />
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-2">
        <Plot
          data={plotData as any}
          layout={layout as any}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>

      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
        className="rounded-xl p-5 border"
        style={{
          borderColor: `${scoreColor}30`,
          background: `${scoreColor}08`,
        }}
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="text-2xl font-bold" style={{ color: scoreColor }}>{Math.round(mean_score)}</div>
          <div>
            <div className="text-xs text-white/40">Mean Feasibility Score</div>
            <div className="text-sm font-medium text-white/70">
              {mean_score >= 70 ? 'Strong' : mean_score >= 50 ? 'Moderate' : 'Limited'} Modeling Potential
            </div>
          </div>
        </div>
        <p className="text-sm text-white/50 leading-relaxed">{interpretation}</p>
      </motion.div>
    </div>
  );
};

export default FeasibilityPanel;
