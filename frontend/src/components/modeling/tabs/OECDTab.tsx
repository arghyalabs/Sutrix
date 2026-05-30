import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, ErrorBanner, GlassCard, TabHeader, StatusBadge
} from './shared';

interface OECDTabProps { clientId: string; analysis?: any }
const runOECD = (clientId: string) => readinessApi.runOECD(clientId) as Promise<any>;

const COMPLIANCE_COLOR: Record<string, string> = {
  FULLY_COMPLIANT: 'text-emerald-400',
  PARTIAL_COMPLIANT: 'text-amber-400',
  NON_COMPLIANT: 'text-rose-400',
};

const ScoreBar: React.FC<{ score: number; status: string }> = ({ score, status }) => {
  const color = status === 'PASS' ? '#10b981' : status === 'WARN' ? '#f59e0b' : '#f43f5e';
  return (
    <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden mb-3">
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={{ width: 0 }}
        animate={{ width: `${score}%` }}
        transition={{ duration: 0.7, delay: 0.1 }}
      />
    </div>
  );
};

export const OECDTab: React.FC<OECDTabProps> = ({ clientId, analysis }) => {
  const { data: freshData, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'oecd', runOECD
  );

  // Build display data: freshData takes priority, then fallback to existing analysis.qsar.oecd_checks
  const oecdData = React.useMemo(() => {
    if (freshData) return freshData;
    if (!analysis?.qsar?.oecd_checks) return null;
    // Convert legacy format to new format
    const checks = analysis.qsar.oecd_checks as Record<string, boolean>;
    const principles = [
      { id: 1, name: 'Defined Endpoint', key: 'defined_endpoint' },
      { id: 2, name: 'Unambiguous Algorithm', key: 'unambiguous_algorithm' },
      { id: 3, name: 'Applicability Domain', key: 'applicability_domain' },
      { id: 4, name: 'Goodness of Fit', key: 'goodness_of_fit' },
      { id: 5, name: 'Mechanistic Interpretation', key: 'mechanistic_interpretation' },
    ].map(p => ({
      id: p.id,
      name: p.name,
      status: checks[p.key] ? 'PASS' : 'FAIL',
      score: checks[p.key] ? 85 : 30,
      details: checks[p.key]
        ? `Principle ${p.id} appears to be met based on initial dataset evaluation.`
        : `Principle ${p.id} needs attention — run the full OECD evaluation for details.`,
      recommendations: checks[p.key] ? [] : [`Run the OECD Re-evaluation to get detailed recommendations for Principle ${p.id}.`],
    }));
    const pass_count = principles.filter(p => p.status === 'PASS').length;
    return {
      principles,
      overall_oecd_score: Math.round(principles.reduce((s, p) => s + p.score, 0) / 5),
      pass_count,
      warn_count: 0,
      fail_count: 5 - pass_count,
      compliance_tier: pass_count === 5 ? 'FULLY_COMPLIANT' : pass_count >= 3 ? 'PARTIAL_COMPLIANT' : 'NON_COMPLIANT',
    };
  }, [freshData, analysis]);

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="OECD QSAR Principles"
        subtitle="5-principle compliance evaluation for regulatory AI workflows"
      >
        <RunButton label="Re-evaluate OECD" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}

      {!oecdData && !isRunning && (
        <div className="py-16 text-center">
          <p className="text-sm text-white/30 mb-4">Run OECD evaluation to assess regulatory compliance</p>
          <RunButton label="Evaluate OECD Compliance" isRunning={false} onClick={run} />
        </div>
      )}

      {oecdData && (
        <>
          {/* Overall score */}
          <GlassCard className="p-6 flex items-center gap-8">
            <div className="text-center">
              <p className="text-4xl font-bold text-white/80">{oecdData.overall_oecd_score}</p>
              <p className="text-[10px] text-white/30 mt-1">OECD Score</p>
            </div>
            <div>
              <p className={`text-sm font-semibold ${COMPLIANCE_COLOR[oecdData.compliance_tier]}`}>
                {oecdData.compliance_tier?.replace(/_/g, ' ')}
              </p>
              <div className="flex gap-4 mt-2 text-xs text-white/40">
                <span className="text-emerald-400">{oecdData.pass_count} PASS</span>
                <span className="text-amber-400">{oecdData.warn_count} WARN</span>
                <span className="text-rose-400">{oecdData.fail_count} FAIL</span>
              </div>
              {!freshData && (
                <p className="text-[10px] text-white/25 mt-2">
                  Using preliminary evaluation — click Re-evaluate for detailed assessment
                </p>
              )}
            </div>
          </GlassCard>

          {/* Principle cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {(oecdData.principles ?? []).map((p: any) => (
              <GlassCard key={p.id} className="p-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] text-white/25 uppercase tracking-wider">Principle {p.id}</span>
                  <StatusBadge status={p.status} />
                </div>
                <h3 className="text-xs font-semibold text-white/80 mb-3">{p.name}</h3>
                <ScoreBar score={p.score} status={p.status} />
                <p className="text-[11px] text-white/40 leading-relaxed">{p.details}</p>
                {(p.recommendations ?? []).length > 0 && (
                  <ul className="mt-3 space-y-1">
                    {p.recommendations.map((r: string, i: number) => (
                      <li key={i} className="text-[10px] text-amber-400">• {r}</li>
                    ))}
                  </ul>
                )}
              </GlassCard>
            ))}
          </div>
        </>
      )}
    </motion.div>
  );
};
