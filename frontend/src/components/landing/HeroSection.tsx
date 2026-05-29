import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ChevronRight, Activity, Network, Zap, GitBranch, Database, ShieldCheck } from 'lucide-react';
import { LogoLoader } from '../ui/SUTRIXLogo';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';

interface HeroSectionProps {
  onLaunch: () => void;
}

const SCIENTIFIC_CAPABILITIES = [
  'SMILES Canonicalization',
  'Descriptor Enrichment',
  'Hierarchy Segregation',
  'QSAR Readiness',
  'AI Optimization'
];

export const HeroSection: React.FC<HeroSectionProps> = ({ onLaunch }) => {
  const hasActiveSession = useWorkspaceStore(state => !!state.filename);

  return (
    <section className="relative min-h-[92vh] flex flex-col w-full bg-[#03060d] overflow-hidden font-sans">
      
      {/* ── 1. Premium Animated Background Depth ── */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden flex items-center justify-center">
        {/* Deep background mesh gradients */}
        <motion.div
          animate={{ opacity: [0.12, 0.2, 0.12], scale: [1, 1.05, 1] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-[-10%] right-[10%] w-[50vw] h-[50vw] rounded-full bg-cyan-500/[0.05] blur-[100px]"
        />
        <motion.div
          animate={{ opacity: [0.08, 0.15, 0.08], scale: [1, 1.05, 1] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
          className="absolute bottom-[-10%] left-[5%] w-[40vw] h-[40vw] rounded-full bg-violet-500/[0.05] blur-[120px]"
        />
        
        {/* Subtle grid and scanning lines */}
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTAgNDBoNDBWMEgwem0zOS0zOUgxVjM5aDM4eiIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjAxNSkiIGZpbGwtcnVsZT0iZXZlbm9kZCIvPjwvc3ZnPg==')] opacity-40" />
        <motion.div
          animate={{ y: ['-100%', '200%'], opacity: [0, 0.5, 0] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
          className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-white/10 to-transparent blur-[1px]"
        />
      </div>

      {/* ── Navbar ── */}
      <header className="absolute top-0 left-0 w-full px-6 py-5 lg:px-12 lg:py-6 z-40 flex items-center justify-between border-b border-white/[0.02] bg-[#03060d]/50 backdrop-blur-xl">
        <motion.div
          initial={{ opacity: 0, x: -16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          className="flex items-center gap-4"
        >
          <LogoLoader size="w-14 h-14" compact />
          <div className="flex flex-col leading-none pt-1">
            <span className="font-extrabold tracking-[0.2em] text-2xl text-white">SUTRIX</span>
            <span className="text-[10px] font-semibold tracking-[0.15em] text-white/50 uppercase mt-1">
              Scientific Data Engineering
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex items-center gap-8"
        >
          <a href="#workflow" className="text-xs font-semibold uppercase tracking-wider text-white/50 hover:text-white transition-colors">Documentation</a>
          <button className="text-xs font-semibold uppercase tracking-wider text-white/50 hover:text-white transition-colors flex items-center gap-1.5">
            Sign In <ArrowRight className="w-3 h-3" />
          </button>
        </motion.div>
      </header>

      {/* ── Main Content (45/55 Split) ── */}
      <div className="relative z-10 flex-1 flex flex-col lg:flex-row items-center justify-between px-6 lg:px-24 w-full max-w-[1800px] mx-auto pt-32 lg:pt-28 pb-12">
        
        {/* ── Left Side: Typography (45%) ── */}
        <div className="w-full lg:w-[45%] flex flex-col justify-center space-y-7 order-2 lg:order-1 pt-8 lg:pt-0 pb-8 lg:pb-0">
          
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/10 self-start mb-2"
          >
            <span className="relative flex h-1.5 w-1.5 items-center justify-center">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-60"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-white"></span>
            </span>
            <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-white/80">
              AI-Native Intelligence Engine
            </span>
          </motion.div>
          
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-5xl lg:text-[4.5rem] font-bold text-white leading-[1.05] tracking-tight"
          >
            AI-Ready Scientific<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-gray-300 via-gray-100 to-gray-400">
              Data Engineering
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-lg lg:text-[1.2rem] text-white/50 leading-relaxed max-w-lg font-medium tracking-wide"
          >
            Curate, standardize, enrich, and optimize scientific datasets for predictive modeling workflows.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="pt-6 flex flex-wrap items-center gap-5"
          >
            {/* Standardized Primary Button */}
            <button
              onClick={onLaunch}
              className="group relative flex items-center gap-3 px-8 py-3.5 rounded-lg bg-white text-black font-semibold text-sm transition-all hover:-translate-y-0.5 active:translate-y-0 shadow-[0_4px_14px_rgba(255,255,255,0.15)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.25)]"
            >
              {hasActiveSession ? 'Continue Workflow' : 'Enter Workspace'}
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
            
            {/* Standardized Secondary Button */}
            <a
              href="#workflow"
              className="group flex items-center gap-2 px-7 py-3.5 rounded-lg bg-white/[0.03] border border-white/10 text-sm font-semibold text-white/70 transition-all hover:-translate-y-0.5 hover:bg-white/[0.06] hover:text-white"
            >
              View Workflow
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform text-white/50 group-hover:text-white/80" />
            </a>
          </motion.div>
        </div>

        {/* ── Right Side: Scientific Intelligence Visualization (55%) ── */}
        <div className="w-full lg:w-[55%] h-[500px] lg:h-[700px] flex items-center justify-center order-1 lg:order-2 relative">
          <div className="relative w-full max-w-[650px] aspect-square flex items-center justify-center">
            
            {/* 1. Subtle glowing connection lines (SVG) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="lineGradWhite" x1="50%" y1="50%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="rgba(34,211,238,0.4)" />
                  <stop offset="100%" stopColor="rgba(34,211,238,0.0)" />
                </linearGradient>
                <linearGradient id="lineGradWhite2" x1="50%" y1="50%" x2="0%" y2="0%">
                  <stop offset="0%" stopColor="rgba(139,92,246,0.4)" />
                  <stop offset="100%" stopColor="rgba(139,92,246,0.0)" />
                </linearGradient>
                <linearGradient id="lineGradTop" gradientUnits="userSpaceOnUse" x1="50" y1="50" x2="50" y2="15">
                  <stop offset="0%" stopColor="rgba(34,211,238,0.4)" />
                  <stop offset="100%" stopColor="rgba(34,211,238,0.0)" />
                </linearGradient>
              </defs>
              
              {/* Connector Lines to the 5 nodes */}
              <motion.path d="M 50 50 L 50 15" stroke="url(#lineGradTop)" strokeWidth="0.5" strokeDasharray="2,2" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5, delay: 0.6 }} />
              <motion.path d="M 50 50 L 90 40" stroke="url(#lineGradWhite)" strokeWidth="0.5" strokeDasharray="2,2" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5, delay: 0.7 }} />
              <motion.path d="M 50 50 L 75 85" stroke="url(#lineGradWhite)" strokeWidth="0.5" strokeDasharray="2,2" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5, delay: 0.8 }} />
              <motion.path d="M 50 50 L 25 85" stroke="url(#lineGradWhite2)" strokeWidth="0.5" strokeDasharray="2,2" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5, delay: 0.9 }} />
              <motion.path d="M 50 50 L 10 40" stroke="url(#lineGradWhite2)" strokeWidth="0.5" strokeDasharray="2,2" fill="none" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5, delay: 1.0 }} />
              
              {/* Animated data particles flowing along paths */}
              <motion.circle r="1" fill="#22d3ee" animate={{ cx: [50, 50], cy: [50, 15], opacity: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'linear', delay: 0 }} />
              <motion.circle r="1" fill="#22d3ee" animate={{ cx: [50, 90], cy: [50, 40], opacity: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'linear', delay: 1 }} />
              <motion.circle r="1" fill="#22d3ee" animate={{ cx: [50, 75], cy: [50, 85], opacity: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'linear', delay: 0.5 }} />
              <motion.circle r="1" fill="#8b5cf6" animate={{ cx: [50, 25], cy: [50, 85], opacity: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'linear', delay: 1.5 }} />
              <motion.circle r="1" fill="#8b5cf6" animate={{ cx: [50, 10], cy: [50, 40], opacity: [0, 1, 0] }} transition={{ duration: 3, repeat: Infinity, ease: 'linear', delay: 2 }} />
            </svg>

            {/* 2. Central Intelligence Core */}
            <motion.div 
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", duration: 1.2, delay: 0.4 }}
              className="absolute inset-[43%] rounded-full bg-cyan-500/5 border border-cyan-500/20 shadow-[0_0_40px_rgba(34,211,238,0.15)] flex items-center justify-center z-10 backdrop-blur-md"
            >
              <motion.div animate={{ opacity: [0.6, 1, 0.6] }} transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}>
                <Activity className="w-8 h-8 text-cyan-400" />
              </motion.div>
              {/* Soft pulse rings */}
              <motion.div animate={{ scale: [1, 1.8], opacity: [0.4, 0] }} transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }} className="absolute inset-0 rounded-full border border-cyan-500/30" />
            </motion.div>

            {/* 3. Floating Process Cards (5) */}
            
            {/* Card 1: Top (Canonicalized) */}
            <motion.div
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.6 }}
              className="absolute top-[8%] left-1/2 -translate-x-1/2 z-20 group"
            >
              <motion.div animate={{ y: [-4, 4, -4] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }} className="p-3 rounded-lg bg-[#080d1e]/90 backdrop-blur-md border border-cyan-500/20 hover:border-cyan-500/40 transition-colors shadow-2xl flex items-center gap-3 w-44 cursor-default">
                <div className="w-7 h-7 rounded-md bg-cyan-500/10 flex items-center justify-center">
                  <Network className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div>
                  <p className="text-[7px] font-bold uppercase tracking-widest text-cyan-400/50">Structure</p>
                  <p className="text-[11px] font-semibold text-white/90">Canonicalized</p>
                </div>
              </motion.div>
            </motion.div>

            {/* Card 2: Top Right (Descriptor Enriched) */}
            <motion.div
              initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.7 }}
              className="absolute top-[33%] right-[0%] z-20 group"
            >
              <motion.div animate={{ y: [4, -4, 4] }} transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut', delay: 1 }} className="p-3 rounded-lg bg-[#080d1e]/90 backdrop-blur-md border border-violet-500/20 hover:border-violet-500/40 transition-colors shadow-2xl flex items-center gap-3 w-44 cursor-default">
                <div className="w-7 h-7 rounded-md bg-violet-500/10 flex items-center justify-center">
                  <Database className="w-3.5 h-3.5 text-violet-400" />
                </div>
                <div>
                  <p className="text-[7px] font-bold uppercase tracking-widest text-violet-400/50">Matrix</p>
                  <p className="text-[11px] font-semibold text-white/90">Descriptor Enriched</p>
                </div>
              </motion.div>
            </motion.div>

            {/* Card 3: Bottom Right (Hierarchy Organized) */}
            <motion.div
              initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.8 }}
              className="absolute bottom-[10%] right-[10%] z-20 group"
            >
              <motion.div animate={{ y: [-3, 3, -3] }} transition={{ duration: 5.5, repeat: Infinity, ease: 'easeInOut', delay: 2 }} className="p-3 rounded-lg bg-[#080d1e]/90 backdrop-blur-md border border-cyan-500/20 hover:border-cyan-500/40 transition-colors shadow-2xl flex items-center gap-3 w-44 cursor-default">
                <div className="w-7 h-7 rounded-md bg-cyan-500/10 flex items-center justify-center">
                  <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div>
                  <p className="text-[7px] font-bold uppercase tracking-widest text-cyan-400/50">Architecture</p>
                  <p className="text-[11px] font-semibold text-white/90">Hierarchy Organized</p>
                </div>
              </motion.div>
            </motion.div>

            {/* Card 4: Bottom Left (QSAR Ready) */}
            <motion.div
              initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 0.9 }}
              className="absolute bottom-[10%] left-[10%] z-20 group"
            >
              <motion.div animate={{ y: [3, -3, 3] }} transition={{ duration: 6.5, repeat: Infinity, ease: 'easeInOut', delay: 1.5 }} className="p-3 rounded-lg bg-[#080d1e]/90 backdrop-blur-md border border-emerald-500/20 hover:border-emerald-500/40 transition-colors shadow-2xl flex items-center gap-3 w-44 cursor-default">
                <div className="w-7 h-7 rounded-md bg-emerald-500/10 flex items-center justify-center">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-[7px] font-bold uppercase tracking-widest text-emerald-400/50">Validation</p>
                  <p className="text-[11px] font-semibold text-white/90">QSAR Ready</p>
                </div>
              </motion.div>
            </motion.div>

            {/* Card 5: Top Left (AI Optimized) */}
            <motion.div
              initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.8, delay: 1.0 }}
              className="absolute top-[33%] left-[0%] z-20 group"
            >
              <motion.div animate={{ y: [-4, 4, -4] }} transition={{ duration: 5.2, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }} className="p-3 rounded-lg bg-[#080d1e]/90 backdrop-blur-md border border-violet-500/20 hover:border-violet-500/40 transition-colors shadow-2xl flex items-center gap-3 w-44 cursor-default">
                <div className="w-7 h-7 rounded-md bg-violet-500/10 flex items-center justify-center">
                  <Zap className="w-3.5 h-3.5 text-violet-400" />
                </div>
                <div>
                  <p className="text-[7px] font-bold uppercase tracking-widest text-violet-400/50">Optimization</p>
                  <p className="text-[11px] font-semibold text-white/90">AI Optimized</p>
                </div>
              </motion.div>
            </motion.div>

          </div>
        </div>
      </div>

      {/* ── Scientific Workflow Indicators (Bottom Edge) ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.8 }}
        className="relative z-20 w-full border-t border-white/[0.04] bg-[#03060d]/80 backdrop-blur-md py-4 mt-auto hidden lg:flex justify-center shadow-[0_-10px_40px_rgba(0,0,0,0.5)]"
      >
        <div className="flex items-center gap-6 text-[10px] font-bold uppercase tracking-widest text-white/30">
          {SCIENTIFIC_CAPABILITIES.map((cap, i) => (
            <React.Fragment key={cap}>
              <span className="hover:text-white/70 transition-colors cursor-default">{cap}</span>
              {i < SCIENTIFIC_CAPABILITIES.length - 1 && <span className="w-1.5 h-1.5 rounded-full bg-white/10" />}
            </React.Fragment>
          ))}
        </div>
      </motion.div>
    </section>
  );
};
