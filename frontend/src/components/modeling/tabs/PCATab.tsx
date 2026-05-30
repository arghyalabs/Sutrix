import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill,
} from './shared';

interface PCATabProps { clientId: string }

const runPCA = (clientId: string) => readinessApi.runPCA(clientId) as Promise<any>;

export const PCATab: React.FC<PCATabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'pca', runPCA
  );
  const [selectedPC, setSelectedPC] = useState<'PC1' | 'PC2' | 'PC3'>('PC1');

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <TabHeader
        title="PCA Analytics"
        subtitle="Principal Component Analysis — variance structure and chemical space projection"
      >
        <RunButton label="Run PCA Analysis" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="PCA" onRun={run} />}

      {data && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatPill label="Compounds" value={data.n_samples?.toLocaleString() ?? '—'} />
            <StatPill label="Features Used" value={data.n_features_used ?? '—'} />
            <StatPill label="PCs for 95% Var" value={data.n_components_95pct ?? '—'} color="text-cyan-400" />
            <StatPill label="Outliers" value={data.outlier_count ?? 0} color={data.outlier_count > 0 ? 'text-rose-400' : 'text-emerald-400'} />
          </div>

          {/* Two-column: variance + scatter */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Variance bar chart */}
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-4">Explained Variance per Component</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.variance_explained?.slice(0, 12) ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="component" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} unit="%" />
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                    formatter={(v: any) => [`${(v as number).toFixed(1)}%`, 'Variance']}
                  />
                  <Bar dataKey="variance_pct" fill="#22d3ee" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>

            {/* Cumulative variance */}
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-4">Cumulative Variance Explained</p>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.variance_explained?.slice(0, 12) ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="component" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} domain={[0, 100]} unit="%" />
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                    formatter={(v: any) => [`${(v as number).toFixed(1)}%`, 'Cumulative']}
                  />
                  <Bar dataKey="cumulative" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          </div>

          {/* Feature loadings */}
          {data.top_features_per_pc && (
            <GlassCard className="p-5">
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs font-medium text-white/50">Top Feature Loadings</p>
                <div className="flex gap-1">
                  {(['PC1', 'PC2', 'PC3'] as const).map(pc => (
                    <button
                      key={pc}
                      onClick={() => setSelectedPC(pc)}
                      className={`px-3 py-1 rounded-lg text-xs transition-colors
                        ${selectedPC === pc
                          ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                          : 'text-white/30 hover:text-white/50'}`}
                    >
                      {pc}
                    </button>
                  ))}
                </div>
              </div>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={[...(data.top_features_per_pc[selectedPC] ?? [])].sort((a: any, b: any) => a.abs_loading - b.abs_loading)}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} domain={[-1, 1]} />
                  <YAxis type="category" dataKey="feature" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} width={90} />
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                    formatter={(v: any) => [(v as number).toFixed(4), 'Loading']}
                  />
                  <Bar dataKey="loading" fill="#22d3ee" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          {/* Outlier table */}
          {data.outlier_count > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-3">
                Outlier Compounds ({data.outlier_count} detected)
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-white/30 border-b border-white/[0.05]">
                      <th className="text-left py-2 pr-4">Index</th>
                      <th className="text-left py-2 pr-4">PC1</th>
                      <th className="text-left py-2 pr-4">PC2</th>
                      <th className="text-left py-2">SMILES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.projections ?? [])
                      .filter((p: any) => p.is_outlier)
                      .slice(0, 50)
                      .map((p: any) => (
                        <tr key={p.idx} className="border-b border-white/[0.03] hover:bg-white/[0.01]">
                          <td className="py-1.5 pr-4 text-rose-400">{p.idx}</td>
                          <td className="py-1.5 pr-4 text-white/60 font-mono">{p.PC1?.toFixed(3)}</td>
                          <td className="py-1.5 pr-4 text-white/60 font-mono">{p.PC2?.toFixed(3)}</td>
                          <td className="py-1.5 text-white/40 font-mono truncate max-w-[200px]">
                            {p.smiles?.slice(0, 30) || '—'}
                          </td>
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
