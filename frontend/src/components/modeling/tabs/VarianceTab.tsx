import React from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill, StatusBadge
} from './shared';

interface VarianceTabProps { clientId: string }

const runVariance = (clientId: string) => readinessApi.runVariance(clientId) as Promise<any>;

export const VarianceTab: React.FC<VarianceTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'variance', runVariance
  );
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('asc');

  const features = React.useMemo(() => {
    if (!data?.features) return [];
    return [...data.features].sort((a: any, b: any) =>
      sortDir === 'asc' ? a.variance - b.variance : b.variance - a.variance
    );
  }, [data, sortDir]);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Variance Threshold Analysis"
        subtitle="Identify near-constant and low-information descriptors"
      >
        <RunButton label="Run Variance Analysis" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Variance" onRun={run} />}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatPill label="Near-Zero" value={data.near_zero_count ?? 0} color="text-rose-400" />
            <StatPill label="Low Variance" value={data.low_variance_count ?? 0} color="text-amber-400" />
            <StatPill label="Safe" value={data.safe_count ?? 0} color="text-emerald-400" />
            <StatPill label="Total Features" value={data.total_features ?? 0} />
          </div>

          {/* Variance histogram */}
          {data.variance_histogram && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-4">Log Variance Distribution</p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart
                  data={(data.variance_histogram.bins ?? []).slice(0, -1).map((bin: number, i: number) => ({
                    bin: bin.toFixed(1),
                    count: data.variance_histogram.counts?.[i] ?? 0,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="bin" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} />
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          {/* Feature table */}
          <GlassCard className="p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-medium text-white/50">
                Feature Variance ({features.length} descriptors)
              </p>
              <button
                onClick={() => setSortDir(d => d === 'asc' ? 'desc' : 'asc')}
                className="text-[10px] text-cyan-400 hover:text-cyan-300"
              >
                Sort: {sortDir === 'asc' ? '↑ Low → High' : '↓ High → Low'}
              </button>
            </div>
            <div className="overflow-y-auto max-h-[400px]">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-[#0B132B]">
                  <tr className="text-white/25 border-b border-white/[0.05] text-left">
                    <th className="py-2 pr-4">Feature</th>
                    <th className="py-2 pr-4">Variance</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2">Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {features.slice(0, 300).map((f: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03] hover:bg-white/[0.01]">
                      <td className="py-1.5 pr-4 text-white/60 font-mono">{f.feature}</td>
                      <td className="py-1.5 pr-4 text-white/50 font-mono">{f.variance?.toExponential(2)}</td>
                      <td className="py-1.5 pr-4"><StatusBadge status={f.status} /></td>
                      <td className="py-1.5 text-white/30 max-w-[300px] truncate">{f.recommendation}</td>
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
