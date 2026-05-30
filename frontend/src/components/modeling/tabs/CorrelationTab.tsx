import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill, StatusBadge
} from './shared';

interface CorrelationTabProps { clientId: string }

const runCorrelation = (clientId: string) => readinessApi.runCorrelation(clientId) as Promise<any>;

export const CorrelationTab: React.FC<CorrelationTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'correlation', runCorrelation
  );
  const [matrixType, setMatrixType] = useState<'pearson' | 'spearman'>('pearson');
  const [threshold, setThreshold] = useState(0.90);

  const matrixData = data ? data[matrixType] : null;
  const pairs = (data?.high_correlation_pairs ?? []).filter(
    (p: any) => Math.abs(p.pearson_r) >= threshold
  );

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Correlation Analysis"
        subtitle="Pearson & Spearman correlation matrices — identify redundant descriptor pairs"
      >
        <RunButton label="Run Correlation" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Correlation" onRun={run} />}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <StatPill label="Features Analyzed" value={matrixData?.labels?.length ?? '—'} />
            <StatPill label="High-Corr Pairs" value={pairs.length} color={pairs.length > 0 ? 'text-amber-400' : 'text-emerald-400'} />
            <StatPill label="Recommended Drops" value={data.recommended_drops?.length ?? 0} color="text-rose-400" />
          </div>

          {/* Matrix type toggle + threshold */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.05]">
              {(['pearson', 'spearman'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setMatrixType(t)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors
                    ${matrixType === t ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/30 hover:text-white/50'}`}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2 text-xs text-white/40">
              <span>Threshold:</span>
              <input
                type="range" min="0.75" max="0.99" step="0.01"
                value={threshold}
                onChange={e => setThreshold(parseFloat(e.target.value))}
                className="w-28 accent-cyan-400"
              />
              <span className="text-cyan-400 font-mono w-8">{threshold.toFixed(2)}</span>
            </div>
          </div>

          {/* Heatmap placeholder (Plotly would load here if available) */}
          {matrixData && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-3">
                {matrixType === 'pearson' ? 'Pearson' : 'Spearman'} Correlation Matrix
                — {matrixData.labels?.length ?? 0} features (top by variance)
              </p>
              {/* Mini heatmap: show color squares for first 10×10 */}
              <div className="overflow-x-auto">
                <div className="grid" style={{ gridTemplateColumns: `80px repeat(${Math.min(10, matrixData.labels?.length ?? 0)}, 1fr)`, gap: 2 }}>
                  <div />
                  {(matrixData.labels ?? []).slice(0, 10).map((l: string) => (
                    <div key={l} className="text-[8px] text-white/30 truncate text-center pb-1" title={l}>{l.slice(0, 6)}</div>
                  ))}
                  {(matrixData.labels ?? []).slice(0, 10).map((rowLabel: string, ri: number) => (
                    <React.Fragment key={rowLabel}>
                      <div className="text-[8px] text-white/30 truncate pr-1 flex items-center" title={rowLabel}>{rowLabel.slice(0, 10)}</div>
                      {(matrixData.z?.[ri] ?? []).slice(0, 10).map((val: number, ci: number) => {
                        const v = Math.max(-1, Math.min(1, val));
                        const intensity = Math.abs(v);
                        const bg = v > 0
                          ? `rgba(34, 211, 238, ${intensity * 0.7})`
                          : `rgba(244, 63, 94, ${intensity * 0.7})`;
                        return (
                          <div
                            key={ci}
                            title={`${rowLabel} × ${matrixData.labels?.[ci]}: ${v.toFixed(3)}`}
                            style={{ background: bg, minHeight: 20, borderRadius: 2 }}
                          />
                        );
                      })}
                    </React.Fragment>
                  ))}
                </div>
                <p className="text-[10px] text-white/20 mt-2">
                  Showing 10×10 preview. Cyan = positive correlation, Rose = negative correlation.
                </p>
              </div>
            </GlassCard>
          )}

          {/* Redundancy pairs table */}
          {pairs.length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-3">
                {pairs.length} Redundant Pair{pairs.length !== 1 ? 's' : ''} at r ≥ {threshold.toFixed(2)}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-white/25 border-b border-white/[0.05] text-left">
                      <th className="py-2 pr-4">Feature 1</th>
                      <th className="py-2 pr-4">Feature 2</th>
                      <th className="py-2 pr-4">r</th>
                      <th className="py-2">Recommendation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pairs.slice(0, 100).map((p: any, i: number) => (
                      <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.01]">
                        <td className="py-1.5 pr-4 text-white/60 font-mono">{p.feat1}</td>
                        <td className="py-1.5 pr-4 text-white/60 font-mono">{p.feat2}</td>
                        <td className={`py-1.5 pr-4 font-mono font-bold ${Math.abs(p.pearson_r) > 0.95 ? 'text-rose-400' : 'text-amber-400'}`}>
                          {p.pearson_r?.toFixed(3)}
                        </td>
                        <td className="py-1.5 text-white/35 max-w-[260px] truncate">{p.recommendation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          )}
        </>
      )}
    </motion.div>
  );
};
