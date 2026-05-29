import React, { useState, useMemo } from 'react';
import { 
  ChevronRight, BarChart2, TrendingUp, CheckCircle, 
  Database, Sliders, CheckCircle2, AlertTriangle, Download, ArrowUp, ArrowDown 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { OptimizedPlotly } from '../charts/OptimizedPlotly';

interface SegregationAnalyticsProps {
  columns: string[];
  mappings: any;
  segregationExecuted: boolean;
  segStats: any;
  handleRunSegregation: (payload: {
    enable_dedup: boolean;
    enable_variance_pruning: boolean;
    prune_high_variance: boolean;
    selected_hierarchy: string[];
  }) => Promise<void>;
  setActiveTab: (tab: string) => void;
  clientId: string;
}

export const SegregationAnalytics: React.FC<SegregationAnalyticsProps> = ({
  columns,
  mappings,
  segregationExecuted,
  segStats,
  handleRunSegregation,
  setActiveTab,
  clientId
}) => {
  // Cleansing and Hierarchy State
  const [enableDedup, setEnableDedup] = useState(false);
  const [enableVariance, setEnableVariance] = useState(false);
  const [pruneHighVariance, setPruneHighVariance] = useState(false);
  const [selectedHierarchy, setSelectedHierarchy] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  // Derive available columns for hierarchy mapping (only columns mapped to valid scientific variables)
  const availableHierarchyCols = useMemo(() => {
    return columns.filter(col => mappings[col] && mappings[col] !== 'none');
  }, [columns, mappings]);

  // Handle checking/unchecking hierarchy columns
  const toggleHierarchyColumn = (col: string) => {
    setSelectedHierarchy(prev => {
      if (prev.includes(col)) {
        return prev.filter(c => c !== col);
      } else {
        return [...prev, col];
      }
    });
  };

  // Reorder hierarchy columns
  const moveColumn = (index: number, direction: 'up' | 'down') => {
    setSelectedHierarchy(prev => {
      const next = [...prev];
      const targetIndex = direction === 'up' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= next.length) return prev;
      
      // Swap
      const temp = next[index];
      next[index] = next[targetIndex];
      next[targetIndex] = temp;
      return next;
    });
  };

  const onExecuteSegregation = async () => {
    setIsRunning(true);
    try {
      await handleRunSegregation({
        enable_dedup: enableDedup,
        enable_variance_pruning: enableVariance,
        prune_high_variance: pruneHighVariance,
        selected_hierarchy: selectedHierarchy.length > 0 ? selectedHierarchy : availableHierarchyCols.slice(0, 2)
      });
    } finally {
      setIsRunning(false);
    }
  };

  // ── BRANCH FLOW ANALYTICS STATE & COMPUTATIONS ──────────────────────
  const validTiers = useMemo(() => {
    if (!segStats || !segStats.statistics) return [];
    return segStats.statistics.hierarchy_variables || [];
  }, [segStats]);

  // Keep track of selected filters at each tier
  const [branchFilters, setBranchFilters] = useState<Record<string, string>>({});

  // Reset subsequent dropdown selections when a higher-level filter changes
  const handleBranchFilterChange = (tierName: string, value: string, tierIndex: number) => {
    setBranchFilters(prev => {
      const updated = { ...prev, [tierName]: value };
      // Delete all lower-level selections
      for (let i = tierIndex + 1; i < validTiers.length; i++) {
        delete updated[validTiers[i]];
      }
      return updated;
    });
  };

  // Get active leaf nodes and calculate interactive branch charts
  const leafNodes = useMemo(() => {
    if (segStats && Array.isArray(segStats.leaf_nodes)) {
      return segStats.leaf_nodes;
    }
    if (segStats && segStats.statistics && Array.isArray(segStats.statistics.leaf_nodes)) {
      return segStats.statistics.leaf_nodes;
    }
    return [];
  }, [segStats]);

  // Computations for active branch distributions
  const branchFlowCharts = useMemo(() => {
    if (!segregationExecuted || validTiers.length < 2 || leafNodes.length === 0) return [];
    
    const steps: any[] = [];
    let currentLeaves = [...leafNodes];

    for (let i = 0; i < validTiers.length - 1; i++) {
      const parentCol = validTiers[i];
      const childCol = validTiers[i + 1];

      // Get all unique values for parentCol in current subset of leaves
      const parentValues = Array.from(new Set(
        currentLeaves.map(leaf => leaf.hierarchy_tags?.[parentCol] || 'Uncategorized')
      )).sort();

      // Selected value for this parentCol
      const selectedParentVal = branchFilters[parentCol] || parentValues[0] || 'Uncategorized';

      // Group leaves in current subset by childCol to compute counts
      const childCounts: Record<string, number> = {};
      const childLeaves = currentLeaves.filter(leaf => 
        (leaf.hierarchy_tags?.[parentCol] || 'Uncategorized') === selectedParentVal
      );

      childLeaves.forEach(leaf => {
        const val = leaf.hierarchy_tags?.[childCol] || 'Uncategorized';
        childCounts[val] = (childCounts[val] || 0) + (leaf.records || 0);
      });

      steps.push({
        parentCol,
        childCol,
        parentValues,
        selectedValue: selectedParentVal,
        data: childCounts
      });

      // Filter leaf node subset for next level
      currentLeaves = childLeaves;
    }

    return steps;
  }, [segregationExecuted, validTiers, leafNodes, branchFilters]);

  // Donut distribution data for primary selected tier
  const [activeTierIndex, setActiveTierIndex] = useState(0);
  const activeTierCol = validTiers[activeTierIndex];

  const donutChartData = useMemo(() => {
    if (!segregationExecuted || !activeTierCol || leafNodes.length === 0) return null;

    const counts: Record<string, number> = {};
    leafNodes.forEach((leaf: any) => {
      const val = leaf.hierarchy_tags?.[activeTierCol] || 'Uncategorized';
      counts[val] = (counts[val] || 0) + (leaf.records || 0);
    });

    const labels = Object.keys(counts);
    const values = Object.values(counts);

    return {
      labels,
      values,
      total: values.reduce((a, b) => a + b, 0)
    };
  }, [segregationExecuted, activeTierCol, leafNodes]);

  // ── DATA REDUCTION FUNNEL COMPUTATIONS ────────────────────────────────
  const funnelChartData = useMemo(() => {
    if (!segregationExecuted || !segStats) return null;

    const stages = ['Raw Ingestion', 'Curated Dataset'];
    const values = [segStats.original_count, segStats.statistics?.input_records || segStats.input_records];

    if (enableDedup && segStats.dedup_stats) {
      stages.push('Deduplicated');
      values.push(segStats.dedup_stats.deduplicated_count);
    }

    if (enableVariance && segStats.variance_summary) {
      stages.push('Variance Pruned');
      values.push(segStats.input_records);
    }

    stages.push('Nested Segregated');
    values.push(segStats.input_records);

    return { stages, values };
  }, [segregationExecuted, segStats, enableDedup, enableVariance]);

  return (
    <div className="max-w-6xl mx-auto py-8 space-y-8">
      
      {/* Page Title */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-2">Step 3: Hierarchical Segregation & Data Analytics</h1>
        <p className="text-secondary text-sm max-w-xl mx-auto">
          Clean, prune, and segregate your dataset. Build folder hierarchies, explore active biological compositions, and download raw structured data packages.
        </p>
      </div>

      <div className="grid lg:grid-cols-12 gap-8 items-start">
        
        {/* Left column: Setup & Cleansing Controls */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* Cleansing controls */}
          <div className="glass p-6 rounded-3xl border-white/[0.06] space-y-4">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Data Cleansing Pipeline</h3>
            </div>
            <p className="text-xs text-secondary leading-relaxed">
              Enable smart deduplication and biological potency variance pruning before building the directory tree.
            </p>

            <div className="space-y-4 pt-2">
              <label className="flex items-start justify-between cursor-pointer group">
                <div className="flex flex-col pr-4">
                  <span className="text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors">Smart Deduplication</span>
                  <span className="text-[10px] text-muted leading-relaxed mt-0.5">Vectorized exact scientific duplicates scanner.</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={enableDedup} 
                  onChange={e => setEnableDedup(e.target.checked)}
                  className="w-4 h-4 rounded border-white/[0.08] bg-void text-cyan-400 focus:ring-cyan-500/20"
                />
              </label>

              <label className="flex items-start justify-between cursor-pointer group">
                <div className="flex flex-col pr-4">
                  <span className="text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors">Log₁₀ Potency Variance Audit</span>
                  <span className="text-[10px] text-muted leading-relaxed mt-0.5">Flag compounds with conflicting potency results (range ≥ 1.0 log₁₀).</span>
                </div>
                <input 
                  type="checkbox" 
                  checked={enableVariance} 
                  onChange={e => {
                    setEnableVariance(e.target.checked);
                    if (!e.target.checked) setPruneHighVariance(false);
                  }}
                  className="w-4 h-4 rounded border-white/[0.08] bg-void text-cyan-400 focus:ring-cyan-500/20"
                />
              </label>

              <AnimatePresence>
                {enableVariance && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden pl-4 border-l border-white/[0.06] pt-1"
                  >
                    <label className="flex items-start justify-between cursor-pointer group">
                      <div className="flex flex-col pr-4">
                        <span className="text-xs font-semibold text-white group-hover:text-cyan-300 transition-colors">Isolate & Prune Conflicts</span>
                        <span className="text-[10px] text-muted leading-relaxed mt-0.5">Drop high-variance potency conflict records.</span>
                      </div>
                      <input 
                        type="checkbox" 
                        checked={pruneHighVariance} 
                        onChange={e => setPruneHighVariance(e.target.checked)}
                        className="w-4 h-4 rounded border-white/[0.08] bg-void text-cyan-400 focus:ring-cyan-500/20"
                      />
                    </label>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>

          {/* Hierarchy Selection Checklist */}
          <div className="glass p-6 rounded-3xl border-white/[0.06] space-y-4">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Nested Folders Hierarchy</h3>
            </div>
            <p className="text-xs text-secondary leading-relaxed">
              Select and order columns to construct the directory nesting sequence (e.g. Endpoint → Species → Duration).
            </p>

            <div className="flex flex-wrap gap-2 pt-2">
              {availableHierarchyCols.map(col => {
                const isSelected = selectedHierarchy.includes(col);
                return (
                  <button
                    key={col}
                    onClick={() => toggleHierarchyColumn(col)}
                    className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all flex items-center gap-1.5
                      ${isSelected
                        ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400'
                        : 'bg-white/[0.02] border-white/[0.06] text-secondary hover:border-white/[0.12] hover:text-white'
                      }
                    `}
                  >
                    {col}
                  </button>
                );
              })}
            </div>

            {selectedHierarchy.length > 0 && (
              <div className="space-y-2 pt-4 border-t border-white/[0.06]">
                <span className="text-[10px] font-bold text-muted uppercase tracking-wider">Hierarchy Sequence Order</span>
                <div className="space-y-1.5">
                  {selectedHierarchy.map((col, idx) => (
                    <div key={col} className="flex items-center justify-between p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                      <span className="text-xs font-semibold text-white">{idx + 1}. {col}</span>
                      <div className="flex items-center gap-1">
                        <button 
                          onClick={() => moveColumn(idx, 'up')} 
                          disabled={idx === 0}
                          className="w-6 h-6 rounded bg-white/[0.03] flex items-center justify-center text-secondary hover:text-white disabled:opacity-30"
                        >
                          <ArrowUp className="w-3.5 h-3.5" />
                        </button>
                        <button 
                          onClick={() => moveColumn(idx, 'down')} 
                          disabled={idx === selectedHierarchy.length - 1}
                          className="w-6 h-6 rounded bg-white/[0.03] flex items-center justify-center text-secondary hover:text-white disabled:opacity-30"
                        >
                          <ArrowDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={onExecuteSegregation}
              disabled={isRunning}
              className="w-full mt-4 flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-white text-void font-bold text-sm shadow-xl hover:bg-gray-100 disabled:opacity-50 transition-colors"
            >
              <CheckCircle className="w-4 h-4" />
              {isRunning ? 'Orchestrating folders...' : 'Execute Cleansing & Segregation'}
            </button>
          </div>

        </div>

        {/* Right column: Audits, Telemetry, and Plotly Analytics */}
        <div className="lg:col-span-7 space-y-6">

          <AnimatePresence mode="wait">
            {!segregationExecuted ? (
              <motion.div 
                key="empty-audit"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="glass p-8 rounded-[2rem] border-white/[0.06] text-center py-20"
              >
                <div className="w-16 h-16 rounded-3xl bg-cyan-500/10 flex items-center justify-center text-cyan-400 mx-auto mb-6">
                  <Sliders className="w-8 h-8" />
                </div>
                <h3 className="text-lg font-bold text-white mb-2">Orchestration Baseline Waiting</h3>
                <p className="text-secondary text-xs max-w-sm mx-auto">
                  Choose directory folder hierarchies and toggle smart sanitizations on the left, then click Execute to compile the visual audits.
                </p>
              </motion.div>
            ) : (
              <motion.div 
                key="audit-content"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                
                {/* Unified Audit Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="glass p-4 rounded-2xl border-white/[0.06]">
                    <span className="block text-[10px] text-muted font-bold uppercase tracking-wider">Ingested Rows</span>
                    <span className="block text-2xl font-black text-white mt-1">{segStats.original_count?.toLocaleString()}</span>
                  </div>
                  <div className="glass p-4 rounded-2xl border-white/[0.06]">
                    <span className="block text-[10px] text-muted font-bold uppercase tracking-wider">Cleaned Rows</span>
                    <span className="block text-2xl font-black text-white mt-1">{segStats.input_records?.toLocaleString()}</span>
                  </div>
                  <div className="glass p-4 rounded-2xl border-white/[0.06]">
                    <span className="block text-[10px] text-muted font-bold uppercase tracking-wider">Folders Built</span>
                    <span className="block text-2xl font-black text-cyan-400 mt-1">{segStats.total_folders?.toLocaleString()}</span>
                  </div>
                  <div className="glass p-4 rounded-2xl border-white/[0.06]">
                    <span className="block text-[10px] text-muted font-bold uppercase tracking-wider">Files Written</span>
                    <span className="block text-2xl font-black text-violet-400 mt-1">{segStats.total_files?.toLocaleString()}</span>
                  </div>
                </div>

                {/* Deduplication Summary */}
                {enableDedup && segStats.dedup_stats && (
                  <div className="glass p-6 rounded-3xl border-emerald-500/10 bg-emerald-500/[0.01] space-y-4">
                    <div className="flex items-center gap-2 text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <h4 className="text-xs font-bold uppercase tracking-wider">Smart Deduplication Summary</h4>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">Original</span>
                        <span className="text-lg font-bold text-white">{segStats.dedup_stats.original_count?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">Deduplicated</span>
                        <span className="text-lg font-bold text-white">{segStats.dedup_stats.deduplicated_count?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">Duplicates Removed</span>
                        <span className="text-lg font-bold text-emerald-400">-{segStats.dedup_stats.duplicates_removed?.toLocaleString()}</span>
                      </div>
                    </div>
                    
                    {segStats.dedup_stats.removed_preview && segStats.dedup_stats.removed_preview.length > 0 && (
                      <div className="border-t border-white/[0.04] pt-3">
                        <span className="text-[10px] text-muted uppercase font-bold tracking-wider mb-2 block">Deduplicated Rows Preview</span>
                        <div className="overflow-x-auto text-[11px] text-secondary max-h-40 overflow-y-auto pr-1">
                          <table className="w-full text-left">
                            <thead>
                              <tr className="border-b border-white/[0.06] text-muted uppercase">
                                {Object.keys(segStats.dedup_stats.removed_preview[0]).slice(0, 5).map(k => (
                                  <th key={k} className="pb-1.5 font-semibold pr-4">{k}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {segStats.dedup_stats.removed_preview.map((row: any, i: number) => (
                                <tr key={i} className="border-b border-white/[0.02]">
                                  {Object.values(row).slice(0, 5).map((v: any, j: number) => (
                                    <td key={j} className="py-1.5 pr-4 text-white/80">{String(v)}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Variance Summary */}
                {enableVariance && segStats.variance_summary && (
                  <div className="glass p-6 rounded-3xl border-violet-500/10 bg-violet-500/[0.01] space-y-4">
                    <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                      <div className="flex items-center gap-2 text-violet-400">
                        <AlertTriangle className="w-4 h-4" />
                        <h4 className="text-xs font-bold uppercase tracking-wider">Log₁₀ Potency Variance Audit</h4>
                      </div>
                      <span className="px-3 py-1.5 rounded-xl bg-violet-500/10 border border-violet-500/20 text-xs font-bold text-violet-400">
                        Consistency: {segStats.variance_summary.consistency_score}%
                      </span>
                    </div>

                    <div className="grid grid-cols-4 gap-4">
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">Groups Scanned</span>
                        <span className="text-lg font-bold text-white">{segStats.variance_summary.total_groups_analyzed?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">Consistent</span>
                        <span className="text-lg font-bold text-emerald-400">{segStats.variance_summary.consistent_count?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">Moderate</span>
                        <span className="text-lg font-bold text-amber-500">{segStats.variance_summary.moderate_count?.toLocaleString()}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-muted block uppercase font-medium">High Conflicts</span>
                        <span className="text-lg font-bold text-rose-500">{segStats.variance_summary.conflict_count?.toLocaleString()}</span>
                      </div>
                    </div>

                    {segStats.variance_summary.conflict_compounds && segStats.variance_summary.conflict_compounds.length > 0 && (
                      <div className="border-t border-white/[0.04] pt-3">
                        <span className="text-[10px] text-rose-400 uppercase font-bold tracking-wider mb-2 block">🛑 HighPotency Conflicts Compounds (10-fold deviation)</span>
                        <div className="overflow-x-auto text-[11px] text-secondary max-h-48 overflow-y-auto pr-1">
                          <table className="w-full text-left">
                            <thead>
                              <tr className="border-b border-white/[0.06] text-muted uppercase">
                                <th className="pb-1.5 font-semibold">Substance</th>
                                <th className="pb-1.5 font-semibold">Endpoint</th>
                                <th className="pb-1.5 font-semibold text-right">Min log₁₀</th>
                                <th className="pb-1.5 font-semibold text-right">Max log₁₀</th>
                                <th className="pb-1.5 font-semibold text-right">log₁₀ Range</th>
                              </tr>
                            </thead>
                            <tbody>
                              {segStats.variance_summary.conflict_compounds.map((row: any, i: number) => (
                                <tr key={i} className="border-b border-white/[0.02] hover:bg-white/[0.01]">
                                  <td className="py-2 pr-4 text-white font-medium">{row.chemical}</td>
                                  <td className="py-2 pr-4">{row.endpoint}</td>
                                  <td className="py-2 text-right">{row.min_log10}</td>
                                  <td className="py-2 text-right">{row.max_log10}</td>
                                  <td className="py-2 text-right text-rose-400 font-bold font-mono">{row.log_range}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Plotly Interactive Donut Distribution */}
                {donutChartData && (
                  <div className="glass p-6 rounded-3xl border-white/[0.06] space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <BarChart2 className="w-4 h-4 text-cyan-400" />
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider">Dataset Composition Distribution</h4>
                      </div>
                      
                      <select 
                        value={activeTierIndex} 
                        onChange={e => setActiveTierIndex(Number(e.target.value))}
                        className="bg-white/[0.03] border border-white/[0.08] text-white rounded-lg px-2.5 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-cyan-500"
                      >
                        {validTiers.map((tier: string, idx: number) => (
                          <option key={tier} value={idx} className="bg-void text-white">{tier}</option>
                        ))}
                      </select>
                    </div>

                    <div className="h-[300px]">
                      <OptimizedPlotly 
                        data={[{
                          labels: donutChartData.labels,
                          values: donutChartData.values,
                          type: 'pie',
                          hole: 0.45,
                          marker: {
                            colors: ['#06B6D4', '#6366F1', '#EC4899', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#14B8A6']
                          },
                          textinfo: 'percent+label',
                          textposition: 'inside',
                          hovertemplate: '<b>%{label}</b><br>Records: %{value}<br>Pct: %{percent}<extra></extra>'
                        }]}
                        layout={{
                          showlegend: true,
                          legend: { orientation: 'h', x: 0, y: -0.2 },
                          margin: { t: 10, b: 10, l: 10, r: 10 },
                          annotations: [{
                            text: `<b>${donutChartData.total.toLocaleString()}</b><br>Records`,
                            showarrow: false,
                            font: { size: 14, color: '#FFFFFF' }
                          }]
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Hierarchical Branch Flow Analytics */}
                {branchFlowCharts.length > 0 && (
                  <div className="glass p-6 rounded-3xl border-white/[0.06] space-y-6">
                    <div className="flex items-center gap-2 pb-3 border-b border-white/[0.06]">
                      <TrendingUp className="w-4 h-4 text-cyan-400" />
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider">🌳 Hierarchical Branch Flow Analytics</h4>
                    </div>
                    
                    <div className="space-y-6">
                      {branchFlowCharts.map((step, idx) => (
                        <div key={step.parentCol} className="space-y-3">
                          <div className="flex items-center justify-between bg-white/[0.02] p-3 rounded-xl border border-white/[0.04]">
                            <span className="text-xs text-secondary">
                              Drill Down Branch at <strong className="text-white">Tier {idx + 1}: {step.parentCol}</strong>
                            </span>
                            <select 
                              value={step.selectedValue}
                              onChange={e => handleBranchFilterChange(step.parentCol, e.target.value, idx)}
                              className="bg-white/[0.03] border border-white/[0.08] text-white rounded-lg px-2.5 py-1 text-xs font-bold focus:outline-none"
                            >
                              {step.parentValues.map((v: string) => (
                                <option key={v} value={v} className="bg-void text-white">{v}</option>
                              ))}
                            </select>
                          </div>

                          <div className="h-[200px]">
                            <OptimizedPlotly 
                              data={[{
                                x: Object.keys(step.data),
                                y: Object.values(step.data),
                                type: 'bar',
                                marker: {
                                  color: '#6366F1'
                                },
                                hovertemplate: '<b>%{x}</b><br>Records: %{y}<extra></extra>'
                              }]}
                              layout={{
                                xaxis: { showgrid: false },
                                yaxis: { showgrid: true, gridcolor: 'rgba(255,255,255,0.04)' },
                                margin: { t: 10, b: 30, l: 30, r: 10 }
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Academic Data Cleansing Funnel */}
                {funnelChartData && (
                  <div className="glass p-6 rounded-3xl border-white/[0.06] space-y-4">
                    <div className="flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-cyan-400" />
                      <h4 className="text-xs font-bold text-white uppercase tracking-wider">Sequential Data Cleansing Funnel</h4>
                    </div>

                    <div className="h-[250px]">
                      <OptimizedPlotly 
                        data={[{
                          type: 'funnel',
                          y: funnelChartData.stages,
                          x: funnelChartData.values,
                          textposition: 'inside',
                          textinfo: 'value+percent initial',
                          connector: { line: { color: '#06B6D4', width: 1 } },
                          marker: {
                            color: ['#0F172A', '#1E293B', '#334155', '#475569', '#64748B'].slice(0, funnelChartData.stages.length)
                          }
                        }]}
                        layout={{
                          margin: { t: 10, b: 10, l: 120, r: 10 }
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Primary Download Raw ZIP */}
                <div className="glass p-6 rounded-3xl border-emerald-500/20 bg-emerald-500/[0.02] flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h4 className="text-sm font-bold text-white">Raw Segregated package</h4>
                    <p className="text-xs text-secondary mt-0.5">Download the raw Excel folder structure (excluding description enrichments).</p>
                  </div>
                  
                  <a 
                    href={`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'}/api/segregate/${clientId}/download`}
                    download
                    className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-white text-void font-bold text-xs hover:bg-gray-100 transition-colors shadow-lg"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Raw ZIP Archive
                  </a>
                </div>

                {/* Navigation Button */}
                <div className="flex justify-end pt-4">
                  <button 
                    onClick={() => setActiveTab('enrichment')}
                    className="flex items-center gap-2 px-6 py-3 rounded-xl bg-cyan-500 text-void font-bold text-sm shadow-xl hover:bg-cyan-400 transition-colors"
                  >
                    Proceed to Enrichment
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

              </motion.div>
            )}
          </AnimatePresence>
          
        </div>
      </div>
    </div>
  );
};
