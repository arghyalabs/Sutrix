import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { OptimizedPlotly } from '../charts/OptimizedPlotly';
import {
  Brain, AlertTriangle, CheckCircle2, XCircle, ChevronDown,
  Zap, RefreshCw, Download, FileJson, FileSpreadsheet, FileText,
  Code2, TrendingUp, Shield, Layers, Target, Activity, FlaskConical,
  Cpu
} from 'lucide-react';
import { modelingApi } from '../../services/modelingApi';
import toast from 'react-hot-toast';
import type { ModelingAnalysis } from '../../types';

// ─── Shared Plotly config & layout base ────────────────────────────────────
const PC = { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['sendDataToCloud'] as any };
const BL = {
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: { t: 10, b: 36, l: 48, r: 12 },
  font: { family: 'Inter, sans-serif', color: 'rgba(255,255,255,0.35)', size: 10 },
  xaxis: { gridcolor: 'rgba(255,255,255,0.04)', tickfont: { color: 'rgba(255,255,255,0.3)', size: 9 }, zerolinecolor: 'rgba(255,255,255,0.06)' },
  yaxis: { gridcolor: 'rgba(255,255,255,0.04)', tickfont: { color: 'rgba(255,255,255,0.3)', size: 9 }, zerolinecolor: 'rgba(255,255,255,0.06)' },
  showlegend: false,
};

// ─── Tier colors ────────────────────────────────────────────────────────────
const TIER_COLOR: Record<string, string> = {
  HIGH: '#10B981', MEDIUM: '#F59E0B', LOW: '#EF4444', INSUFFICIENT: '#6B7280'
};
const SEV_COLOR: Record<string, string> = {
  CRITICAL: '#EF4444', HIGH: '#F59E0B', MEDIUM: '#3B82F6', LOW: '#6B7280'
};

// ─── Animated circular gauge ────────────────────────────────────────────────
const Gauge: React.FC<{ score: number; size?: number }> = ({ score, size = 140 }) => {
  const r = (size - 20) / 2;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#10B981' : score >= 60 ? '#F59E0B' : score >= 40 ? '#EF4444' : '#6B7280';
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={10} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={10} strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1.6, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="font-bold tabular-nums"
          style={{ color, fontSize: size * 0.24 }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6 }}
        >
          {Math.round(score)}
        </motion.span>
        <span className="text-white/30 text-xs mt-0.5">/ 100</span>
      </div>
    </div>
  );
};

