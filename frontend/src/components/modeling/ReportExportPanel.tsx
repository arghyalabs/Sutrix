import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, FileJson, FileText, FileSpreadsheet, Printer } from 'lucide-react';
import toast from 'react-hot-toast';
import { modelingApi } from '../../services/modelingApi';
import type { ModelingAnalysis } from '../../types';

const FORMAT_CARDS = [
  { format: 'json' as const, icon: FileJson, label: 'JSON', desc: 'Full analysis object — all scores, risks, recommendations', color: '#22D3EE' },
  { format: 'csv' as const, icon: FileText, label: 'CSV', desc: 'Flat summary table — scores, tier, top risks', color: '#10B981' },
  { format: 'xlsx' as const, icon: FileSpreadsheet, label: 'Excel', desc: 'Multi-sheet workbook — scores, risks, features, models', color: '#3B82F6' },
];

const ReportExportPanel: React.FC<{ data: ModelingAnalysis; clientId: string }> = ({ data, clientId }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const r = data.readiness;

  const handleExport = async (format: 'json' | 'csv' | 'xlsx') => {
    setLoading(format);
    try {
      const blob = await modelingApi.exportReport(clientId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sdo_modeling_report_${clientId}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} report downloaded`);
    } catch {
      toast.error('Export failed. Please try again.');
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Export Report</h2>
        <p className="text-sm text-white/40 mt-1">Download the full AI readiness analysis in your preferred format</p>
      </div>

      {/* Executive Summary */}
      <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6 space-y-4">
        <h3 className="text-sm font-semibold text-white/80">Executive Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'AI Readiness', value: `${r.ai_score}%`, color: r.ai_score >= 80 ? '#10B981' : r.ai_score >= 60 ? '#F59E0B' : '#EF4444' },
            { label: 'QSAR Score', value: `${r.qsar_score}%`, color: '#8B5CF6' },
            { label: 'Stability', value: `${r.stability_score}%`, color: '#3B82F6' },
            { label: 'Integrity', value: `${r.integrity_score}%`, color: '#10B981' },
          ].map(({ label, value, color }) => (
            <div key={label} className="text-center">
              <div className="text-2xl font-bold" style={{ color }}>{value}</div>
              <div className="text-xs text-white/40 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
        <div className="border-t border-white/[0.06] pt-4 grid grid-cols-3 gap-4 text-sm text-center">
          <div><span className="text-rose-400 font-semibold">{data.risks.filter(r => r.severity === 'CRITICAL' || r.severity === 'HIGH').length}</span> <span className="text-white/40">Critical/High Risks</span></div>
          <div><span className="text-amber-400 font-semibold">{data.features.length}</span> <span className="text-white/40">Feature Recommendations</span></div>
          <div><span className="text-cyan-400 font-semibold">{data.models.length}</span> <span className="text-white/40">Model Suggestions</span></div>
        </div>
        <div className="text-xs text-white/30">
          Confidence: <span className="text-white/60 font-medium">{r.confidence_tier}</span> · 
          Dataset: <span className="text-white/60">{r.n_samples.toLocaleString()} compounds, {r.n_features.toLocaleString()} descriptors</span> · 
          Analysis time: <span className="text-white/60">{data.meta.elapsed_seconds}s</span>
        </div>
      </div>

      {/* Export format cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {FORMAT_CARDS.map(({ format, icon: Icon, label, desc, color }, i) => (
          <motion.button
            key={format}
            onClick={() => handleExport(format)}
            disabled={loading !== null}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="rounded-xl border border-white/[0.08] bg-white/[0.03] p-5 text-left hover:bg-white/[0.05] transition-all disabled:opacity-40 disabled:cursor-wait"
          >
            <Icon className="w-6 h-6 mb-3" style={{ color }} />
            <div className="text-sm font-semibold text-white mb-1 flex items-center gap-2">
              {label}
              {loading === format && <span className="text-xs text-white/40">(downloading…)</span>}
            </div>
            <p className="text-xs text-white/40 leading-relaxed">{desc}</p>
            <div className="mt-3 flex items-center gap-1.5 text-xs font-medium" style={{ color }}>
              <Download className="w-3 h-3" /> Download {label}
            </div>
          </motion.button>
        ))}
      </div>

      {/* Print / PDF */}
      <button
        onClick={() => window.print()}
        className="w-full flex items-center justify-center gap-3 py-3 rounded-xl border border-white/[0.06] text-white/50 hover:text-white/70 hover:bg-white/[0.04] transition-all text-sm"
      >
        <Printer className="w-4 h-4" /> Print / Save as PDF (browser print dialog)
      </button>
    </div>
  );
};

export default ReportExportPanel;
