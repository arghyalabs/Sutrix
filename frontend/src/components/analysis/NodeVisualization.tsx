import React, { useRef, useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Download, Image, FileText, Maximize2 } from 'lucide-react';
import { toPng } from 'html-to-image';
import { FullscreenPieModal } from './FullscreenPieModal';

interface NodeDetail {
  id: string;
  metadata: any;
  stats: {
    total_rows: number;
    missing_cells: number;
    numeric_cols: number;
    categorical_cols: number;
    unique_compounds: number;
    missing_pct: number;
  };
  charts: {
    composition_pie?: { labels: string[]; values: number[]; title: string };
    composition_bar?: { x: string[]; y: number[]; title: string };
    statistical_table?: Array<{
      subgroup: string; count: number; percentage: number; missing: number; duplicates: number;
    }>;
    distributions?: Record<string, {
      counts: number[]; bins: number[]; mean: number; median: number; std: number;
    }>;
  };
  export_formats: string[];
}

interface NodeVisualizationProps {
  nodeDetail: NodeDetail | null;
  isLoading: boolean;
}

const CHART_COLORS = ['#22d3ee', '#8b5cf6', '#10b981', '#f59e0b', '#f43f5e', '#3b82f6', '#ec4899', '#84cc16'];

const CustomPieTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0d1a30] border border-white/[0.08] rounded-xl px-3 py-2 shadow-2xl">
        <p className="text-cyan-400 font-bold text-sm">{payload[0].name}</p>
        <p className="text-white text-sm">{payload[0].value.toLocaleString()}</p>
        <p className="text-white/40 text-xs">{payload[0].payload?.pct?.toFixed(1)}%</p>
      </div>
    );
  }
  return null;
};

const CustomBarTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#0d1a30] border border-white/[0.08] rounded-xl px-3 py-2 shadow-2xl">
        <p className="text-white/60 text-xs mb-1">{label}</p>
        <p className="text-cyan-400 font-bold text-sm">{payload[0].value.toLocaleString()}</p>
      </div>
    );
  }
  return null;
};

const SkeletonBlock: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`bg-white/[0.03] rounded-xl animate-pulse ${className}`} />
);

// ── Download helpers ──────────────────────────────────────────────────────────

/**
 * Captures the full DOM element (card + chart, exactly as rendered)
 * using html-to-image for pixel-perfect output. The dark card background
 * is included automatically since it's part of the element.
 */
async function downloadChartAsPng(
  containerRef: React.RefObject<HTMLDivElement | null>,
  filename: string
) {
  const el = containerRef.current;
  if (!el) return;

  // Exclude any element marked with data-download-ignore (e.g. the PNG button)
  const filter = (node: Element) =>
    !(node instanceof HTMLElement && node.dataset.downloadIgnore === 'true');

  try {
    // Two-pass: first warms up font/style loading, second captures the final result
    await toPng(el, { pixelRatio: 2, cacheBust: true, filter });
    const dataUrl = await toPng(el, { pixelRatio: 2, cacheBust: true, filter });

    const a = document.createElement('a');
    a.download = filename;
    a.href = dataUrl;
    a.click();
  } catch (err) {
    console.error('[SDO] Chart PNG export failed:', err);
  }
}