// ─── KPI card ───────────────────────────────────────────────────────────────
const KPICard: React.FC<{
  label: string; value: string | number; sub: string;
  color?: string; icon: React.FC<any>; delay?: number;
}> = ({ label, value, sub, color = '#22D3EE', icon: Icon, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-5 
      hover:border-white/[0.08] transition-colors"
  >
    <div className="flex items-start justify-between mb-3">
      <Icon className="w-4 h-4" style={{ color }} />
      <span className="text-[10px] text-white/25 font-medium tracking-wide uppercase">{label}</span>
    </div>
    <div className="text-3xl font-bold tabular-nums" style={{ color }}>{value}</div>
    <div className="text-xs text-white/35 mt-1.5 leading-snug">{sub}</div>
  </motion.div>
);

// ─── Section header ─────────────────────────────────────────────────────────
const SectionHeader: React.FC<{ title: string; subtitle?: string; icon: React.FC<any> }> = ({
  title, subtitle, icon: Icon
}) => (
  <div className="flex items-center gap-3 mb-5">
    <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
      <Icon className="w-4 h-4 text-white/50" />
    </div>
    <div>
      <h2 className="text-sm font-semibold text-white/80">{title}</h2>
      {subtitle && <p className="text-xs text-white/30 mt-0.5">{subtitle}</p>}
    </div>
  </div>
);

// ─── Chart card wrapper ──────────────────────────────────────────────────────
const ChartCard: React.FC<{
  title: string; subtitle?: string; children: React.ReactNode; className?: string;
}> = ({ title, subtitle, children, className = '' }) => (
  <div className={`rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl overflow-hidden hover:border-white/[0.08] transition-colors ${className}`}>
    <div className="px-5 pt-4 pb-2">
      <h3 className="text-sm font-medium text-white/70">{title}</h3>
      {subtitle && <p className="text-xs text-white/30 mt-0.5">{subtitle}</p>}
    </div>
    <div className="px-4 pb-4">{children}</div>
  </div>
);

// ─── Score bar ───────────────────────────────────────────────────────────────
const ScoreBar: React.FC<{ label: string; value: number; delay?: number }> = ({ label, value, delay = 0 }) => {
  const color = value >= 80 ? '#10B981' : value >= 60 ? '#F59E0B' : '#EF4444';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1.5">
        <span className="text-white/45">{label}</span>
        <span className="font-semibold tabular-nums" style={{ color }}>{Math.round(value)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.9, delay, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
};

// ─── Loading state ───────────────────────────────────────────────────────────
const PHASES = [
  'Analyzing descriptor variance…',
  'Computing endpoint distributions…',
  'Evaluating class imbalance…',
  'Building QSAR compatibility metrics…',
  'Running scaffold leakage audit…',
  'Detecting structural conflicts…',
  'Estimating predictive signal…',
  'Generating risk matrix…',
];

const LoadingState: React.FC = () => {
  const [phaseIdx, setPhaseIdx] = useState(0);
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhaseIdx(p => (p + 1) % PHASES.length);
      setPct(p => Math.min(95, p + Math.floor(8 + Math.random() * 6)));
    }, 1400);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-[1700px] mx-auto px-6 xl:px-10 py-16">
      <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-12 max-w-xl mx-auto">
        <div className="flex flex-col items-center gap-6">
          <div className="relative w-14 h-14">
            <div className="absolute inset-0 rounded-full border-2 border-cyan-400/10" />
            <div className="w-14 h-14 rounded-full border-2 border-transparent border-t-cyan-400 animate-spin" />
            <Cpu className="absolute inset-0 m-auto w-5 h-5 text-cyan-400/50" />
          </div>
          <div className="text-center w-full">
            <AnimatePresence mode="wait">
              <motion.p
                key={phaseIdx}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                className="text-sm text-white/50 mb-4"
              >
                {PHASES[phaseIdx]}
              </motion.p>
            </AnimatePresence>
            <div className="h-1 rounded-full bg-white/[0.05] overflow-hidden mb-2">
              <motion.div
                className="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full"
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.6 }}
              />
            </div>
            <p className="text-xs text-white/25">{pct}% complete</p>
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── Empty state ─────────────────────────────────────────────────────────────
const EmptyState: React.FC<{ onRun: () => void }> = ({ onRun }) => (
  <div className="max-w-[1700px] mx-auto px-6 xl:px-10 py-24 flex flex-col items-center gap-8 text-center">
    <div className="relative">
      <div className="w-20 h-20 rounded-2xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center">
        <Brain className="w-9 h-9 text-white/20" />
      </div>
      <motion.div
        className="absolute -inset-3 rounded-2xl border border-cyan-500/10"
        animate={{ opacity: [0.3, 0.8, 0.3] }}
        transition={{ duration: 3, repeat: Infinity }}
      />
    </div>
    <div className="max-w-md">
      <h2 className="text-xl font-semibold text-white/70 mb-2">AI Readiness Analysis</h2>
      <p className="text-sm text-white/35 leading-relaxed">
        Run a comprehensive evaluation across 15 scientific dimensions — 
        QSAR compliance, predictive feasibility, descriptor quality, and modeling risk.
      </p>
    </div>
    <motion.button
      onClick={onRun}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="flex items-center gap-2.5 px-7 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 
        text-white text-sm font-semibold shadow-lg shadow-cyan-500/15 hover:shadow-cyan-500/30 transition-shadow"
    >
      <Zap className="w-4 h-4" /> Run AI Analysis
    </motion.button>
  </div>
);

