import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Download, FileText, Archive, ArrowRight, RotateCcw, GitBranch, FolderOpen, CheckCircle, AlertCircle } from 'lucide-react';
import { hierarchyApi } from '../../services/hierarchyApi';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';
import { SUTRIXLogo } from '../ui/SUTRIXLogo';

interface ReportsExportProps {
  clientId: string;
  activeJobId: string | null;
  handleResetWorkspace: () => void;
}

interface HierarchyNode {
  id: string;
  path: string;
  filter_col: string;
  filter_val: string;
  row_count: number;
  is_leaf: boolean;
  level: number;
}

export const ReportsExport: React.FC<ReportsExportProps> = ({
  clientId,
  activeJobId,
  handleResetWorkspace
}) => {
  const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const { activeLineage } = useWorkspaceStore();
  const [hierarchyNodes, setHierarchyNodes] = useState<HierarchyNode[]>([]);
  const [isLoadingHierarchy, setIsLoadingHierarchy] = useState(false);
  const [hasHierarchy, setHasHierarchy] = useState(false);

  const downloadZipUrl = `${API_BASE}/api/compliance/${clientId}/download`;
  const downloadPdfUrl = `${API_BASE}/api/compliance/${clientId}/report`;
  const downloadParquetUrl = activeJobId ? `${API_BASE}/api/jobs/${clientId}/download_enriched_parquet?job_id=${activeJobId}` : '#';

  // Load hierarchy tree if available
  useEffect(() => {
    if (activeLineage?.nodes) {
      setHierarchyNodes(activeLineage.nodes);
      setHasHierarchy(true);
    } else if (clientId) {
      setIsLoadingHierarchy(true);
      hierarchyApi.getTree(clientId)
        .then((tree: any) => {
          if (tree?.nodes?.length > 0) {
            setHierarchyNodes(tree.nodes);
            setHasHierarchy(true);
          }
        })
        .catch(() => setHasHierarchy(false))
        .finally(() => setIsLoadingHierarchy(false));
    }
  }, [clientId, activeLineage]);

  const leafNodes = hierarchyNodes.filter(n => n.is_leaf);
  const totalRows = hierarchyNodes.reduce((sum, n) => n.is_leaf ? sum + (n.row_count || 0) : sum, 0);

  const levelColors = [
    'text-emerald-400 bg-emerald-500/10',
    'text-cyan-400 bg-cyan-500/10',
    'text-violet-400 bg-violet-500/10',
    'text-amber-400 bg-amber-500/10',
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Export & Reports</h1>
        <p className="text-white/40 text-sm mt-1">
          Download your hierarchy datasets, enriched matrices, and compliance documents.
        </p>
      </div>

      {/* FINAL OUTPUT: Full Compliance Package (Highlighted) */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass p-8 rounded-2xl border-2 border-emerald-500/50 bg-emerald-500/5 relative overflow-hidden shadow-[0_0_40px_rgba(16,185,129,0.15)]"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 to-teal-500" />
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 flex items-center justify-center shrink-0">
              <Archive className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-white font-bold text-lg">Full Compliance Package</h2>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-wider">
                  Complete
                </span>
              </div>
              <p className="text-white/60 text-sm max-w-xl leading-relaxed">
                Download the complete regulatory compliance package containing the manifest metadata, master index, and all segregated target datasets structured for toxicological submissions.
              </p>
            </div>
          </div>
          
          <div className="shrink-0">
            <a
              href={downloadZipUrl}
              download
              className="flex items-center gap-2 px-8 py-4 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-void font-bold shadow-[0_0_20px_rgba(16,185,129,0.4)] hover:shadow-[0_0_30px_rgba(16,185,129,0.6)] transition-all hover:-translate-y-0.5"
            >
              Download ZIP <ArrowRight className="w-5 h-5" />
            </a>
          </div>
        </div>
      </motion.div>

      {/* Final Enriched Dataset (QSAR Ready) - Unhighlighted */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="glass p-6 rounded-2xl group hover:border-cyan-500/20 transition-all border border-white/[0.06]"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 flex items-center justify-center shrink-0">
              <Download className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-white font-bold text-sm">Final Enriched Dataset (QSAR Ready)</h3>
                {activeJobId ? (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold uppercase tracking-wider">
                    Ready
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/40 text-[10px] font-bold uppercase tracking-wider">
                    Pending
                  </span>
                )}
              </div>
              <p className="text-white/40 text-xs max-w-xl leading-relaxed">
                Snappy-compressed Parquet matrix containing all selected molecular descriptors and topology fingerprints. Optimized for AI/QSAR modeling.
              </p>
            </div>
          </div>
          
          <div className="shrink-0">
            {activeJobId ? (
              <a
                href={downloadParquetUrl}
                download
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl
                  bg-white/[0.04] text-white text-xs font-semibold
                  hover:bg-cyan-500/10 hover:text-cyan-400 transition-colors"
              >
                Download Parquet <ArrowRight className="w-4 h-4" />
              </a>
            ) : (
              <button
                disabled
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.02] text-white/20 text-xs font-semibold cursor-not-allowed border border-white/[0.04]"
              >
                <AlertCircle className="w-4 h-4 opacity-40" />
                Run Enrichment First
              </button>
            )}
          </div>
        </div>
      </motion.div>

      {/* Section 1: Raw Hierarchy Export */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-white/[0.06] overflow-hidden"
      >
        <div className="px-6 py-4 bg-white/[0.02] border-b border-white/[0.06] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            <div>
              <h2 className="text-white font-bold text-sm">Raw Hierarchy Export</h2>
              <p className="text-white/40 text-xs mt-0.5">
                Curated datasets per hierarchy branch in a structured folder ZIP
              </p>
            </div>
          </div>
          {hasHierarchy && (
            <div className="flex items-center gap-3 text-xs text-white/40">
              <span>{hierarchyNodes.length} nodes</span>
              <span>·</span>
              <span>{leafNodes.length} leaf datasets</span>
              <span>·</span>
              <span>{totalRows.toLocaleString()} total rows</span>
            </div>
          )}
        </div>

        {hasHierarchy ? (
          <div>
            {/* Tree preview */}
            <div className="px-6 py-4 max-h-64 overflow-y-auto custom-scrollbar bg-[#040810]">
              {hierarchyNodes.slice(0, 20).map((node, i) => (
                <motion.div
                  key={node.id}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.02 }}
                  className="flex items-center gap-2 py-1.5"
                  style={{ paddingLeft: `${(node.level * 20) + 8}px` }}
                >
                  <FolderOpen className={`w-3 h-3 shrink-0 ${levelColors[Math.min(node.level, 3)].split(' ')[0]}`} />
                  <span className="text-xs text-white/50 font-mono">
                    {node.filter_col ? (
                      <>
                        <span className="text-white/30">{node.filter_col}</span>
                        <span className="text-white/20 mx-1">=</span>
                        <span className={levelColors[Math.min(node.level, 3)].split(' ')[0]}>{node.filter_val}</span>
                      </>
                    ) : (
                      <span className="text-emerald-400">Root Dataset</span>
                    )}
                  </span>
                  <span className="ml-auto text-[10px] text-white/20 font-mono">
                    {node.row_count?.toLocaleString()} rows
                    {node.is_leaf && <span className="ml-1.5 text-violet-400/60">leaf</span>}
                  </span>
                </motion.div>
              ))}
              {hierarchyNodes.length > 20 && (
                <div className="py-2 text-center text-xs text-white/20">
                  ...and {hierarchyNodes.length - 20} more nodes
                </div>
              )}
            </div>

            {/* Download button */}
            <div className="px-6 py-4 border-t border-white/[0.06] flex items-center justify-between">
              <div className="text-xs text-white/30">
                ZIP contains: <span className="text-white/50">data.csv + data.parquet per node, manifest.json</span>
              </div>
              <button
                onClick={() => hierarchyApi.exportAll(clientId)}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-white text-black font-bold text-sm shadow-[0_4px_14px_rgba(255,255,255,0.15)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.25)] hover:-translate-y-0.5 active:translate-y-0 transition-all"
              >
                <Download className="w-4 h-4" />
                Download Full Hierarchy ZIP
              </button>
            </div>
          </div>
        ) : isLoadingHierarchy ? (
          <div className="px-6 py-8 text-center">
            <SUTRIXLogo className="w-8 h-8 mx-auto mb-3" />
            <p className="text-white/30 text-sm">Loading hierarchy tree...</p>
          </div>
        ) : (
          <div className="px-6 py-8 text-center">
            <AlertCircle className="w-8 h-8 text-white/10 mx-auto mb-3" />
            <p className="text-white/30 text-sm font-medium">No hierarchy available</p>
            <p className="text-white/20 text-xs mt-1">
              Complete the Hierarchy Builder step first to enable structured exports.
            </p>
          </div>
        )}
      </motion.div>

      {/* Section 2: PDF Audit */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08 }}
        className="glass p-6 rounded-2xl group hover:border-violet-500/20 transition-all border border-white/[0.06]"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center">
            <FileText className="w-5 h-5 text-violet-400" />
          </div>
          <div>
            <h3 className="text-white font-bold text-sm">Scientific Audit Report</h3>
            <p className="text-white/40 text-xs">OECD compliance PDF</p>
          </div>
        </div>
        <p className="text-xs text-white/40 mb-4 leading-relaxed">
          Comprehensive PDF documenting OECD curation compliance, Unit-Endpoint anomalies, and biological variance auditing.
        </p>
        <a
          href={downloadPdfUrl}
          download
          className="flex items-center justify-between w-full px-4 py-2.5 rounded-xl
            bg-white/[0.04] text-white text-xs font-semibold
            hover:bg-violet-500/10 hover:text-violet-400 transition-colors"
        >
          Download PDF Report <ArrowRight className="w-4 h-4" />
        </a>
      </motion.div>

      {/* Reset */}
      <div className="pt-2 flex justify-center">
        <button
          onClick={handleResetWorkspace}
          className="flex items-center gap-2 px-5 py-2.5 rounded-full text-white/30
            hover:text-white hover:bg-white/[0.04] text-xs font-medium transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Reset Workspace Environment
        </button>
      </div>
    </div>
  );
};
