import React, { useState, useEffect, useRef } from 'react';
import { motion, useMotionValue, useSpring, AnimatePresence } from 'framer-motion';
import { 
  ArrowRight, Upload, Map, Zap, CheckCircle, LineChart, Download, 
  Layers, Shield, Cpu, Box, Network, Database, FlaskConical, Activity
} from 'lucide-react';
import { SturixLogo } from '../ui/SturixLogo';

interface LandingPageProps {
  onLaunch: () => void;
}

const workflowSteps = [
  { icon: <Upload className="w-5 h-5" />, label: 'Ingest', desc: 'Secure snappy ingestion with auto-schema detection', color: 'from-emerald-400 to-emerald-600' },
  { icon: <Map className="w-5 h-5" />, label: 'Map', desc: 'AI-powered binding of toxicological primitives', color: 'from-cyan-400 to-cyan-600' },
  { icon: <Network className="w-5 h-5" />, label: 'Segregate', desc: 'Build a DAG hierarchy of your compound space', color: 'from-violet-400 to-violet-600' },
  { icon: <Database className="w-5 h-5" />, label: 'Analyze', desc: 'Interactive node-level statistical exploration', color: 'from-blue-400 to-blue-600' },
  { icon: <Zap className="w-5 h-5" />, label: 'Enrich', desc: 'Multi-core descriptor calculation engine', color: 'from-amber-400 to-amber-600' },
  { icon: <CheckCircle className="w-5 h-5" />, label: 'Audit', desc: 'OECD compliance & multicollinearity checks', color: 'from-pink-400 to-pink-600' },
  { icon: <LineChart className="w-5 h-5" />, label: 'Visualize', desc: '3D WebGL PCA and chemical space mapping', color: 'from-rose-400 to-rose-600' },
  { icon: <Download className="w-5 h-5" />, label: 'Export', desc: 'Model-ready Parquet, SDF, XLSX, Feather', color: 'from-teal-400 to-teal-600' },
];

const features = [
  { icon: <Layers className="w-6 h-6 text-cyan-400" />, title: 'High-Dimensional Pipeline', desc: 'Process 100k+ compounds with 2,000+ descriptors without dropping a single frame.' },
  { icon: <Cpu className="w-6 h-6 text-violet-400" />, title: 'Parallel Execution Engine', desc: 'Leverages pure multiprocess background workers to bypass GIL locks completely.' },
  { icon: <Shield className="w-6 h-6 text-emerald-400" />, title: 'OECD Readiness Audits', desc: 'Automatic feature multicollinearity and Bemis-Murcko scaffold density scoring.' },
  { icon: <Box className="w-6 h-6 text-amber-400" />, title: 'Zero-Latency Caching', desc: 'Persistent SQLite WAL topology cache with 90%+ hit rates on recurring molecules.' },
  { icon: <Network className="w-6 h-6 text-blue-400" />, title: 'DAG Hierarchy Builder', desc: 'Interactive visual DAG for compound segregation with real-time job telemetry.' },
  { icon: <FlaskConical className="w-6 h-6 text-pink-400" />, title: 'Scientific Provenance', desc: 'Full filter lineage tracking with path notation and inherited filter history.' },
];

// Live telemetry counter (fake animated)
const LiveTelemetry: React.FC = () => {
  const [count, setCount] = useState(1847);
  useEffect(() => {
    const t = setInterval(() => {
      setCount(v => v + Math.floor(Math.random() * 3));
    }, 4500);
    return () => clearInterval(t);
  }, []);
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.5 }}
      className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-medium"
    >
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
      </span>
      <span className="text-emerald-400 font-bold">Live</span>
      <span className="text-white/40">—</span>
      <AnimatePresence mode="wait">
        <motion.span
          key={count}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          className="text-white font-semibold"
        >
          {count.toLocaleString()}
        </motion.span>
      </AnimatePresence>
      <span className="text-white/40">datasets processed today</span>
    </motion.div>
  );
};

