import React from 'react';
import { motion } from 'framer-motion';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill, StatusBadge
} from './shared';

interface ApplicabilityDomainTabProps { clientId: string }
const runDomain = (clientId: string) => readinessApi.runDomain(clientId) as Promise<any>;

const DOMAIN_COLORS: Record<string, string> = {
  INSIDE: '#22d3ee',
  BORDERLINE: '#f59e0b',
  OUTSIDE: '#f43f5e',
};

export const ApplicabilityDomainTab: React.FC<ApplicabilityDomainTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'domain', runDomain
  );

  const pieData = data ? [
    { name: 'Inside', value: data.inside_count ?? 0, color: '#22d3ee' },
    { name: 'Borderline', value: data.borderline_count ?? 0, color: '#f59e0b' },
    { name: 'Outside', value: data.outside_count ?? 0, color: '#f43f5e' },
  ] : [];

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Applicability Domain"
        subtitle="Williams Plot leverage analysis — which compounds are within the model's domain?"
      >
        <RunButton label="Run Domain Analysis" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Applicability Domain" onRun={run} />}

      {data && (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatPill label="Inside Domain" value={data.inside_count ?? 0} color="text-cyan-400" />
            <StatPill label="Borderline" value={data.borderline_count ?? 0} color="text-amber-400" />
            <StatPill label="Outside Domain" value={data.outside_count ?? 0} color="text-rose-400" />
            <StatPill
              label="Coverage"
              value={`${(data.domain_coverage_pct ?? 0).toFixed(1)}%`}
              color={
                (data.domain_coverage_pct ?? 0) >= 85 ? 'text-emerald-400' :
                (data.domain_coverage_pct ?? 0) >= 70 ? 'text-amber-400' : 'text-rose-400'
              }
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Williams Plot */}
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-2">Williams Plot (Leverage vs Standardized Residuals)</p>
              <p className="text-[10px] text-white/25 mb-4">
                h* = {data.h_star?.toFixed(4)} · Dashed lines mark the domain boundary
              </p>
              <div className="h-48 flex items-center justify-center">
                {(data.williams_plot_data?.leverage ?? []).length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={(data.williams_plot_data?.leverage ?? []).slice(0, 500).map((h: number, i: number) => ({
                        leverage: h.toFixed(4),
                        residual: (data.williams_plot_data?.std_residuals?.[i] ?? 0).toFixed(4),
                        domain: data.williams_plot_data?.domain?.[i] ?? 'INSIDE',
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="leverage" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 8 }} hide />
                      <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 9 }} />
                      <Tooltip
                        contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                      />
                      <Bar dataKey="residual" fill="#22d3ee" radius={[1, 1, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-xs text-white/30">No plot data available</p>
                )}
              </div>
            </GlassCard>

            {/* Pie chart */}
            <GlassCard className="p-5 flex flex-col">
              <p className="text-xs font-medium text-white/50 mb-4">Domain Classification Distribution</p>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={70} dataKey="value" paddingAngle={3}>
                    {pieData.map((entry, index) => (
                      <Cell key={index} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                    formatter={(v: any, name: any) => [v, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex justify-center gap-4 mt-2">
                {pieData.map(p => (
                  <div key={p.name} className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                    <span className="text-[10px] text-white/40">{p.name}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        </>
      )}
    </motion.div>
  );
};
