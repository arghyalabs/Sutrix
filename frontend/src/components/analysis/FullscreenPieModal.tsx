import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Table2, PieChart as PieChartIcon, Download, Image as ImageIcon, Beaker, BarChart2 } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { toPng } from 'html-to-image';

interface FullscreenPieModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: Array<{ name: string; value: number }>;
  title: string;
  colors: string[];
}

export const FullscreenPieModal: React.FC<FullscreenPieModalProps> = ({
  isOpen, onClose, data, title, colors
}) => {
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart');
  const chartRef = useRef<HTMLDivElement>(null);

  // Compute Research Metrics
  const metrics = useMemo(() => {
    if (!data || data.length === 0) return null;
    
    const total = data.reduce((sum, item) => sum + item.value, 0);
    let shannonEntropy = 0;
    let maxProp = 0;
    let dominantCategory = '';

    const enrichedData = data.map(item => {
      const p = item.value / total;
      if (p > 0) shannonEntropy -= p * Math.log(p);
      if (p > maxProp) {
        maxProp = p;
        dominantCategory = item.name;
      }
      return { ...item, percentage: p * 100 };
    });

    // Shannon Diversity Index: H = -sum(p * ln(p))
    // Evenness: E = H / ln(S) where S is number of categories
    const maxEntropy = Math.log(data.length) || 1;
    const evenness = shannonEntropy / maxEntropy;

    return {
      total,
      shannonEntropy: shannonEntropy.toFixed(3),
      evenness: evenness.toFixed(3),
      dominantCategory,
      dominanceRatio: (maxProp * 100).toFixed(1),
      enrichedData: enrichedData.sort((a, b) => b.value - a.value)
    };
  }, [data]);

  const handleDownloadPng = async () => {
    if (!chartRef.current) return;
    try {
      const filter = (node: Element) => !(node instanceof HTMLElement && node.dataset.downloadIgnore === 'true');
      const dataUrl = await toPng(chartRef.current, { pixelRatio: 2, filter });
      const a = document.createElement('a');
      a.download = `sdo_pie_${title.replace(/\s+/g, '_')}.png`;
      a.href = dataUrl;
      a.click();
    } catch (err) {
      console.error('PNG Export failed:', err);
    }
  };

  const handleDownloadCsv = () => {
    if (!metrics) return;
    const header = 'Category,Value,Percentage\n';
    const body = metrics.enrichedData.map(r => `"${r.name}",${r.value},${r.percentage.toFixed(2)}`).join('\n');
    const blob = new Blob([header + body], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sdo_pie_${title.replace(/\s+/g, '_')}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen || !metrics) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex bg-void/90 backdrop-blur-xl p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="w-full h-full bg-[#080f1f] border border-white/[0.05] shadow-2xl rounded-2xl flex overflow-hidden"
        >
          {/* Main Content Area */}
          <div className="flex-1 flex flex-col p-6 border-r border-white/[0.05]" ref={chartRef}>
            <div className="flex items-center justify-between mb-8" data-download-ignore="true">
              <div>
                <h2 className="text-2xl font-bold text-white">{title}</h2>
                <p className="text-white/40 text-sm mt-1 flex items-center gap-2">
                  <Beaker className="w-4 h-4 text-cyan-500" />
                  Interactive Research View
                </p>
              </div>
              <div className="flex items-center gap-2 bg-white/[0.03] p-1 rounded-xl">
                <button
                  onClick={() => setViewMode('chart')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${viewMode === 'chart' ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/40 hover:text-white'}`}
                >
                  <PieChartIcon className="w-4 h-4" /> Chart
                </button>
                <button
                  onClick={() => setViewMode('table')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all ${viewMode === 'table' ? 'bg-cyan-500/20 text-cyan-400' : 'text-white/40 hover:text-white'}`}
                >
                  <Table2 className="w-4 h-4" /> Data Table
                </button>
              </div>
            </div>

            <div className="flex-1 min-h-0 relative flex items-center justify-center">
              {viewMode === 'chart' ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={metrics.enrichedData}
                      cx="50%"
                      cy="50%"
                      innerRadius="40%"
                      outerRadius="80%"
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {metrics.enrichedData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={colors[index % colors.length]} stroke="rgba(255,255,255,0.05)" />
                      ))}
                    </Pie>
                    <Tooltip 
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const d = payload[0].payload;
                          return (
                            <div className="bg-[#0d1a30] border border-white/[0.08] rounded-xl px-4 py-3 shadow-2xl">
                              <p className="text-cyan-400 font-bold text-base mb-1">{d.name}</p>
                              <div className="space-y-1">
                                <p className="text-white text-sm">Count: <span className="font-bold">{d.value.toLocaleString()}</span></p>
                                <p className="text-white/60 text-xs">Share: <span className="text-white font-mono">{d.percentage.toFixed(1)}%</span></p>
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Legend 
                      layout="vertical" 
                      verticalAlign="middle" 
                      align="right"
                      wrapperStyle={{ paddingLeft: '40px', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="w-full h-full overflow-auto custom-scrollbar pr-4">
                  <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-[#080f1f]/90 backdrop-blur-md z-10">
                      <tr>
                        <th className="py-4 px-4 text-xs font-bold uppercase tracking-wider text-white/40 border-b border-white/[0.05]">Category</th>
                        <th className="py-4 px-4 text-xs font-bold uppercase tracking-wider text-white/40 border-b border-white/[0.05] text-right">Count</th>
                        <th className="py-4 px-4 text-xs font-bold uppercase tracking-wider text-white/40 border-b border-white/[0.05] text-right">Percentage</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.enrichedData.map((row, idx) => (
                        <tr key={idx} className="hover:bg-white/[0.02] border-b border-white/[0.02] transition-colors">
                          <td className="py-3 px-4 text-sm font-medium text-white flex items-center gap-3">
                            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: colors[idx % colors.length] }} />
                            {row.name}
                          </td>
                          <td className="py-3 px-4 text-sm text-white/80 text-right font-mono">{row.value.toLocaleString()}</td>
                          <td className="py-3 px-4 text-sm text-cyan-400 text-right font-mono">{row.percentage.toFixed(2)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Right Sidebar - Analysis Tools */}
          <div className="w-80 bg-white/[0.01] p-6 flex flex-col">
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-violet-400" />
                Analysis
              </h3>
              <button 
                onClick={onClose}
                className="p-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-white/50 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 space-y-6">
              {/* Core Stats */}
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                  <p className="text-xs text-white/40 uppercase tracking-wider font-bold mb-1">Total Records</p>
                  <p className="text-2xl font-bold text-white">{metrics.total.toLocaleString()}</p>
                </div>
                
                <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/20">
                  <p className="text-xs text-cyan-400/60 uppercase tracking-wider font-bold mb-1">Dominant Segment</p>
                  <p className="text-lg font-bold text-cyan-400 truncate" title={metrics.dominantCategory}>{metrics.dominantCategory}</p>
                  <p className="text-sm text-cyan-400/80 mt-1 font-mono">{metrics.dominanceRatio}% of dataset</p>
                </div>
              </div>

              <div className="w-full h-px bg-white/[0.05]" />

              {/* Research Metrics */}
              <div>
                <h4 className="text-xs font-bold text-white/30 uppercase tracking-wider mb-4">Diversity Metrics</h4>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-white/60">Shannon Entropy (H)</span>
                      <span className="text-violet-400 font-mono font-bold">{metrics.shannonEntropy}</span>
                    </div>
                    <p className="text-[10px] text-white/30 leading-relaxed">Measures distributional diversity. Higher values indicate more evenly distributed categories.</p>
                  </div>
                  
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-white/60">Evenness Index (E)</span>
                      <span className="text-emerald-400 font-mono font-bold">{metrics.evenness}</span>
                    </div>
                    <p className="text-[10px] text-white/30 leading-relaxed">Normalized entropy (0 to 1). 1.0 represents perfectly even distribution.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Export Actions */}
            <div className="pt-6 mt-auto border-t border-white/[0.05] space-y-3">
              <button 
                onClick={handleDownloadCsv}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-white font-semibold transition-colors"
              >
                <Download className="w-4 h-4" />
                Export CSV Data
              </button>
              <button 
                onClick={handleDownloadPng}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-void font-bold shadow-[0_0_15px_rgba(34,211,238,0.2)] transition-colors"
              >
                <ImageIcon className="w-4 h-4" />
                Save High-Res Chart
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
