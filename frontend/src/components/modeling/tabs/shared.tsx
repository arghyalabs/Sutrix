/**
 * Shared components used by all readiness tabs.
 * RunButton, ProgressBar, SectionEmptyState, StatPill, StatusBadge
 */
import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw, FlaskConical, Maximize2, Minimize2, Download } from 'lucide-react';
import { toPng } from 'html-to-image';
import toast from 'react-hot-toast';

// ── Run Button ────────────────────────────────────────────────────────────────
interface RunButtonProps {
  label: string;
  isRunning: boolean;
  progress?: number;
  phase?: string;
  onClick: () => void;
  className?: string;
}
export const RunButton: React.FC<RunButtonProps> = ({
  label, isRunning, progress = 0, phase = '', onClick, className = ''
}) => (
  <button
    onClick={onClick}
    disabled={isRunning}
    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all
      ${isRunning
        ? 'bg-white/[0.04] border border-white/[0.06] text-white/40 cursor-not-allowed'
        : 'bg-gradient-to-r from-cyan-500/20 to-violet-500/20 border border-cyan-500/30 text-cyan-400 hover:from-cyan-500/30 hover:to-violet-500/30 cursor-pointer'
      } ${className}`}
  >
    <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
    {isRunning ? `${progress}% — ${phase || 'Running…'}` : label}
  </button>
);

// ── Progress Bar ──────────────────────────────────────────────────────────────
interface ProgressBarProps { progress: number; phase: string }
export const ProgressBar: React.FC<ProgressBarProps> = ({ progress, phase }) => (
  <div className="space-y-1.5">
    <div className="flex justify-between text-[10px] text-white/30">
      <span>{phase}</span>
      <span>{progress}%</span>
    </div>
    <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden">
      <motion.div
        className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500"
        style={{ width: `${progress}%` }}
        transition={{ duration: 0.4 }}
      />
    </div>
  </div>
);

// ── Empty State ───────────────────────────────────────────────────────────────
interface EmptyStateProps { label: string; onRun: () => void }
export const SectionEmptyState: React.FC<EmptyStateProps> = ({ label, onRun }) => (
  <div className="flex flex-col items-center justify-center py-20 text-center">
    <div className="w-14 h-14 rounded-2xl bg-white/[0.02] border border-white/[0.05] flex items-center justify-center mb-4">
      <FlaskConical className="w-6 h-6 text-white/15" />
    </div>
    <p className="text-sm text-white/30 mb-1">No {label} results yet</p>
    <p className="text-xs text-white/20 mb-4">Run the analysis to generate results</p>
    <RunButton label={`Run ${label}`} isRunning={false} onClick={onRun} />
  </div>
);

// ── Error Banner ──────────────────────────────────────────────────────────────
export const ErrorBanner: React.FC<{ error: string }> = ({ error }) => (
  <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-xs text-rose-400">
    ⚠ {error}
  </div>
);

// ── Status Badge ──────────────────────────────────────────────────────────────
export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, string> = {
    PASS: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    WARN: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    FAIL: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    GOOD: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    PARTIAL: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    MISSING: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    DROP: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    REVIEW: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    KEEP: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    SAFE: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    HIGH: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    MEDIUM: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    LOW: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    CRITICAL: 'bg-red-600/10 text-red-400 border-red-600/20',
    INSIDE: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    BORDERLINE: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    OUTSIDE: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  };
  const cls = map[status] || 'bg-white/[0.04] text-white/40 border-white/[0.06]';
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium border ${cls}`}>
      {status}
    </span>
  );
};

// ── Stat Pill ─────────────────────────────────────────────────────────────────
export const StatPill: React.FC<{
  label: string; value: string | number; color?: string
}> = ({ label, value, color = 'text-white/70' }) => (
  <div className="flex flex-col items-center px-4 py-3 rounded-xl bg-white/[0.02] border border-white/[0.05]">
    <span className={`text-base font-bold ${color}`}>{value}</span>
    <span className="text-[10px] text-white/30 mt-0.5">{label}</span>
  </div>
);

