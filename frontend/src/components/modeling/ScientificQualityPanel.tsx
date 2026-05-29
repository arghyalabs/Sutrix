import React from 'react';
import { motion } from 'framer-motion';
import Plot from 'react-plotly.js';
import { AlertTriangle, Info } from 'lucide-react';
import type { ModelingAnalysis } from '../../types';

const SEV_COLOR: Record<string, string> = {
  CRITICAL: '#EF4444', HIGH: '#F59E0B', MEDIUM: '#3B82F6', LOW: '#6B7280'
};

const ScientificQualityPanel: React.FC<{ data: ModelingAnalysis }> = ({ data }) => {
  const { anomalies, funnel, health_score, recommendations } = data.quality;

  const funnelPlotData = [{
    type: 'funnel' as const,
    y: funnel.map(f => f.stage),
    x: funnel.map(f => f.count),
    textinfo: 'value+percent initial' as const,
    marker: {
      color: ['rgba(34,211,238,0.7)', 'rgba(59,130,246,0.7)', 'rgba(139,92,246,0.7)', 'rgba(16,185,129,0.7)'],
    },
    hovertemplate: '<b>%{y}</b><br>%{x} rows<extra></extra>',
  }];

  const healthColor = health_score >= 80 ? '#10B981' : health_score >= 60 ? '#F59E0B' : '#EF4444';

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">Scientific Data Quality</h2>
          <p className="text-sm text-white/40 mt-1">Anomaly detection, conflict analysis, quality funnel</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold" style={{ color: healthColor }}>{health_score}</div>
          <div className="text-xs text-white/40">Health Score</div>
        </div>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="space-y-2">
          {recommendations.map((rec, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.07 }}
              className="flex items-start gap-3 px-4 py-3 rounded-lg bg-white/[0.03] border border-white/[0.06] text-xs text-white/60"
            >
              <Info className="w-3.5 h-3.5 text-cyan-400 mt-0.5 shrink-0" />
              {rec}
            </motion.div>
          ))}
        </div>
      )}

      {/* Funnel chart */}
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4">
        <h3 className="text-sm font-semibold text-white/70 mb-3">Data Quality Funnel</h3>
        <Plot
          data={funnelPlotData as any}
          layout={{
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            height: 280,
            margin: { t: 10, b: 10, l: 10, r: 10 },
            font: { color: 'rgba(255,255,255,0.5)', family: 'Inter, sans-serif', size: 11 },
            showlegend: false,
          } as any}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
          useResizeHandler
        />
      </div>

      {/* Anomaly table */}
      {anomalies.length > 0 ? (
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
          <div className="px-5 py-3 border-b border-white/[0.06]">
            <h3 className="text-sm font-semibold text-white/80 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Detected Anomalies ({anomalies.length})
            </h3>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {anomalies.map((a, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                className="px-5 py-3 flex items-start gap-4"
              >
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 mt-0.5"
                  style={{ color: SEV_COLOR[a.severity] || '#6B7280', background: `${SEV_COLOR[a.severity] || '#6B7280'}18` }}
                >
                  {a.severity}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-white/70">{a.type}</div>
                  <p className="text-xs text-white/40 mt-0.5 leading-relaxed">{a.description}</p>
                  <p className="text-xs text-cyan-400/60 mt-1">→ {a.suggested_action}</p>
                </div>
                <div className="text-xs text-white/30 shrink-0">{a.affected_rows} rows</div>
              </motion.div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-3 px-5 py-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] text-sm text-emerald-400">
          <span className="text-lg">✓</span> No significant anomalies detected. Dataset quality is acceptable.
        </div>
      )}
    </div>
  );
};

export default ScientificQualityPanel;
