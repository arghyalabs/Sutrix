import React from 'react';
import { motion } from 'framer-motion';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatusBadge
} from './shared';

interface LeakageTabProps { clientId: string }
const runLeakage = (clientId: string) => readinessApi.runLeakage(clientId) as Promise<any>;

const RISK_COLOR: Record<string, string> = {
  SAFE: 'text-emerald-400',
  MEDIUM: 'text-amber-400',
  HIGH: 'text-rose-400',
  CRITICAL: 'text-red-400',
};

const GaugeScore: React.FC<{ score: number }> = ({ score }) => {
  const color = score < 20 ? '#10b981' : score < 50 ? '#f59e0b' : score < 75 ? '#f43f5e' : '#dc2626';
  const r = 40;
  const circ = Math.PI * r; // half circle
  const dash = (score / 100) * circ;
  return (
    <svg width="100" height="60" viewBox="0 0 100 60">
      <path d="M10 55 A40 40 0 0 1 90 55" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round" />
      <path d="M10 55 A40 40 0 0 1 90 55" fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`} />
      <text x="50" y="52" textAnchor="middle" fill={color} fontSize="16" fontWeight="bold">{Math.round(score)}</text>
    </svg>
  );
};

export const LeakageTab: React.FC<LeakageTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'leakage', runLeakage
  );

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Data Leakage Detection"
        subtitle="Identify identifier columns, target-correlated features, and duplicate structural leakage"
      >
        <RunButton label="Run Leakage Detection" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Leakage Detection" onRun={run} />}

      {data && (
        <>
          {/* Risk score */}
          <GlassCard className="p-6 flex items-center gap-8">
            <div className="flex flex-col items-center">
              <GaugeScore score={data.leakage_risk_score ?? 0} />
              <p className="text-[10px] text-white/30 mt-1">Leakage Risk Score</p>
            </div>
            <div>
              <p className="text-xs text-white/40 mb-1">Risk Tier</p>
              <StatusBadge status={data.risk_tier ?? 'SAFE'} />
              <div className="mt-4 space-y-1 text-xs text-white/35">
                <p>· {data.n_identifier_flags ?? 0} identifier column{(data.n_identifier_flags ?? 0) !== 1 ? 's' : ''} flagged</p>
                <p>· {data.n_suspicious_correlations ?? 0} suspicious feature-target correlation{(data.n_suspicious_correlations ?? 0) !== 1 ? 's' : ''}</p>
                <p>· {data.duplicate_info?.duplicate_count ?? 0} structural duplicates ({data.duplicate_info?.risk_tier ?? 'SAFE'})</p>
              </div>
            </div>
          </GlassCard>

          {/* Identifier columns */}
          {(data.identifier_columns ?? []).length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-amber-400 mb-3">
                ⚠ Identifier Columns Detected ({data.identifier_columns.length})
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(data.identifier_columns ?? []).map((c: any) => (
                  <div key={c.column} className="px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs">
                    <span className="text-amber-400 font-mono">{c.column}</span>
                    <span className="text-white/30 ml-2 text-[10px]">matched: {c.pattern_matched}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-white/25 mt-3">
                Remove these from your feature set before training to avoid identity-based leakage.
              </p>
            </GlassCard>
          )}

          {/* Suspicious correlations */}
          {(data.suspicious_correlations ?? []).length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-rose-400 mb-3">
                ✗ Suspicious Feature-Target Correlations ({data.suspicious_correlations.length})
              </p>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-white/25 border-b border-white/[0.05] text-left">
                    <th className="py-2 pr-4">Feature</th>
                    <th className="py-2 pr-4">Pearson r to Target</th>
                    <th className="py-2">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {(data.suspicious_correlations ?? []).map((c: any, i: number) => (
                    <tr key={i} className="border-b border-white/[0.03]">
                      <td className="py-1.5 pr-4 text-rose-400 font-mono">{c.feature}</td>
                      <td className="py-1.5 pr-4 text-white/60 font-mono">{c.pearson_r?.toFixed(4)}</td>
                      <td className="py-1.5"><StatusBadge status={c.risk} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </GlassCard>
          )}

          {/* Duplicate info */}
          <GlassCard className="p-5">
            <p className="text-xs font-medium text-white/50 mb-3">Structural Duplicate Analysis</p>
            <div className="flex items-center gap-4">
              <div>
                <p className="text-2xl font-bold text-white/70">
                  {data.duplicate_info?.duplicate_count ?? 0}
                </p>
                <p className="text-[10px] text-white/30">duplicate compounds</p>
              </div>
              <div>
                <p className="text-sm font-medium" style={{ color: RISK_COLOR[data.duplicate_info?.risk_tier ?? 'SAFE'] }}>
                  {data.duplicate_info?.risk_tier ?? 'SAFE'}
                </p>
                <p className="text-[10px] text-white/25">{(data.duplicate_info?.duplicate_pct ?? 0).toFixed(1)}% of dataset</p>
              </div>
            </div>
            {(data.duplicate_info?.duplicate_smiles_sample ?? []).length > 0 && (
              <div className="mt-4">
                <p className="text-[10px] text-white/30 mb-2">Example duplicate SMILES:</p>
                <div className="space-y-1">
                  {data.duplicate_info.duplicate_smiles_sample.map((s: string, i: number) => (
                    <p key={i} className="text-[10px] font-mono text-white/40 truncate">{s}</p>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
        </>
      )}
    </motion.div>
  );
};