// ── Glass Card ────────────────────────────────────────────────────────────────
interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children, className = '', title = 'Dataset Diagnostics'
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const expandedCardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  const handleDownloadPng = async () => {
    const el = expandedCardRef.current;
    if (!el) return;

    const filter = (node: Element) =>
      !(node instanceof HTMLElement && node.dataset.downloadIgnore === 'true');

    try {
      const toastId = toast.loading('Exporting high-resolution PNG...');
      await toPng(el, { pixelRatio: 2, cacheBust: true, filter });
      const dataUrl = await toPng(el, { pixelRatio: 2, cacheBust: true, filter });

      const a = document.createElement('a');
      a.download = `sdo_diagnostic_${title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.png`;
      a.href = dataUrl;
      a.click();
      toast.success('PNG exported successfully!', { id: toastId });
    } catch (err) {
      console.error('PNG export failed:', err);
      toast.error('PNG export failed.');
    }
  };

  // Recursively inspect and clone children to boost chart font size & readability in fullscreen
  const enhanceChildrenForFullscreen = (nodes: React.ReactNode): React.ReactNode => {
    return React.Children.map(nodes, child => {
      if (!React.isValidElement(child)) return child;
      
      const childProps = child.props as any;
      
      // If it's a Recharts container/chart, override layout styling or height
      if (child.type && (child.type as any).displayName && (child.type as any).displayName.includes('Container')) {
        return React.cloneElement(child as React.ReactElement<any>, {
          height: '100%',
          children: enhanceChildrenForFullscreen(childProps.children),
        });
      }
      
      if (child.type && (child.type as any).displayName && (
        (child.type as any).displayName.includes('Chart') || 
        (child.type as any).displayName.includes('Area') || 
        (child.type as any).displayName.includes('Bar')
      )) {
        return React.cloneElement(child as React.ReactElement<any>, {
          children: enhanceChildrenForFullscreen(childProps.children),
        });
      }

      // If it's an Axis, increase tick size
      if (child.type && (child.type as any).displayName && (
        (child.type as any).displayName.includes('XAxis') ||
        (child.type as any).displayName.includes('YAxis')
      )) {
        return React.cloneElement(child as React.ReactElement<any>, {
          tick: {
            fill: 'rgba(255,255,255,0.6)',
            fontSize: 12,
          },
        });
      }

      // If it has children, recurse
      if (childProps && childProps.children) {
        return React.cloneElement(child as React.ReactElement<any>, {
          children: enhanceChildrenForFullscreen(childProps.children),
        });
      }

      return child;
    });
  };

  return (
    <>
      <div className={`group/card relative rounded-2xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-xl transition-all duration-200 hover:border-white/[0.08] ${className}`}>
        {/* Maximize hover button */}
        <button
          onClick={() => setIsFullscreen(true)}
          className="absolute top-3 right-3 p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.06] text-white/20 group-hover/card:text-white/60 group-hover/card:bg-white/[0.06] hover:!text-white hover:!bg-white/[0.1] transition-all z-10 opacity-0 group-hover/card:opacity-100"
          title="Maximize Visual"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        {children}
      </div>

      <AnimatePresence>
        {isFullscreen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-6 md:p-10">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsFullscreen(false)}
              className="absolute inset-0 bg-black/90 backdrop-blur-md"
            />

            {/* Fullscreen Expanded Content */}
            <motion.div
              ref={expandedCardRef}
              initial={{ opacity: 0, scale: 0.96, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 15 }}
              className="relative w-full max-w-6xl h-[85vh] rounded-3xl border border-white/[0.08] bg-[#0c1224] p-6 md:p-8 shadow-2xl flex flex-col overflow-hidden z-10"
            >
              {/* Decorative glows */}
              <div className="absolute -top-12 -left-12 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute -bottom-12 -right-12 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />

              {/* Pinned Header */}
              <div className="flex justify-between items-center shrink-0 border-b border-white/[0.06] pb-4 mb-6">
                <div>
                  <h3 className="text-xl font-bold text-white bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
                    {title}
                  </h3>
                  <p className="text-xs text-white/30 mt-1">High-Resolution Diagnostic Analysis View</p>
                </div>
                
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleDownloadPng}
                    data-download-ignore="true"
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 hover:bg-cyan-500/20 text-xs font-bold uppercase tracking-wider transition-all"
                    title="Download PNG Image"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download PNG
                  </button>
                  <span className="text-[10px] text-white/40 uppercase tracking-widest bg-white/[0.03] border border-white/[0.06] px-2.5 py-1 rounded-full">Interactive Overlay</span>
                  <button
                    onClick={() => setIsFullscreen(false)}
                    data-download-ignore="true"
                    className="p-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-white/40 hover:text-white hover:bg-white/[0.06] transition-all"
                    title="Close"
                  >
                    <Minimize2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Children (Chart container scaled up) */}
              <div className="flex-1 min-h-0 w-full flex flex-col justify-center relative p-2 select-none h-full max-h-[60vh]">
                {enhanceChildrenForFullscreen(children)}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

// ── Section header ────────────────────────────────────────────────────────────
export const TabHeader: React.FC<{
  title: string; subtitle?: string; children?: React.ReactNode
}> = ({ title, subtitle, children }) => (
  <div className="flex items-start justify-between mb-4">
    <div>
      <h2 className="text-sm font-semibold text-white/80">{title}</h2>
      {subtitle && <p className="text-xs text-white/30 mt-0.5">{subtitle}</p>}
    </div>
    {children}
  </div>
);
