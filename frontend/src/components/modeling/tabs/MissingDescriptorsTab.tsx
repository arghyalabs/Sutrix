import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { readinessApi } from '../../../services/readinessApi';
import { useAnalysisSection } from '../../../services/useAnalysisSection';
import {
  RunButton, ProgressBar, SectionEmptyState, ErrorBanner, GlassCard, TabHeader
} from './shared';

interface MissingDescriptorsTabProps { clientId: string }
const runCoverage = (clientId: string) => readinessApi.runCoverage(clientId) as Promise<any>;

const ImportanceBadge: React.FC<{ level: string }> = ({ level }) => {
  const map: Record<string, string> = {
    Critical: 'bg-red-600/10 text-red-400 border-red-600/20',
    High: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    Medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    Low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  };
  const cls = map[level] || 'bg-white/[0.04] text-white/40 border-white/[0.06]';
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium border ${cls}`}>{level}</span>
  );
};

const RecommendationCard: React.FC<{ rec: any }> = ({ rec }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-white/[0.05] bg-white/[0.01] overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          <ImportanceBadge level={rec.importance} />
          <span className="text-xs font-medium text-white/70">{rec.name}</span>
          <span className="text-[10px] text-white/30">({rec.family})</span>
        </div>
        {open ? <ChevronDown className="w-3.5 h-3.5 text-white/30" /> : <ChevronRight className="w-3.5 h-3.5 text-white/30" />}
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3">
          <p className="text-xs text-white/40 leading-relaxed">{rec.reason}</p>
          {rec.how_to_generate && (
            <div>
              <p className="text-[10px] text-cyan-400/70 mb-1">How to generate:</p>
              <pre className="text-[10px] font-mono text-white/50 bg-white/[0.02] rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                {rec.how_to_generate}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const MissingDescriptorsTab: React.FC<MissingDescriptorsTabProps> = ({ clientId }) => {
  const { data, isRunning, progress, phase, error, run } = useAnalysisSection(
    clientId, 'coverage', runCoverage
  );

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <TabHeader
        title="Missing Descriptors"
        subtitle="Scientific descriptor gaps and how to fill them"
      >
        <RunButton label="Audit Coverage" isRunning={isRunning} progress={progress} phase={phase} onClick={run} />
      </TabHeader>

      {error && <ErrorBanner error={error} />}
      {isRunning && <ProgressBar progress={progress} phase={phase} />}
      {!data && !isRunning && <SectionEmptyState label="Coverage" onRun={run} />}

      {data && (
        <>
          {/* Generated descriptors */}
          {data.generated_descriptors?.length > 0 && (
            <GlassCard className="p-5">
              <p className="text-xs font-medium text-emerald-400 mb-3">
                ✓ Generated Descriptors ({data.generated_descriptors.length})
              </p>
              <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
                {(data.generated_descriptors ?? []).map((d: string) => (
                  <span key={d} className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono">
                    {d}
                  </span>
                ))}
              </div>
            </GlassCard>
          )}

          {/* Missing families */}
          {data.missing_families?.length > 0 && (
            <div>
              <p className="text-xs text-rose-400/80 mb-3 font-medium">
                ✗ {data.missing_families.length} Missing Descriptor Families
              </p>
              <div className="space-y-2">
                {(data.missing_families ?? []).map((fam: string) => (
                  <div key={fam} className="px-4 py-2 rounded-lg bg-rose-500/5 border border-rose-500/10">
                    <span className="text-xs text-rose-400 font-medium">{fam}</span>
                    <span className="text-[10px] text-white/25 ml-2">— not present in dataset</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {data.missing_descriptor_recommendations?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-white/50 mb-3">
                Descriptor Recommendations ({data.missing_descriptor_recommendations.length})
              </p>
              <div className="space-y-2">
                {(data.missing_descriptor_recommendations ?? []).map((rec: any, i: number) => (
                  <RecommendationCard key={i} rec={rec} />
                ))}
              </div>
            </div>
          )}

          {data.missing_descriptor_recommendations?.length === 0 && (
            <div className="py-12 text-center">
              <p className="text-sm text-emerald-400">✓ No critical missing descriptors — excellent coverage!</p>
            </div>
          )}
        </>
      )}
    </motion.div>
  );
};