/** Downloads statistical table as CSV. */
function downloadTableAsCsv(
  rows: Array<{ subgroup: string; count: number; percentage: number; missing: number; duplicates: number }>,
  filename: string
) {
  const header = 'Subgroup,Count,Percentage (%),Missing,Duplicates\n';
  const body = rows
    .map(r => `${r.subgroup},${r.count},${r.percentage.toFixed(2)},${r.missing},${r.duplicates}`)
    .join('\n');
  const blob = new Blob([header + body], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Download button ───────────────────────────────────────────────────────────

const DownloadBtn: React.FC<{
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
}> = ({ label, icon, onClick }) => (
  <button
    onClick={onClick}
    title={`Download ${label}`}
    data-download-ignore="true"
    className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg
      bg-white/[0.04] border border-white/[0.06] text-white/40
      hover:bg-cyan-500/10 hover:border-cyan-500/30 hover:text-cyan-400
      text-[10px] font-semibold uppercase tracking-wider transition-all"
  >
    {icon ?? <Download className="w-3 h-3" />}
    {label}
  </button>
);

// ── Chart card wrapper ────────────────────────────────────────────────────────

/**
 * A card wrapper with a title row + download button.
 * The ref is attached here so `html-to-image` captures the full card
 * including the dark background and title — matching the screen exactly.
 */
const ChartCard = React.forwardRef<
  HTMLDivElement,
  {
    title: string;
    subtitle?: string;
    onDownload: () => void;
    onExpand?: () => void;
    downloadLabel?: string;
    downloadIcon?: React.ReactNode;
    children: React.ReactNode;
  }
>(({ title, subtitle, onDownload, onExpand, downloadLabel = 'PNG', downloadIcon, children }, ref) => (
  <div
    ref={ref}
    className="p-5 rounded-2xl bg-[#080f1f] border border-white/[0.07] flex flex-col overflow-visible"
  >
    <div className="flex items-start justify-between mb-3 shrink-0">
      <div>
        <h4 className="text-sm font-bold text-white">{title}</h4>
        {subtitle && (
          <p className="text-[10px] text-white/30 mt-0.5 font-mono">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-2">
        {onExpand && (
          <button
            onClick={onExpand}
            title="Open in Interactive Fullscreen"
            data-download-ignore="true"
            className="flex items-center justify-center w-7 h-7 rounded-lg bg-white/[0.04] border border-white/[0.06] text-white/40 hover:bg-violet-500/10 hover:border-violet-500/30 hover:text-violet-400 transition-all"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        )}
        <DownloadBtn label={downloadLabel} icon={downloadIcon} onClick={onDownload} />
      </div>
    </div>
    {children}
  </div>
));
ChartCard.displayName = 'ChartCard';

// ── Distribution histogram card (needs its own ref per instance) ──────────────

const DistributionCard: React.FC<{
  colName: string;
  dist: { counts: number[]; bins: number[]; mean: number; median: number; std: number };
  nodeId: string;
}> = ({ colName, dist, nodeId }) => {
  const ref = useRef<HTMLDivElement>(null);

  const histData = dist.bins.slice(0, -1).map((bin, i) => ({
    bin: bin.toFixed(2),
    count: dist.counts[i] ?? 0,
  }));

  return (
    <div
      ref={ref}
      className="p-4 rounded-xl bg-[#080f1f] border border-white/[0.05]"
    >
      <div className="flex items-center justify-between mb-2">
        <div>
          <p className="text-xs font-bold text-white/70">{colName}</p>
          <p className="text-[10px] text-white/30 font-mono">
            μ={dist.mean.toFixed(2)} · σ={dist.std.toFixed(2)}
          </p>
        </div>
        <button
          onClick={() => downloadChartAsPng(ref, `sdo_histogram_${colName}_${nodeId}.png`)}
          title="Download histogram"
          className="p-1 rounded-lg bg-white/[0.03] border border-white/[0.06] text-white/30
            hover:bg-cyan-500/10 hover:border-cyan-500/30 hover:text-cyan-400 transition-all"
        >
          <Download className="w-3 h-3" />
        </button>
      </div>
      <ResponsiveContainer width="100%" height={100}>
        <BarChart data={histData} margin={{ top: 4, right: 0, left: -30, bottom: 0 }}>
          <XAxis dataKey="bin" tick={false} axisLine={false} />
          <YAxis tick={false} axisLine={false} />
          <Tooltip content={<CustomBarTooltip />} />
          <Bar dataKey="count" fill="#8b5cf6" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

export const NodeVisualization: React.FC<NodeVisualizationProps> = ({ nodeDetail, isLoading }) => {
  const pieRef = useRef<HTMLDivElement>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const [isPieFullscreen, setIsPieFullscreen] = useState(false);

  const handleDownloadPie = useCallback(() => {
    downloadChartAsPng(pieRef, `sdo_pie_chart_${nodeDetail?.id ?? 'node'}.png`);
  }, [nodeDetail?.id]);

  const handleDownloadBar = useCallback(() => {
    downloadChartAsPng(barRef, `sdo_bar_chart_${nodeDetail?.id ?? 'node'}.png`);
  }, [nodeDetail?.id]);

  const handleDownloadTable = useCallback(() => {
    if (!nodeDetail?.charts.statistical_table) return;
    downloadTableAsCsv(
      nodeDetail.charts.statistical_table,
      `sdo_statistical_summary_${nodeDetail.id}.csv`
    );
  }, [nodeDetail]);

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <SkeletonBlock className="h-8 w-48" />
        <div className="grid grid-cols-2 gap-6">
          <SkeletonBlock className="h-80" />
          <SkeletonBlock className="h-80" />
        </div>
        <SkeletonBlock className="h-48" />
      </div>
    );
  }

  if (!nodeDetail) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-white/20 p-12">
        <div className="w-20 h-20 rounded-full bg-white/[0.03] flex items-center justify-center mb-4">
          <svg className="w-10 h-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <p className="text-sm font-medium">Select a node to view analytics</p>
      </div>
    );
  }

  const { charts, stats } = nodeDetail;

  // ── Data transforms ──────────────────────────────────────────────────────
  const pieData = charts.composition_pie
    ? charts.composition_pie.labels.map((label, i) => {
        const total = charts.composition_pie!.values.reduce((a, b) => a + b, 0);
        return {
          name: label,
          value: charts.composition_pie!.values[i],
          pct: total > 0 ? (charts.composition_pie!.values[i] / total) * 100 : 0,
        };
      })
    : [];

  const barData = charts.composition_bar
    ? charts.composition_bar.x.map((x, i) => ({
        name: x,
        value: charts.composition_bar!.y[i],
      }))
    : [];

  const distributions = charts.distributions ? Object.entries(charts.distributions) : [];

  // Build subtitle from backend title (e.g., "endpoint" → shown as small column badge)
  const pieSubtitle = charts.composition_pie?.title
    ? `column: ${charts.composition_pie.title}`
    : undefined;
  const barSubtitle = charts.composition_bar?.title
    ? `column: ${charts.composition_bar.title}`
    : undefined;

  return (
    <div className="overflow-y-auto h-full custom-scrollbar">
      <AnimatePresence mode="wait">
        <motion.div
          key={nodeDetail.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="p-6 space-y-6"
        >
          {/* ── KPI row ── */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Total Rows', value: stats.total_rows?.toLocaleString() ?? '—', color: 'text-cyan-400' },
              { label: 'Unique Compounds', value: stats.unique_compounds?.toLocaleString() ?? '—', color: 'text-violet-400' },
              { label: 'Missing %', value: `${stats.missing_pct?.toFixed(1) ?? 0}%`, color: 'text-amber-400' },
            ].map(s => (
              <div key={s.label} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                <p className="text-[10px] uppercase tracking-wider text-white/40 font-bold mb-1">{s.label}</p>
                <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* ── Charts row ── */}
          <div className="grid grid-cols-2 gap-5">

            {/* Pie Chart */}
            {pieData.length > 0 && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.1 }}>
                <ChartCard
                  ref={pieRef}
                  title="Pie Chart"
                  subtitle={pieSubtitle}
                  onDownload={handleDownloadPie}
                  onExpand={() => setIsPieFullscreen(true)}
                  downloadIcon={<Image className="w-3 h-3" />}
                >
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart margin={{ top: 16, right: 10, bottom: 0, left: 10 }}>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="47%"
                        innerRadius={54}
                        outerRadius={82}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {pieData.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomPieTooltip />} />
                      <Legend
                        wrapperStyle={{ paddingTop: '12px' }}
                        formatter={(value) => (
                          <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: '11px' }}>{value}</span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartCard>
              </motion.div>
            )}

            {/* Bar Chart */}
            {barData.length > 0 && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.15 }}>
                <ChartCard
                  ref={barRef}
                  title="Bar Chart"
                  subtitle={barSubtitle}
                  onDownload={handleDownloadBar}
                  downloadIcon={<Image className="w-3 h-3" />}
                >
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={barData} margin={{ top: 10, right: 6, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip content={<CustomBarTooltip />} />
                      <Bar dataKey="value" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </motion.div>
            )}
          </div>

          {/* ── Statistical Summary ── */}
          {charts.statistical_table && charts.statistical_table.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="p-5 rounded-2xl bg-white/[0.02] border border-white/[0.05] overflow-hidden"
            >
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-bold text-white">Statistical Summary</h4>
                <DownloadBtn
                  label="CSV"
                  icon={<FileText className="w-3 h-3" />}
                  onClick={handleDownloadTable}
                />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06]">
                      {['Subgroup', 'Count', '%', 'Missing', 'Duplicates'].map(h => (
                        <th key={h} className="text-left px-3 py-2.5 text-white/40 font-bold uppercase tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.03]">
                    {charts.statistical_table.map((row, i) => (
                      <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-3 py-2.5 text-white font-medium">{row.subgroup}</td>
                        <td className="px-3 py-2.5 text-cyan-400 font-bold">{row.count.toLocaleString()}</td>
                        <td className="px-3 py-2.5 text-white/60">{row.percentage.toFixed(1)}%</td>
                        <td className="px-3 py-2.5 text-amber-400/80">{row.missing}</td>
                        <td className="px-3 py-2.5 text-white/40">{row.duplicates}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}

          {/* ── Numeric Distributions ── */}
          {distributions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="space-y-4"
            >
              <h4 className="text-sm font-bold text-white">Numeric Distributions</h4>
              <div className="grid grid-cols-2 gap-4">
                {distributions.slice(0, 4).map(([colName, dist]) => (
                  <DistributionCard
                    key={colName}
                    colName={colName}
                    dist={dist}
                    nodeId={nodeDetail.id}
                  />
                ))}
              </div>
            </motion.div>
          )}

          <div className="pt-2" />
        </motion.div>
      </AnimatePresence>

      <FullscreenPieModal
        isOpen={isPieFullscreen}
        onClose={() => setIsPieFullscreen(false)}
        data={pieData}
        title={charts.composition_pie?.title ? `Composition Analysis: ${charts.composition_pie.title}` : "Pie Chart Analysis"}
        colors={CHART_COLORS}
      />
    </div>
  );
};