// Molecular dot grid SVG background
const MolecularDotGrid: React.FC = () => (
  <svg
    className="absolute inset-0 w-full h-full opacity-[0.03] pointer-events-none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <pattern id="mol-grid" width="32" height="32" patternUnits="userSpaceOnUse">
        <circle cx="1" cy="1" r="1" fill="#22d3ee" />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#mol-grid)" />
  </svg>
);

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunch }) => {
  const [activeStep, setActiveStep] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Mouse parallax for orbs
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 40, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 40, damping: 20 });

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      const cx = window.innerWidth / 2;
      const cy = window.innerHeight / 2;
      mouseX.set((e.clientX - cx) / cx * 30);
      mouseY.set((e.clientY - cy) / cy * 30);
    };
    window.addEventListener('mousemove', handleMove);
    return () => window.removeEventListener('mousemove', handleMove);
  }, [mouseX, mouseY]);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % workflowSteps.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div ref={containerRef} className="min-h-screen bg-void text-primary font-sans overflow-x-hidden selection:bg-cyan-500/30">
      
      {/* Background: animated gradient orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <MolecularDotGrid />
        {/* Orb 1 - Cyan, top-left */}
        <motion.div
          style={{ x: springX, y: springY }}
          className="absolute top-[-15%] left-[-15%] w-[55%] h-[55%] bg-cyan-500/[0.07] rounded-full blur-[140px]"
          animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        {/* Orb 2 - Violet, bottom-right */}
        <motion.div
          style={{ x: springX, y: springY }}
          className="absolute bottom-[-15%] right-[-15%] w-[50%] h-[50%] bg-violet-500/[0.07] rounded-full blur-[140px]"
          animate={{ scale: [1, 1.1, 1], opacity: [0.6, 0.9, 0.6] }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        />
        {/* Orb 3 - Emerald, center-right */}
        <motion.div
          className="absolute top-[40%] right-[10%] w-[25%] h-[25%] bg-emerald-500/[0.04] rounded-full blur-[100px]"
          animate={{ scale: [1, 1.15, 1], opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 12, repeat: Infinity, ease: 'easeInOut', delay: 5 }}
        />
      </div>

      <div className="relative z-10">
        {/* Navigation */}
        <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto">
          <div className="flex items-center gap-3">
            <SturixLogo className="w-12 h-12" />
            <span className="font-extrabold tracking-widest text-xl bg-clip-text text-transparent bg-gradient-to-r from-white to-white/70">STURIX</span>
          </div>
          <button 
            onClick={onLaunch}
            className="px-5 py-2 rounded-full bg-white text-void font-medium text-sm hover:bg-gray-200 transition-colors"
          >
            Enter Workspace
          </button>
        </nav>

        {/* Hero Section */}
        <section className="pt-20 pb-28 px-6 max-w-5xl mx-auto text-center flex flex-col items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="space-y-6 flex flex-col items-center"
          >
            {/* SDO Engine badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs font-medium text-cyan-400 mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              SDO Engine v3.0 Live
            </div>

            {/* Live telemetry badge */}
            <LiveTelemetry />
            
            <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight leading-[1.1] text-transparent bg-clip-text bg-gradient-to-b from-white to-white/60">
              AI-Native Scientific <br className="hidden md:block" /> Data Intelligence
            </h1>
            
            <p className="text-lg md:text-xl text-secondary max-w-2xl mx-auto leading-relaxed font-medium">
              Transform raw compound datasets into AI-ready research pipelines. 
              The most powerful offline QSAR modeling workspace for biotech teams.
            </p>

            <div className="pt-6 flex items-center justify-center gap-4">
              <button 
                onClick={onLaunch}
                className="group relative px-8 py-4 rounded-xl bg-gradient-to-b from-cyan-400 to-cyan-500 text-void font-bold text-sm shadow-[0_0_30px_rgba(34,211,238,0.3)] hover:shadow-[0_0_40px_rgba(34,211,238,0.5)] transition-all overflow-hidden"
              >
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
                <span className="relative flex items-center gap-2">
                  Launch Workspace <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </span>
              </button>
              <button className="px-8 py-4 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white font-semibold text-sm hover:bg-white/[0.08] transition-colors">
                View Documentation
              </button>
            </div>
          </motion.div>
        </section>

        {/* Live Metrics Strip */}
        <section className="pb-28 px-6">
          <div className="max-w-4xl mx-auto flex flex-wrap justify-center gap-x-12 gap-y-6">
            {[
              { value: '100k+', label: 'Compounds' },
              { value: '2,043', label: 'Descriptors' },
              { value: '<3s', label: 'Fast Mode' },
              { value: 'WebGL', label: 'Rendering' },
              { value: '8-step', label: 'Pipeline' },
            ].map((m, i) => (
              <React.Fragment key={m.label}>
                {i > 0 && <div className="hidden md:block w-px h-12 bg-white/[0.06]" />}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex flex-col items-center"
                >
                  <span className="text-3xl font-bold text-white">{m.value}</span>
                  <span className="text-xs text-muted font-medium mt-1 uppercase tracking-wider">{m.label}</span>
                </motion.div>
              </React.Fragment>
            ))}
          </div>
        </section>

        {/* Interactive Workflow Timeline */}
        <section className="py-24 bg-surface/50 border-y border-white/[0.04] relative overflow-hidden">
          <MolecularDotGrid />
          <div className="max-w-6xl mx-auto px-6 relative z-10">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-center mb-16"
            >
              <h2 className="text-3xl font-bold text-white mb-4">An 8-Step Research Pipeline</h2>
              <p className="text-secondary">Fully automated and offline-first processing engine.</p>
            </motion.div>

            <div className="relative">
              {/* Connecting line */}
              <div className="absolute top-6 left-0 right-0 h-[2px] bg-white/[0.04] -z-10 hidden md:block" />
              
              <div className="grid grid-cols-2 md:grid-cols-8 gap-4">
                {workflowSteps.map((step, idx) => {
                  const isActive = idx === activeStep;
                  return (
                    <motion.div
                      key={step.label}
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ delay: idx * 0.07 }}
                      className="relative flex flex-col items-center text-center cursor-pointer group"
                      onMouseEnter={() => setActiveStep(idx)}
                    >
                      <motion.div
                        animate={isActive ? { scale: 1.12 } : { scale: 1 }}
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center mb-3 transition-all duration-300 relative overflow-hidden
                          ${isActive
                            ? `bg-gradient-to-br ${step.color} text-white shadow-[0_0_25px_rgba(34,211,238,0.4)]`
                            : 'glass text-secondary group-hover:text-white'
                          }`}
                      >
                        {isActive && (
                          <motion.div
                            className="absolute inset-0 bg-white/20"
                            animate={{ opacity: [0, 0.3, 0] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                          />
                        )}
                        {step.icon}
                      </motion.div>
                      
                      {/* Step number */}
                      <span className={`text-[9px] font-bold uppercase tracking-widest mb-1 ${isActive ? 'text-cyan-400' : 'text-white/20'}`}>
                        0{idx + 1}
                      </span>
                      
                      <h4 className={`text-xs font-bold mb-1 transition-colors ${isActive ? 'text-white' : 'text-secondary'}`}>
                        {step.label}
                      </h4>
                      
                      <AnimatePresence>
                        {isActive && (
                          <motion.p
                            initial={{ opacity: 0, y: 4, height: 0 }}
                            animate={{ opacity: 1, y: 0, height: 'auto' }}
                            exit={{ opacity: 0, y: -4, height: 0 }}
                            className="text-[10px] text-white/40 leading-relaxed"
                          >
                            {step.desc}
                          </motion.p>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Feature Grid */}
        <section className="py-28 px-6 max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl font-bold text-white mb-4">Built for Scientific Scale</h2>
            <p className="text-secondary">Every component engineered for toxicological data workflows.</p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                whileHover={{ y: -6, transition: { duration: 0.2 } }}
                className="glass p-7 rounded-3xl group border border-white/[0.04] hover:border-white/[0.1] transition-all
                  hover:shadow-[0_0_30px_rgba(34,211,238,0.05)] relative overflow-hidden"
              >
                {/* Hover glow */}
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/[0.03] to-violet-500/[0.03] opacity-0 group-hover:opacity-100 transition-opacity rounded-3xl" />
                <div className="relative z-10">
                  <div className="w-14 h-14 rounded-2xl bg-white/[0.03] flex items-center justify-center mb-5 border border-white/[0.06] group-hover:bg-white/[0.06] transition-colors">
                    {f.icon}
                  </div>
                  <h3 className="text-lg font-bold text-white mb-3">{f.title}</h3>
                  <p className="text-secondary text-sm leading-relaxed">{f.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </section>

        {/* Live Activity Strip */}
        <section className="py-12 border-y border-white/[0.04] overflow-hidden">
          <div className="flex items-center gap-8 animate-[marquee_30s_linear_infinite] whitespace-nowrap">
            {Array.from({ length: 3 }).flatMap((_, rep) =>
              ['ECOTOX Database', 'QSAR Ready', 'RDKit Integration', 'Mordred Descriptors', 'DAG Hierarchy', 'Parquet Storage', 'WebSocket Jobs', 'OECD Compliance', 'PCA Mapping', 'Chemical Space'].map((item, i) => (
                <div key={`${rep}-${i}`} className="flex items-center gap-3 shrink-0">
                  <Activity className="w-3.5 h-3.5 text-cyan-400/40" />
                  <span className="text-sm text-white/20 font-medium">{item}</span>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-32 px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="max-w-4xl mx-auto text-center glass p-16 rounded-[2.5rem] relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/10 to-violet-500/10 pointer-events-none" />
            {/* Glow orbs inside CTA */}
            <div className="absolute top-0 left-0 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-0 right-0 w-48 h-48 bg-violet-500/10 rounded-full blur-3xl pointer-events-none" />
            
            <h2 className="text-4xl font-bold text-white mb-6 relative z-10">
              Ready to accelerate your research?
            </h2>
            <p className="text-lg text-secondary mb-10 max-w-lg mx-auto relative z-10">
              Join leading pharmaceutical teams using SDO to process and analyze massive chemical datasets natively.
            </p>
            <button 
              onClick={onLaunch}
              className="relative z-10 px-8 py-4 rounded-xl bg-white text-void font-bold text-sm shadow-xl hover:bg-gray-100 hover:scale-105 transition-all"
            >
              Initialize Workspace Sandbox
            </button>
          </motion.div>
        </section>

        {/* Footer */}
        <footer className="py-8 text-center text-xs text-muted border-t border-white/[0.04]">
          &copy; {new Date().getFullYear()} Scientific Data Orchestrator. All rights reserved.
        </footer>
      </div>
    </div>
  );
};
