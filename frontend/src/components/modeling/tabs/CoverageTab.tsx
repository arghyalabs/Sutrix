import React from 'react';
import { motion } from 'framer-motion';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader, StatPill, StatusBadge
} from './shared';

interface CoverageTabProps { clientId: string }

const runCoverage = (clientId: string) => readinessApi.runCoverage(clientId) as Promise<any>;

// SVG ring gauge
const RingGauge: React.FC<{ pct: number; status: string }> = ({ pct, status }) => {
  const r = 22;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = status === 'GOOD' ? '#10b981' : status === 'PARTIAL' ? '#f59e0b' : '#f43f5e';
  return (
    <svg width="56" height="56" viewBox="0 0 56 56">
      <circle cx="28" cy="28" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
      <circle
        cx="28" cy="28" r={r} fill="none"
        stroke={color} strokeWidth="5"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 28 28)"
      />
      <text x="28" y="33" textAnchor="middle" fill={color} fontSize="11" fontWeight="bold">
        {Math.round(pct)}%
      </text>
    </svg>
  );
};

export const CoverageTab: React.FC<CoverageTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'coverage', runCoverage
  );

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Descriptor Coverage Audit"
        subtitle="Coverage of scientific descriptor families across the computed feature set"
      >
        <RunButton label="Run Coverage Audit" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Coverage" onRun={run} />}

      {data && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatPill
              label="Overall Coverage"
              value={`${(data.overall_coverage_pct ?? 0).toFixed(1)}%`}
              color={data.overall_coverage_pct > 70 ? 'text-emerald-400' : data.overall_coverage_pct > 30 ? 'text-amber-400' : 'text-rose-400'}
            />
            <StatPill label="Families Found" value={data.families?.filter((f: any) => f.present > 0).length ?? 0} color="text-cyan-400" />
            <StatPill label="Missing Families" value={data.missing_families?.length ?? 0} color="text-rose-400" />
            <StatPill label="Descriptors Generated" value={data.generated_descriptors?.length ?? 0} color="text-emerald-400" />
          </div>

          {/* Family cards grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
            {(data.families ?? []).map((fam: any) => (
              <GlassCard key={fam.name} className="p-4 flex flex-col items-center text-center gap-2">
                <RingGauge pct={fam.coverage_pct ?? 0} status={fam.status} />
                <p className="text-xs font-medium text-white/70">{fam.name}</p>
                <p className="text-[10px] text-white/35">{fam.present ?? 0} descriptors</p>
                <StatusBadge status={fam.status} />
              </GlassCard>
            ))}
          </div>

          {/* Generated descriptors */}
          {data.generated_descriptors?.length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-white/50 mb-3">Generated Descriptors ({data.generated_descriptors.length})</p>
              <div className="flex flex-wrap gap-1.5 max-h-32 overflow-y-auto">
                {(data.generated_descriptors ?? []).map((d: string) => (
                  <span key={d} className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                    {d}
                  </span>
                ))}
              </div>
            </GlassCard>
          )}
        </>
      )}
    </motion.div>
  );
};
