import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import Plot from 'react-plotly.js';
import { Maximize2, Download } from 'lucide-react';
import { toPng } from 'html-to-image';
import type { ModelingAnalysis } from '../../types';

const ChartCard: React.FC<{ title: string; subtitle?: string; children: React.ReactNode }> = ({
  title, subtitle, children
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const download = async () => {
    if (!ref.current) return;
    const png = await toPng(ref.current, { backgroundColor: '#0A0F1E' });
    const a = document.createElement('a'); a.href = png; a.download = `${title.replace(/\s+/g, '_')}.png`; a.click();
  };
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden"
    >
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div>
          <h3 className="text-sm font-semibold text-white/80">{title}</h3>
          {subtitle && <p className="text-xs text-white/30 mt-0.5">{subtitle}</p>}
        </div>
        <button onClick={download}
          className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.06] transition-colors">
          <Download className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="p-4">{children}</div>
    </motion.div>
  );
};

const plotConfig = { displayModeBar: false, responsive: true };
const baseLayout = {
  paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
  margin: { t: 10, b: 40, l: 50, r: 10 }, height: 280,
  font: { family: 'Inter, sans-serif', color: 'rgba(255,255,255,0.4)', size: 10 },
  xaxis: { gridcolor: 'rgba(255,255,255,0.04)', tickfont: { color: 'rgba(255,255,255,0.3)', size: 9 } },
  yaxis: { gridcolor: 'rgba(255,255,255,0.04)', tickfont: { color: 'rgba(255,255,255,0.3)', size: 9 } },
  showlegend: false,
};

const ChartVisualizationsTab: React.FC<{ data: ModelingAnalysis }> = ({ data }) => {
  const viz = data.visualizations;

  return (
    <div className="p-6 space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-white">Scientific Visualizations</h2>
        <p className="text-sm text-white/40 mt-1">Interactive dataset diagnostics — hover, zoom, and download any chart</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

        {/* Missing Heatmap */}
        {viz.missing_heatmap && (
          <ChartCard title="Missing Value Heatmap" subtitle="Compound rows × descriptor columns">
            <Plot
              data={[{
                type: 'heatmap', z: viz.missing_heatmap.z,
                x: viz.missing_heatmap.x, colorscale: 'Reds',
                showscale: true, hovertemplate: '<b>%{x}</b><br>Row %{y}<br>Missing: %{z}<extra></extra>',
              }] as any}
              layout={{ ...baseLayout, height: 240 } as any}
              config={plotConfig}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </ChartCard>
        )}

        {/* Endpoint Distribution */}
        {viz.endpoint_distribution && (
          <ChartCard title="Endpoint Distribution" subtitle="Target value spread and skew detection">
            <Plot
              data={[{
                type: 'histogram', x: viz.endpoint_distribution.values,
                marker: { color: 'rgba(34,211,238,0.6)', line: { color: 'rgba(34,211,238,0.9)', width: 0.5 } },
                hovertemplate: 'Value: %{x}<br>Count: %{y}<extra></extra>',
              }] as any}
              layout={{ ...baseLayout } as any}
              config={plotConfig}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </ChartCard>
        )}

        {/* Variance Explorer */}
        {viz.variance_data && (
          <ChartCard title="Descriptor Variance Profile" subtitle="Top 40 descriptors sorted by variance">
            <Plot
              data={[{
                type: 'bar',
                x: viz.variance_data.variances,
                y: viz.variance_data.names,
                orientation: 'h',
                marker: {
                  color: viz.variance_data.variances.map(v =>
                    v < 0.001 ? '#EF4444' : v < 0.1 ? '#F59E0B' : 'rgba(139,92,246,0.7)'
                  ),
                },
                hovertemplate: '<b>%{y}</b><br>Variance: %{x:.4f}<extra></extra>',
              }] as any}
              layout={{
                ...baseLayout, height: 320,
                margin: { ...baseLayout.margin, l: 130 },
                yaxis: { ...baseLayout.yaxis, autorange: 'reversed' as const },
              } as any}
              config={plotConfig}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </ChartCard>
        )}

        {/* Correlation Matrix */}
        {viz.correlation_matrix && (
          <ChartCard title="Descriptor Correlation Matrix" subtitle="Pearson r — collinearity analysis (top 25)">
            <Plot
              data={[{
                type: 'heatmap',
                z: viz.correlation_matrix.z,
                x: viz.correlation_matrix.labels,
                y: viz.correlation_matrix.labels,
                colorscale: 'RdBu', zmin: -1, zmax: 1,
                hovertemplate: '%{x} × %{y}<br>r = %{z:.3f}<extra></extra>',
              }] as any}
              layout={{ ...baseLayout, height: 300 } as any}
              config={plotConfig}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </ChartCard>
        )}

        {/* Outlier Explorer */}
        {viz.outliers && (
          <ChartCard title="Outlier Explorer" subtitle="IQR-based outliers highlighted in rose">
            <Plot
              data={[
                {
                  type: 'scattergl',
                  x: viz.outliers.x.filter((_, i) => !viz.outliers!.is_outlier[i]),
                  y: viz.outliers.y.filter((_, i) => !viz.outliers!.is_outlier[i]),
                  mode: 'markers',
                  name: 'Normal',
                  marker: { color: 'rgba(34,211,238,0.5)', size: 4 },
                  hovertemplate: `${viz.outliers.x_label}: %{x}<br>${viz.outliers.y_label}: %{y}<extra></extra>`,
                },
                {
                  type: 'scattergl',
                  x: viz.outliers.x.filter((_, i) => viz.outliers!.is_outlier[i]),
                  y: viz.outliers.y.filter((_, i) => viz.outliers!.is_outlier[i]),
                  mode: 'markers',
                  name: 'Outlier',
                  marker: { color: 'rgba(239,68,68,0.8)', size: 6, symbol: 'diamond' },
                  hovertemplate: `OUTLIER<br>${viz.outliers.x_label}: %{x}<br>${viz.outliers.y_label}: %{y}<extra></extra>`,
                },
              ] as any}
              layout={{
                ...baseLayout, showlegend: true,
                legend: { font: { color: 'rgba(255,255,255,0.4)', size: 10 }, bgcolor: 'transparent' },
                xaxis: { ...baseLayout.xaxis, title: { text: viz.outliers.x_label, font: { size: 10, color: 'rgba(255,255,255,0.3)' } } },
                yaxis: { ...baseLayout.yaxis, title: { text: viz.outliers.y_label, font: { size: 10, color: 'rgba(255,255,255,0.3)' } } },
              } as any}
              config={plotConfig}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </ChartCard>
        )}

        {/* Class Balance */}
        {viz.class_balance && (
          <ChartCard title="Endpoint Class Balance" subtitle="Distribution of biological endpoint categories">
            <Plot
              data={[{
                type: 'bar',
                x: viz.class_balance.labels,
                y: viz.class_balance.counts,
                marker: { color: 'rgba(139,92,246,0.7)', line: { color: 'rgba(139,92,246,1)', width: 0.5 } },
                hovertemplate: '%{x}: %{y} samples<extra></extra>',
              }] as any}
              layout={{ ...baseLayout } as any}
              config={plotConfig}
              style={{ width: '100%' }}
              useResizeHandler
            />
          </ChartCard>
        )}
      </div>
    </div>
  );
};

export default ChartVisualizationsTab;
