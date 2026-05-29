import React, { useEffect, useRef, useState } from 'react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import { ArrowRight, ChevronDown, Upload, GitBranch, Zap, BarChart3, CheckCircle, Download } from 'lucide-react';
import { SUTRIXLogo } from '../ui/SUTRIXLogo';

interface HeroSectionProps {
  onLaunch: () => void;
}

// Animated molecule dot grid (pure CSS, GPU optimized)
const DotGrid: React.FC = () => (
  <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <pattern id="hero-grid" width="36" height="36" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="1" fill="#22d3ee" opacity="0.15" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#hero-grid)" />
  </svg>
);

// Animated pipeline node for hero right side
const PipelineNode: React.FC<{
  icon: React.ReactNode;
  label: string;
  color: string;
  delay: number;
  active?: boolean;
}> = ({ icon, label, color, delay, active }) => (
  <motion.div
    initial={{ opacity: 0, x: 30 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay, duration: 0.6, ease: 'easeOut' }}
    className="flex items-center gap-3"
  >
    <motion.div
      animate={active ? { scale: [1, 1.08, 1], boxShadow: [`0 0 0px ${color}`, `0 0 16px ${color}`, `0 0 0px ${color}`] } : {}}
      transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
      className="w-10 h-10 rounded-xl flex items-center justify-center border border-white/[0.08] bg-white/[0.04] shrink-0"
    >
      {icon}
    </motion.div>
    <div>
      <p className="text-xs font-semibold text-white/80">{label}</p>
    </div>
  </motion.div>
);

// Animated connection line between nodes
const ConnectorLine: React.FC<{ delay: number }> = ({ delay }) => (
  <motion.div
    initial={{ scaleY: 0 }}
    animate={{ scaleY: 1 }}
    transition={{ delay, duration: 0.4, ease: 'easeOut' }}
    style={{ transformOrigin: 'top' }}
    className="w-px h-6 bg-gradient-to-b from-white/[0.08] to-white/[0.02] ml-5"
  />
);

// Moving data packet animation
const DataPacket: React.FC<{ delay: number }> = ({ delay }) => (
  <motion.div
    initial={{ opacity: 0, y: 0 }}
    animate={{ opacity: [0, 1, 1, 0], y: [0, 0, 220, 220] }}
    transition={{ delay, duration: 3.5, repeat: Infinity, ease: 'linear', times: [0, 0.05, 0.95, 1] }}
    className="absolute left-[18px] w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_#22d3ee]"
  />
);

const pipelineSteps = [
  { icon: <Upload className="w-4 h-4 text-emerald-400" />, label: 'Dataset Ingestion', color: 'rgba(52,211,153,0.4)' },
  { icon: <GitBranch className="w-4 h-4 text-cyan-400" />, label: 'Variable Mapping', color: 'rgba(34,211,238,0.4)' },
  { icon: <BarChart3 className="w-4 h-4 text-violet-400" />, label: 'Hierarchy Builder', color: 'rgba(167,139,250,0.4)' },
  { icon: <Zap className="w-4 h-4 text-amber-400" />, label: 'Descriptor Enrichment', color: 'rgba(251,191,36,0.4)' },
  { icon: <CheckCircle className="w-4 h-4 text-pink-400" />, label: 'AI Readiness Audit', color: 'rgba(244,114,182,0.4)' },
  { icon: <Download className="w-4 h-4 text-teal-400" />, label: 'Export Engine', color: 'rgba(45,212,191,0.4)' },
];