// ─── Main Component ──────────────────────────────────────────────────────────
interface Props {
  clientId: string;
  modelingAnalysis: ModelingAnalysis | null;
  modelingLoading: boolean;
  onRunAnalysis: () => Promise<void>;
  activePanel: string;
  setActivePanel: (p: string) => void;
}

const ModelingReadinessWorkspace: React.FC<Props> = ({
  clientId, modelingAnalysis, modelingLoading, onRunAnalysis,
}) => {
  const [exportLoading, setExportLoading] = useState<string | null>(null);
  const [openRisk, setOpenRisk] = useState<string | null>(null);

  const handleExport = useCallback(async (format: 'json' | 'csv' | 'xlsx') => {
    setExportLoading(format);
    try {
      const blob = await modelingApi.exportReport(clientId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `sdo_readiness_${clientId}.${format}`; a.click();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} exported`);
    } catch { toast.error('Export failed'); }
    finally { setExportLoading(null); }
  }, [clientId]);

  // ── Empty / Loading states ──────────────────────────────────────────────
  if (modelingLoading) return <LoadingState />;
  if (!modelingAnalysis) return <EmptyState onRun={onRunAnalysis} />;

  const d = modelingAnalysis;
  const r = d.readiness;
  const viz = d.visualizations;
  const tierColor = TIER_COLOR[r.confidence_tier] || '#6B7280';

  // Interpretation text based on score
  const interpretation =
    r.ai_score >= 80
      ? `Dataset demonstrates strong descriptor completeness and balanced endpoint representation. Suitable for initial QSAR experimentation with moderate overfitting risk given N:P = ${r.n_to_p_ratio.toFixed(1)}.`
      : r.ai_score >= 60
        ? `Dataset shows adequate readiness for exploratory modeling. Address high-priority feature engineering recommendations before training. N:P ratio of ${r.n_to_p_ratio.toFixed(1)} requires regularization.`
        : `Dataset has significant quality gaps that must be resolved before reliable QSAR modeling is possible. Focus on CRITICAL and HIGH severity recommendations first.`;

  // ────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-full pb-16">
      <div className="max-w-[1700px] mx-auto px-6 xl:px-10 pt-8 space-y-10">

        {/* ── Top bar: title + re-run ─────────────────────────────────── */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white/80">AI Readiness Workspace</h1>
            <p className="text-xs text-white/30 mt-0.5">
              {r.n_samples.toLocaleString()} compounds · {r.n_features.toLocaleString()} descriptors · analyzed in {d.meta.elapsed_seconds}s
            </p>
          </div>
          <button
            onClick={onRunAnalysis}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/[0.06] 
              text-white/50 hover:text-white/70 hover:border-white/[0.10] transition-all text-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Re-analyze
          </button>
        </div>

        {/* ── KPI Row ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
          <KPICard label="AI Readiness" value={`${Math.round(r.ai_score)}%`}
            sub={`${r.confidence_tier} confidence`} color={tierColor} icon={Brain} delay={0} />
          <KPICard label="QSAR Score" value={`${Math.round(r.qsar_score)}%`}
            sub={`${d.qsar.oecd_pass_count}/5 OECD principles`} color="#8B5CF6" icon={FlaskConical} delay={0.06} />
          <KPICard label="Dataset Integrity" value={`${Math.round(r.integrity_score)}%`}
            sub={d.quality.health_score >= 80 ? 'Pristine quality' : 'Issues detected'} color="#3B82F6" icon={Shield} delay={0.12} />
          <KPICard label="N : P Ratio" value={r.n_to_p_ratio.toFixed(1)}
            sub={r.n_to_p_ratio >= 10 ? 'Safe dimensionality' : r.n_to_p_ratio >= 3 ? 'Monitor overfitting' : 'High overfitting risk'}
            color={r.n_to_p_ratio >= 10 ? '#10B981' : r.n_to_p_ratio >= 3 ? '#F59E0B' : '#EF4444'}
            icon={Layers} delay={0.18} />
          <KPICard label="Active Risks" value={d.risks.filter(r => r.severity === 'CRITICAL' || r.severity === 'HIGH').length}
            sub={`${d.risks.length} total identified`} color={d.risks.some(r => r.severity === 'CRITICAL') ? '#EF4444' : '#F59E0B'} icon={AlertTriangle} delay={0.24} />
        </div>

        {/* ── Hero Score Section ───────────────────────────────────────── */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Gauge + tier */}
          <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-8 flex flex-col items-center justify-center gap-4">
            <Gauge score={r.ai_score} size={156} />
            <div
              className="px-3 py-1 rounded-full text-xs font-semibold tracking-wider uppercase border"
              style={{ color: tierColor, borderColor: `${tierColor}30`, background: `${tierColor}10` }}
            >
              {r.confidence_tier} Confidence
            </div>
            <p className="text-xs text-white/30 text-center">Overall AI Modeling Readiness</p>
          </div>

          {/* Score breakdown bars */}
          <div className="lg:col-span-2 rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-6 space-y-4">
            <p className="text-xs text-white/40 leading-relaxed mb-2 italic border-l-2 border-white/[0.06] pl-3">
              {interpretation}
            </p>
            <div className="space-y-3 pt-2">
              {[
                ['Descriptor Completeness', r.descriptor_reliability_score],
                ['Data Integrity', r.integrity_score],
                ['Chemical Diversity', r.diversity_score],
                ['Predictive Stability', r.stability_score],
                ['QSAR Compatibility', r.qsar_score],
              ].map(([label, val], i) => (
                <ScoreBar key={label as string} label={label as string} value={Number(val)} delay={i * 0.08} />
              ))}
            </div>
            {r.baseline_performance > 0 && (
              <div className="pt-2 border-t border-white/[0.04] flex items-center gap-3 text-xs text-white/35">
                <Activity className="w-3.5 h-3.5 text-cyan-400/60" />
                Baseline signal: <span className="text-cyan-400 font-semibold">{r.baseline_performance.toFixed(1)}%</span>
                — {r.success_confidence}
              </div>
            )}
          </div>
        </section>

        {/* ── Visualization Grid ───────────────────────────────────────── */}
        <section>
          <SectionHeader title="Scientific Visualizations" subtitle="Interactive dataset diagnostics — zoom, pan, download" icon={Activity} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

            {/* Endpoint Distribution */}
            {viz.endpoint_distribution && (
              <ChartCard title="Endpoint Distribution" subtitle="Target value spread & skewness">
                <OptimizedPlotly
                  data={[{ type: 'histogram', x: viz.endpoint_distribution.values,
                    marker: { color: 'rgba(34,211,238,0.55)', line: { color: 'rgba(34,211,238,0.8)', width: 0.5 } },
                    hovertemplate: 'Value: %{x}<br>Count: %{y}<extra></extra>',
                  }] as any}
                  layout={{ ...BL, height: 260 } as any}
                />
              </ChartCard>
            )}

            {/* Variance Profile */}
            {viz.variance_data && (
              <ChartCard title="Descriptor Variance Profile" subtitle="Top 40 descriptors — low variance = low signal">
                <OptimizedPlotly
                  data={[{ type: 'bar', x: viz.variance_data.variances, y: viz.variance_data.names,
                    orientation: 'h',
                    marker: { color: viz.variance_data.variances.map(v =>
                      v < 0.001 ? '#EF4444' : v < 0.1 ? '#F59E0B' : 'rgba(139,92,246,0.65)') },
                    hovertemplate: '<b>%{y}</b><br>Variance: %{x:.4f}<extra></extra>',
                  }] as any}
                  layout={{ ...BL, height: 260, margin: { ...BL.margin, l: 120 },
                    yaxis: { ...BL.yaxis, autorange: 'reversed' as const } } as any}
                />
              </ChartCard>
            )}

            {/* Missing Value Heatmap — full width */}
            {viz.missing_heatmap && (
              <ChartCard title="Missing Value Heatmap" subtitle="Compound rows × descriptor columns — darker = missing" className="lg:col-span-2">
                <OptimizedPlotly
                  data={[{ type: 'heatmap', z: viz.missing_heatmap.z,
                    x: viz.missing_heatmap.x, colorscale: 'Reds', showscale: true,
                    hovertemplate: '<b>%{x}</b><br>Row %{y}<br>Missing: %{z}<extra></extra>',
                  }] as any}
                  layout={{ ...BL, height: 240 } as any}
                />
              </ChartCard>
            )}

            {/* Correlation Matrix */}
            {viz.correlation_matrix && (
              <ChartCard title="Descriptor Correlation Matrix" subtitle="Pearson r collinearity — deep red/blue = highly correlated">
                <OptimizedPlotly
                  data={[{ type: 'heatmap', z: viz.correlation_matrix.z,
                    x: viz.correlation_matrix.labels, y: viz.correlation_matrix.labels,
                    colorscale: 'RdBu', zmin: -1, zmax: 1,
                    hovertemplate: '%{x} × %{y}<br>r = %{z:.3f}<extra></extra>',
                  }] as any}
                  layout={{ ...BL, height: 300 } as any}
                />
              </ChartCard>
            )}

            {/* Outlier explorer */}
            {viz.outliers && (
              <ChartCard title="Outlier Explorer" subtitle="IQR outliers in rose — normal in cyan">
                <OptimizedPlotly
                  data={[
                    { type: 'scattergl',
                      x: viz.outliers.x.filter((_, i) => !viz.outliers!.is_outlier[i]),
                      y: viz.outliers.y.filter((_, i) => !viz.outliers!.is_outlier[i]),
                      mode: 'markers', name: 'Normal',
                      marker: { color: 'rgba(34,211,238,0.45)', size: 4 },
                      hovertemplate: `${viz.outliers.x_label}: %{x}<br>${viz.outliers.y_label}: %{y}<extra></extra>`,
                    },
                    { type: 'scattergl',
                      x: viz.outliers.x.filter((_, i) => viz.outliers!.is_outlier[i]),
                      y: viz.outliers.y.filter((_, i) => viz.outliers!.is_outlier[i]),
                      mode: 'markers', name: 'Outlier',
                      marker: { color: 'rgba(239,68,68,0.75)', size: 6, symbol: 'diamond' },
                      hovertemplate: `OUTLIER<br>${viz.outliers.x_label}: %{x}<br>${viz.outliers.y_label}: %{y}<extra></extra>`,
                    },
                  ] as any}
                  layout={{ ...BL, height: 300, showlegend: true,
                    legend: { font: { color: 'rgba(255,255,255,0.3)', size: 9 }, bgcolor: 'transparent' },
                    xaxis: { ...BL.xaxis, title: { text: viz.outliers.x_label, font: { size: 9, color: 'rgba(255,255,255,0.25)' } } },
                    yaxis: { ...BL.yaxis, title: { text: viz.outliers.y_label, font: { size: 9, color: 'rgba(255,255,255,0.25)' } } },
                  } as any}
                />
              </ChartCard>
            )}

            {/* Class balance */}
            {viz.class_balance && (
              <ChartCard title="Endpoint Class Balance" subtitle="Distribution of biological endpoint categories">
                <OptimizedPlotly
                  data={[{ type: 'bar', x: viz.class_balance.labels, y: viz.class_balance.counts,
                    marker: { color: 'rgba(139,92,246,0.6)', line: { color: 'rgba(139,92,246,0.9)', width: 0.5 } },
                    hovertemplate: '%{x}: %{y} samples<extra></extra>',
                  }] as any}
                  layout={{ ...BL, height: 260 } as any}
                />
              </ChartCard>
            )}
          </div>
        </section>

        {/* ── QSAR OECD Panel ─────────────────────────────────────────── */}
        <section>
          <SectionHeader title="QSAR Readiness — OECD 5-Principle Compliance" subtitle={`${d.qsar.oecd_pass_count}/5 principles met`} icon={FlaskConical} />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
            {d.qsar.oecd_checks.map((check, i) => (
              <motion.div
                key={check.principle}
                initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
                className={`rounded-2xl border p-4 ${
                  check.status
                    ? 'border-emerald-500/15 bg-emerald-500/[0.04]'
                    : 'border-rose-500/15 bg-rose-500/[0.04]'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {check.status
                    ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    : <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  }
                  <span className="text-[10px] text-white/30 font-medium">Principle {check.principle}</span>
                </div>
                <p className="text-xs font-medium text-white/65 mb-1">{check.name}</p>
                <p className="text-[11px] text-white/35 leading-relaxed">{check.evidence}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* ── Descriptor Readiness ────────────────────────────────────── */}
        <section>
          <SectionHeader title="Descriptor Readiness" subtitle="Completeness by quality tier" icon={Layers} />
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {d.qsar.descriptor_readiness.map((dr, i) => {
              const col = dr.completeness >= 90 ? '#10B981' : dr.completeness >= 60 ? '#F59E0B' : '#EF4444';
              return (
                <motion.div
                  key={dr.category}
                  initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.08 }}
                  className="rounded-2xl border border-white/[0.05] bg-white/[0.02] p-5"
                >
                  <div className="text-2xl font-bold mb-1" style={{ color: col }}>{dr.count}</div>
                  <div className="text-xs text-white/50 font-medium mb-1">{dr.category}</div>
                  <div className="text-[11px] text-white/30 mb-3">{dr.recommendation}</div>
                  <div className="h-1 rounded-full bg-white/[0.06]">
                    <motion.div className="h-full rounded-full" style={{ backgroundColor: col }}
                      initial={{ width: 0 }} animate={{ width: `${dr.completeness}%` }}
                      transition={{ duration: 0.8, delay: i * 0.08 }}
                    />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* ── Scientific Intelligence Panel ───────────────────────────── */}
        <section>
          <SectionHeader title="Scientific Intelligence" subtitle="Automated warnings and recommendations" icon={Brain} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Warnings */}
            <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-5">
              <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-4">Warnings</h3>
              <div className="space-y-2">
                {d.quality.recommendations.map((rec, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                    className="flex items-start gap-2.5 text-xs text-white/50 py-2 border-b border-white/[0.03] last:border-0"
                  >
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400/70 mt-0.5 shrink-0" />
                    {rec}
                  </motion.div>
                ))}
                {d.quality.recommendations.length === 0 && (
                  <div className="flex items-center gap-2 text-xs text-emerald-400/70">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Dataset is pristine and QSAR-ready.
                  </div>
                )}
              </div>
            </div>

            {/* Feature Advisor */}
            <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-5">
              <h3 className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-4">Preprocessing Recommendations</h3>
              <div className="space-y-2">
                {d.features.slice(0, 6).map((feat, i) => {
                  const color = SEV_COLOR[feat.severity] || '#6B7280';
                  return (
                    <motion.div key={feat.id} initial={{ opacity: 0, x: 6 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                      className="py-2 border-b border-white/[0.03] last:border-0"
                    >
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded"
                          style={{ color, background: `${color}18` }}>{feat.severity}</span>
                        <span className="text-xs text-white/60 font-medium">{feat.action}</span>
                      </div>
                      <p className="text-[11px] text-white/30 pl-0 leading-relaxed line-clamp-2">{feat.reasoning}</p>
                      {feat.code_hint && (
                        <div className="mt-1.5 flex items-start gap-1.5">
                          <Code2 className="w-3 h-3 text-white/20 mt-0.5 shrink-0" />
                          <pre className="text-[9px] font-mono text-cyan-300/50 overflow-hidden text-ellipsis whitespace-nowrap max-w-[280px]">
                            {feat.code_hint.split('\n')[0]}
                          </pre>
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* ── Model Recommendations ───────────────────────────────────── */}
        <section>
          <SectionHeader title="Model Recommendations" subtitle="Algorithm suitability ranked for your dataset" icon={Cpu} />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {d.models.slice(0, 6).map((model, i) => {
              const robColor = { HIGH: '#10B981', MEDIUM: '#F59E0B', LOW: '#EF4444' }[model.expected_robustness] || '#6B7280';
              return (
                <motion.div
                  key={model.algorithm}
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07 }}
                  className={`rounded-2xl border bg-white/[0.02] backdrop-blur-xl p-5 hover:border-white/[0.10] transition-colors ${
                    model.suitability_score >= 70 ? 'border-cyan-500/20' : 'border-white/[0.05]'
                  }`}
                >
                  {model.suitability_score >= 70 && (
                    <div className="text-[9px] font-semibold text-cyan-400 tracking-wider uppercase mb-2">✦ Recommended</div>
                  )}
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-sm font-semibold text-white/80">{model.algorithm}</h3>
                      <span className="text-[10px] text-white/30">{model.category}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold" style={{ color: robColor }}>{model.suitability_score}</div>
                      <div className="text-[9px]" style={{ color: robColor }}>{model.expected_robustness}</div>
                    </div>
                  </div>
                  <div className="h-1 rounded-full bg-white/[0.06] mb-3">
                    <motion.div className="h-full rounded-full" style={{ backgroundColor: robColor }}
                      initial={{ width: 0 }} animate={{ width: `${model.suitability_score}%` }}
                      transition={{ duration: 0.8, delay: i * 0.07 }}
                    />
                  </div>
                  <p className="text-[11px] text-white/35 leading-relaxed line-clamp-3">{model.scientific_reasoning}</p>
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* ── Risk Analysis ───────────────────────────────────────────── */}
        <section>
          <SectionHeader title="Risk Analysis" subtitle="Identified modeling risks with probability and mitigation" icon={AlertTriangle} />
          {d.risks.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-emerald-400/70 px-4 py-3 rounded-2xl border border-emerald-500/15 bg-emerald-500/[0.04]">
              <CheckCircle2 className="w-4 h-4" /> No significant modeling risks detected.
            </div>
          ) : (
            <div className="space-y-2">
              {d.risks.map((risk) => {
                const color = SEV_COLOR[risk.severity] || '#6B7280';
                const isOpen = openRisk === risk.risk;
                return (
                  <motion.div key={risk.risk} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    className="rounded-2xl border overflow-hidden"
                    style={{ borderColor: `${color}20`, background: `${color}05` }}
                  >
                    <button className="w-full flex items-center gap-5 px-5 py-4 text-left"
                      onClick={() => setOpenRisk(isOpen ? null : risk.risk)}>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0"
                        style={{ color, background: `${color}18` }}>{risk.severity}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-white/70">{risk.risk}</span>
                          <span className="text-xs text-white/30">{risk.affected_stage}</span>
                        </div>
                        {/* Risk probability bar */}
                        <div className="flex items-center gap-3 mt-1.5">
                          <div className="flex-1 h-1 rounded-full bg-white/[0.05]">
                            <div className="h-full rounded-full" style={{ width: `${risk.probability * 100}%`, backgroundColor: color }} />
                          </div>
                          <span className="text-[10px] text-white/30 w-8 text-right">{Math.round(risk.probability * 100)}%</span>
                        </div>
                      </div>
                      <ChevronDown className={`w-4 h-4 text-white/20 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {isOpen && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="border-t border-white/[0.05] px-5 py-4 grid grid-cols-2 gap-6"
                      >
                        <div>
                          <div className="text-[10px] text-white/30 uppercase tracking-wide mb-1.5">Impact</div>
                          <p className="text-xs text-white/50 leading-relaxed">{risk.impact}</p>
                        </div>
                        <div>
                          <div className="text-[10px] text-white/30 uppercase tracking-wide mb-1.5">Mitigation</div>
                          <p className="text-xs text-cyan-300/60 leading-relaxed">{risk.mitigation}</p>
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          )}
        </section>

        {/* ── Data Quality Funnel ─────────────────────────────────────── */}
        <section>
          <SectionHeader title="Data Quality Pipeline" subtitle="Row count through quality gates" icon={Target} />
          <div className="rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl p-5">
            <div className="flex items-center gap-0 overflow-x-auto">
              {d.quality.funnel.map((f, i) => {
                const pct = i === 0 ? 100 : Math.round((f.count / d.quality.funnel[0].count) * 100);
                const color = pct >= 90 ? '#10B981' : pct >= 70 ? '#F59E0B' : '#EF4444';
                return (
                  <div key={f.stage} className="flex items-center gap-0 shrink-0">
                    <div className="flex flex-col items-center px-6 py-2">
                      <div className="text-xl font-bold tabular-nums" style={{ color }}>{f.count.toLocaleString()}</div>
                      <div className="text-xs text-white/40 mt-0.5 text-center max-w-[100px]">{f.stage}</div>
                      {i > 0 && (
                        <div className="text-[10px] font-semibold mt-1" style={{ color }}>{pct}% retained</div>
                      )}
                    </div>
                    {i < d.quality.funnel.length - 1 && (
                      <div className="text-white/20 text-lg shrink-0">→</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* ── Score Deductions ────────────────────────────────────────── */}
        {r.deductions.length > 0 && (
          <section>
            <SectionHeader title="Scientific Findings" subtitle="Score deduction reasons" icon={TrendingUp} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {r.deductions.map((d_item, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-start gap-3 px-4 py-3 rounded-xl border border-amber-500/10 bg-amber-500/[0.03] text-xs text-white/50"
                >
                  <span className="text-amber-500/60 shrink-0 mt-0.5">→</span>{d_item}
                </motion.div>
              ))}
            </div>
          </section>
        )}

        {/* ── Export Section ───────────────────────────────────────────── */}
        <section>
          <SectionHeader title="Export Report" subtitle="Download the full analysis" icon={Download} />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { format: 'json' as const, icon: FileJson, label: 'Export Readiness JSON', desc: 'Full analysis object — all scores, risks, recommendations' },
              { format: 'csv' as const, icon: FileText, label: 'Export Summary CSV', desc: 'Flat metrics table for quick review' },
              { format: 'xlsx' as const, icon: FileSpreadsheet, label: 'Export Feature Audit XLSX', desc: 'Multi-sheet workbook: scores, risks, features, models' },
            ].map(({ format, icon: Icon, label, desc }) => (
              <button
                key={format}
                onClick={() => handleExport(format)}
                disabled={exportLoading !== null}
                className="flex items-start gap-4 p-5 rounded-2xl border border-white/[0.05] bg-white/[0.02]
                  hover:border-white/[0.09] hover:bg-white/[0.04] transition-all text-left group
                  disabled:opacity-40 disabled:cursor-wait"
              >
                <Icon className="w-5 h-5 text-white/30 group-hover:text-white/50 transition-colors mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm font-medium text-white/60 group-hover:text-white/75 transition-colors mb-0.5">
                    {exportLoading === format ? 'Downloading…' : label}
                  </div>
                  <p className="text-xs text-white/25">{desc}</p>
                </div>
              </button>
            ))}
          </div>
        </section>

      </div>
    </div>
  );
};

export default ModelingReadinessWorkspace;
