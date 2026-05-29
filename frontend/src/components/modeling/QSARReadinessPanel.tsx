import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, ChevronDown } from 'lucide-react';
import * as Accordion from '@radix-ui/react-accordion';
import type { ModelingAnalysis } from '../../types';

const QSARReadinessPanel: React.FC<{ data: ModelingAnalysis }> = ({ data }) => {
  const { oecd_checks, descriptor_readiness, endpoint_status, oecd_pass_count } = data.qsar;
  const passRate = Math.round((oecd_pass_count / 5) * 100);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold text-white">QSAR Readiness Intelligence</h2>
          <p className="text-sm text-white/40 mt-1">OECD 5-Principle Compliance Assessment</p>
        </div>
        <div className="text-right">
          <div className={`text-3xl font-bold ${passRate >= 80 ? 'text-emerald-400' : passRate >= 60 ? 'text-amber-400' : 'text-rose-400'}`}>
            {oecd_pass_count}/5
          </div>
          <div className="text-xs text-white/40">Principles Passed</div>
        </div>
      </div>

      {/* OECD Checklist */}
      <Accordion.Root type="multiple" className="space-y-2">
        {oecd_checks.map((check, i) => (
          <Accordion.Item
            key={check.principle}
            value={String(check.principle)}
            className={`rounded-xl border overflow-hidden ${
              check.status ? 'border-emerald-500/20 bg-emerald-500/[0.03]' : 'border-rose-500/20 bg-rose-500/[0.03]'
            }`}
          >
            <Accordion.Trigger className="w-full flex items-center gap-4 px-5 py-4 text-left group">
              <motion.div
                initial={{ scale: 0 }} animate={{ scale: 1 }}
                transition={{ delay: i * 0.1, type: 'spring', stiffness: 300 }}
              >
                {check.status
                  ? <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  : <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
                }
              </motion.div>
              <div className="flex-1">
                <div className="text-xs text-white/30 mb-0.5">OECD Principle {check.principle}</div>
                <div className="text-sm font-medium text-white/80">{check.name}</div>
              </div>
              <ChevronDown className="w-4 h-4 text-white/30 group-data-[state=open]:rotate-180 transition-transform" />
            </Accordion.Trigger>
            <Accordion.Content className="px-5 pb-4">
              <p className="text-xs text-white/50 leading-relaxed pl-9">{check.evidence}</p>
            </Accordion.Content>
          </Accordion.Item>
        ))}
      </Accordion.Root>

      {/* Descriptor Readiness */}
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
        <h3 className="text-sm font-semibold text-white/80 mb-4">Descriptor Readiness by Category</h3>
        <div className="space-y-3">
          {descriptor_readiness.map((dr, i) => {
            const col = dr.completeness >= 90 ? '#10B981' : dr.completeness >= 60 ? '#F59E0B' : '#EF4444';
            return (
              <motion.div key={dr.category} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-white/60">{dr.category}</span>
                  <span className="text-white/40">{dr.count} descriptors · <span style={{ color: col }}>{dr.recommendation}</span></span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.06]">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: col }}
                    initial={{ width: 0 }}
                    animate={{ width: `${dr.completeness}%` }}
                    transition={{ duration: 0.7, delay: i * 0.08 }}
                  />
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Endpoint Status */}
      <div className={`rounded-xl border p-5 ${endpoint_status.harmonized ? 'border-emerald-500/20 bg-emerald-500/[0.04]' : 'border-amber-500/20 bg-amber-500/[0.04]'}`}>
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-white/80">
          {endpoint_status.harmonized
            ? <><CheckCircle2 className="w-4 h-4 text-emerald-400" /> Endpoint Harmonization — Passed</>
            : <><XCircle className="w-4 h-4 text-amber-400" /> Endpoint Harmonization — Issues Detected</>
          }
        </h3>
        {endpoint_status.findings.length === 0
          ? <p className="text-xs text-white/40">All assay units and endpoints are consistent.</p>
          : endpoint_status.findings.map((f: any, i: number) => (
              <div key={i} className="text-xs text-white/50 mb-2">
                <span className="text-amber-400 font-medium">{f.issue}:</span> {f.details}
              </div>
            ))
        }
      </div>
    </div>
  );
};

export default QSARReadinessPanel;