export const HeroSection: React.FC<HeroSectionProps> = ({ onLaunch }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 30, damping: 25 });
  const springY = useSpring(mouseY, { stiffness: 30, damping: 25 });

  const orbX = useTransform(springX, v => v * 0.4);
  const orbY = useTransform(springY, v => v * 0.4);

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseX.set((e.clientX - cx) / cx * 40);
      mouseY.set((e.clientY - cy) / cy * 40);
    };
    window.addEventListener('mousemove', handleMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMove);
  }, [mouseX, mouseY]);

  const [activeNode, setActiveNode] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setActiveNode(v => (v + 1) % pipelineSteps.length), 1800);
    return () => clearInterval(t);
  }, []);

  return (
    <section ref={containerRef} className="relative min-h-screen flex flex-col overflow-hidden bg-[#03070f]">
      {/* Background layers */}
      <div className="absolute inset-0 pointer-events-none">
        <DotGrid />
        <motion.div
          style={{ x: orbX, y: orbY }}
          className="absolute top-[-20%] left-[-15%] w-[60%] h-[60%] rounded-full bg-cyan-500/[0.06] blur-[120px]"
        />
        <motion.div
          style={{ x: useTransform(orbX, v => -v * 0.5), y: useTransform(orbY, v => -v * 0.5) }}
          className="absolute bottom-[-20%] right-[-15%] w-[55%] h-[55%] rounded-full bg-violet-500/[0.05] blur-[120px]"
        />
      </div>

      {/* Navbar */}
      <nav className="relative z-20 flex items-center justify-between px-8 py-5 max-w-7xl mx-auto w-full">
        <div className="flex items-center gap-3">
          <SUTRIXLogo className="w-9 h-9" />
          <span className="font-extrabold tracking-widest text-base text-white/90">SUTRIX</span>
        </div>
        <div className="hidden md:flex items-center gap-8 text-sm text-white/40 font-medium">
          <a href="#workflow" className="hover:text-white/70 transition-colors">Workflow</a>
          <a href="#features" className="hover:text-white/70 transition-colors">Features</a>
          <a href="#hierarchy" className="hover:text-white/70 transition-colors">Engine</a>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onLaunch}
          className="px-5 py-2 rounded-full bg-white/[0.08] border border-white/[0.12] text-white text-sm font-semibold hover:bg-white/[0.14] transition-colors"
        >
          Enter Workspace
        </motion.button>
      </nav>

      {/* Main hero content */}
      <div className="relative z-10 flex-1 flex items-center">
        <div className="max-w-7xl mx-auto px-8 w-full grid lg:grid-cols-2 gap-16 items-center py-16">

          {/* LEFT: Text content */}
          <div className="space-y-8">
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-cyan-500/[0.08] border border-cyan-500/20 text-xs font-semibold text-cyan-400"
            >
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-400" />
              </span>
              SDO Engine — Computational Toxicology Platform
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.1 }}
              className="text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.08] text-white"
            >
              AI-Native Scientific
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-violet-400 to-cyan-400 bg-[length:200%_auto] animate-[shimmer_4s_linear_infinite]">
                Data Engineering
              </span>
              <br />
              for Toxicology
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="text-lg text-white/50 leading-relaxed max-w-xl"
            >
              Transform messy ecotoxicology datasets into AI-ready scientific intelligence pipelines with
              hierarchical preprocessing, descriptor enrichment, and predictive modeling readiness analysis.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.3 }}
              className="flex flex-wrap items-center gap-4"
            >
              <motion.button
                whileHover={{ scale: 1.02, boxShadow: '0 0 32px rgba(34,211,238,0.35)' }}
                whileTap={{ scale: 0.98 }}
                onClick={onLaunch}
                className="group flex items-center gap-2 px-7 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-cyan-600 text-[#03070f] font-bold text-sm shadow-[0_0_24px_rgba(34,211,238,0.25)] transition-all"
              >
                Start Workspace
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </motion.button>
              <a
                href="#workflow"
                className="flex items-center gap-2 px-7 py-3.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white/70 font-semibold text-sm hover:bg-white/[0.07] hover:text-white transition-all"
              >
                View Workflow
                <ChevronDown className="w-4 h-4" />
              </a>
            </motion.div>

            {/* Stats row */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="flex flex-wrap gap-8 pt-2"
            >
              {[
                { val: '100k+', label: 'Compounds' },
                { val: '2,043', label: 'Descriptors' },
                { val: '8-Step', label: 'Pipeline' },
                { val: 'QSAR', label: 'Ready' },
              ].map((s) => (
                <div key={s.label}>
                  <div className="text-2xl font-extrabold text-white">{s.val}</div>
                  <div className="text-xs text-white/30 font-medium uppercase tracking-widest mt-0.5">{s.label}</div>
                </div>
              ))}
            </motion.div>
          </div>

          {/* RIGHT: Animated pipeline visualization */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="hidden lg:flex justify-center"
          >
            <div className="relative w-72">
              {/* Vertical line track */}
              <div className="absolute left-5 top-5 bottom-5 w-px bg-gradient-to-b from-white/[0.06] via-cyan-500/20 to-white/[0.06]" />

              {/* Moving data packets */}
              {[0, 1.2, 2.4].map((d, i) => <DataPacket key={i} delay={d} />)}

              <div className="space-y-1">
                {pipelineSteps.map((step, idx) => (
                  <React.Fragment key={step.label}>
                    <PipelineNode
                      icon={step.icon}
                      label={step.label}
                      color={step.color}
                      delay={0.1 + idx * 0.1}
                      active={activeNode === idx}
                    />
                    {idx < pipelineSteps.length - 1 && <ConnectorLine delay={0.15 + idx * 0.1} />}
                  </React.Fragment>
                ))}
              </div>

              {/* Status panel */}
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 1.2 }}
                className="mt-6 p-4 rounded-2xl bg-white/[0.03] border border-white/[0.06] backdrop-blur-sm"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-white/30">Live Pipeline</span>
                  <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-semibold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Active
                  </span>
                </div>
                <div className="space-y-2">
                  {['Species filtering', 'Endpoint grouping', 'SMILES resolution'].map((task, i) => (
                    <div key={task} className="flex items-center gap-2">
                      <motion.div
                        animate={{ width: ['20%', '100%'] }}
                        transition={{ delay: 1.4 + i * 0.3, duration: 1.5, ease: 'easeOut' }}
                        className="h-1 rounded-full bg-gradient-to-r from-cyan-500/40 to-violet-500/40"
                        style={{ width: '100%' }}
                      />
                      <span className="text-[9px] text-white/20 shrink-0">{task}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.5 }}
        className="relative z-10 flex justify-center pb-8"
      >
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          className="flex flex-col items-center gap-2 text-white/20"
        >
          <span className="text-[10px] uppercase tracking-widest font-medium">Scroll to explore</span>
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </motion.div>
    </section>
  );
};
