import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill, StatusBadge
} from './shared';

interface ImbalanceTabProps { clientId: string }
const runImbalance = (clientId: string) => readinessApi.runImbalance(clientId) as Promise<any>;

const RecommendationCard: React.FC<{ rec: any }> = ({ rec }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-white/[0.05] bg-white/[0.01] overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <StatusBadge status={rec.severity} />
          <span className="text-xs font-medium text-white/70">{rec.strategy}</span>
        </div>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-white/30" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-2">
          <p className="text-xs text-white/40">{rec.reason}</p>
          {rec.code_hint && (
            <pre className="text-[10px] font-mono text-white/50 bg-white/[0.02] rounded-lg p-3 overflow-x-auto">
              {rec.code_hint}
            </pre>
          )}
        </div>
      )}
    </div>
  );
};

export const ImbalanceTab: React.FC<ImbalanceTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'imbalance', runImbalance
  );

  const barData = data && !data.is_continuous
    ? Object.entries(data.class_distribution ?? {}).map(([cls, count]: [string, any]) => ({
        class: cls,
        count,
        pct: data.class_percentages?.[cls] ?? 0,
      }))
    : [];

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Class Imbalance Analysis"
        subtitle="Endpoint distribution, entropy, and recommended balancing strategies"
      >
        <RunButton label="Run Imbalance Analysis" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Imbalance Analysis" onRun={run} />}

      {data && data.is_continuous && (
        <GlassCard className="p-6 text-center">
          <p className="text-sm font-medium text-cyan-400 mb-2">Continuous Endpoint Detected</p>
          <p className="text-xs text-white/40">
            This is a regression task — class imbalance metrics do not apply.
          </p>
          {data.continuous_stats && (
            <div className="grid grid-cols-4 gap-3 mt-5">
              {['mean', 'std', 'skew', 'kurt'].map(k => (
                <div key={k} className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3">
                  <p className="text-xs text-white/70 font-mono">{data.continuous_stats[k]?.toFixed(4)}</p>
                  <p className="text-[10px] text-white/30 mt-0.5 uppercase">{k}</p>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      )}

      {data && !data.is_continuous && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatPill label="Classes" value={data.n_classes ?? '—'} />
            <StatPill
              label="Minority Ratio"
              value={`${((data.minority_ratio ?? 0) * 100).toFixed(1)}%`}
              color={
                (data.minority_ratio ?? 1) < 0.05 ? 'text-red-400' :
                (data.minority_ratio ?? 1) < 0.20 ? 'text-rose-400' :
                (data.minority_ratio ?? 1) < 0.40 ? 'text-amber-400' : 'text-emerald-400'
              }
            />
            <StatPill label="Shannon Entropy" value={(data.shannon_entropy ?? 0).toFixed(3)} color="text-cyan-400" />
            <StatPill label="Imbalance Score" value={`${(data.imbalance_score ?? 0).toFixed(1)}/100`} />
          </div>

          {/* Class distribution bar chart */}
          {barData.length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-4">Class Distribution</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="class" tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} />
                  <YAxis tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ background: '#0B132B', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8 }}
                    formatter={(v: any) => [(v as number).toLocaleString(), 'Compounds']}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </GlassCard>
          )}

          {/* Recommendations */}
          {data.recommendations?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-white/50 mb-3">
                Balancing Recommendations ({data.recommendations.length})
              </p>
              <div className="space-y-2">
                {(data.recommendations ?? []).map((rec: any, i: number) => (
                  <RecommendationCard key={i} rec={rec} />
                ))}
              </div>
            </div>
          )}

          {data.recommendations?.length === 0 && (
            <GlassCard className="p-6 text-center">
              <p className="text-sm text-emerald-400">✓ Class distribution is well-balanced</p>
              <p className="text-xs text-white/30 mt-1">No imbalance correction needed</p>
            </GlassCard>
          )}
        </>
      )}
    </motion.div>
  );
};
