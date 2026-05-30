import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill
} from './shared';

interface OutlierTabProps { clientId: string }
const runOutliers = (clientId: string) => readinessApi.runOutliers(clientId) as Promise<any>;

const METHODS = ['All', 'IsolationForest', 'LOF', 'ZScore', 'IQR'] as const;
type Method = typeof METHODS[number];

export const OutlierTab: React.FC<OutlierTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'outliers', runOutliers
  );
  const [method, setMethod] = useState<Method>('All');

  const compounds = React.useMemo(() => {
    if (!data?.compound_risk_scores) return [];
    let list = [...data.compound_risk_scores].filter((c: any) => c.risk_score > 0);
    if (method !== 'All') {
      list = list.filter((c: any) => (c.flagged_by ?? []).includes(method));
    }
    return list.sort((a: any, b: any) => b.risk_score - a.risk_score);
  }, [data, method]);

  const histData = React.useMemo(() => {
    if (!data?.risk_distribution) return [];
    const { bins, counts } = data.risk_distribution;
    return (bins ?? []).slice(0, -1).map((b: number, i: number) => ({
      bin: b.toFixed(2),
      count: counts?.[i] ?? 0,
    }));
  }, [data]);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Outlier Intelligence"
        subtitle="Multi-method outlier detection: IsolationForest · LOF · Z-Score · IQR"
      >
        <RunButton label="Run Outlier Analysis" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Outlier Analysis" onRun={run} />}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <StatPill label="Outlier Density" value={`${(data.outlier_density_pct ?? 0).toFixed(1)}%`} color="text-amber-400" />
            <StatPill label="High Risk" value={data.high_risk_count ?? 0} color="text-rose-400" />
            <StatPill label="Analyzed" value={data.n_samples?.toLocaleString() ?? '—'} />
          </div>

          {/* Method counts */}
          <div className="flex gap-2 flex-wrap">
            {Object.entries(data.method_counts ?? {}).map(([m, count]: [string, any]) => (
              <div key={m} className="px-3 py-1.5 rounded-xl bg-white/[0.02] border border-white/[0.05] text-[10px]">
                <span className="text-white/50">{m}:</span>{' '}
                <span className="text-cyan-400 font-medium">{count} flagged</span>
              </div>
            ))}
          </div>

          {/* Risk histogram */}
          {histData.length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-4">Risk Score Distribution</p>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={histData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="bin" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} />
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                  />
                  <Bar dataKey="count" fill="#f43f5e" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          {/* Method filter tabs */}
          <div className="flex gap-1 p-1 rounded-xl bg-white/[0.03] border border-white/[0.05] w-fit">
            {METHODS.map(m => (
              <button
                key={m}
                onClick={() => setMethod(m)}
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors
                  ${method === m ? 'bg-rose-500/20 text-rose-400' : 'text-white/30 hover:text-white/50'}`}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Flagged compounds table */}
          <GlassCard className="p-5">
            <p className="text-xs font-medium text-white/50 mb-3">
              Flagged Compounds ({compounds.length})
            </p>
            <div className="overflow-y-auto max-h-[400px]">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-[#0B132B]">
                  <tr className="text-white/25 border-b border-white/[0.05] text-left">
                    <th className="py-2 pr-4">Index</th>
                    <th className="py-2 pr-4">SMILES</th>
                    <th className="py-2 pr-4">Risk Score</th>
                    <th className="py-2">Flagged By</th>
                  </tr>
                </thead>
                <tbody>
                  {compounds.slice(0, 200).map((c: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.01]">
                      <td className="py-1.5 pr-4 text-white/50">{c.index}</td>
                      <td className="py-1.5 pr-4 text-white/40 font-mono truncate max-w-[160px]">
                        {(c.smiles || '').slice(0, 24) || '—'}
                      </td>
                      <td className="py-1.5 pr-4">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-16 bg-white/[0.06] rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${c.risk_score * 100}%`,
                                background: c.risk_score >= 0.75 ? '#f43f5e' : c.risk_score >= 0.5 ? '#f59e0b' : '#22d3ee'
                              }}
                            />
                          </div>
                          <span className={`font-mono ${c.risk_score >= 0.75 ? 'text-rose-400' : c.risk_score >= 0.5 ? 'text-amber-400' : 'text-cyan-400'}`}>
                            {c.risk_score?.toFixed(2)}
                          </span>
                        </div>
                      </td>
                      <td className="py-1.5">
                        <div className="flex gap-1 flex-wrap">
                          {(c.flagged_by ?? []).map((m: string) => (
                            <span key={m} className="px-1.5 py-0.5 rounded bg-white/[0.04] text-white/40 text-[9px]">{m}</span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        </>
      )}
    </motion.div>
  );
};
