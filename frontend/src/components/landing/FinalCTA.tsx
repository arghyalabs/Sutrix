import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { LogoLoader } from '../ui/SUTRIXLogo';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';

interface FinalCTAProps {
  onLaunch: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({ onLaunch }) => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  const hasActiveSession = useWorkspaceStore(state => !!state.filename);

  return (
    <section
      ref={ref}
      className="py-32 px-6 bg-[#020610] border-t border-white/[0.04] relative overflow-hidden"
    >
      {/* Ambient background glows */}
      <motion.div
        animate={{ opacity: [0.4, 0.7, 0.4] }}
        transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-[-30%] left-[-20%] w-[80%] h-[80%] rounded-full bg-cyan-500/[0.04] blur-[120px] pointer-events-none"
      />
      <motion.div
        animate={{ opacity: [0.3, 0.6, 0.3] }}
        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut', delay: 3 }}
        className="absolute bottom-[-30%] right-[-20%] w-[70%] h-[70%] rounded-full bg-violet-500/[0.04] blur-[120px] pointer-events-none"
      />

      <div className="relative z-10 max-w-3xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="space-y-8"
        >
          {/* 3D logo */}
          <div className="flex justify-center">
            <LogoLoader size="w-20 h-20" compact />
          </div>

          <h2 className="text-5xl font-extrabold text-white leading-tight">
            Build AI-Ready
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-gray-300 via-gray-100 to-gray-400">
              Scientific Datasets
            </span>
          </h2>

          <p className="text-xl text-white/40 leading-relaxed max-w-xl mx-auto">
            Transform raw toxicology data into structured, lineage-aware scientific intelligence
            workflows — without writing a single line of code.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <button
              onClick={onLaunch}
              className="group flex items-center gap-2.5 px-8 py-4 rounded-lg bg-white text-black font-semibold text-sm transition-all hover:-translate-y-0.5 active:translate-y-0 shadow-[0_4px_14px_rgba(255,255,255,0.15)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.25)]"
            >
              {hasActiveSession ? 'Continue Workflow' : 'Launch Workspace'}
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
            <a
              href="#workflow"
              className="group flex items-center gap-2 px-8 py-4 rounded-lg bg-white/[0.03] border border-white/10 text-white/70 font-semibold text-sm hover:bg-white/[0.06] hover:text-white transition-all hover:-translate-y-0.5"
            >
              Explore Workflow
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>

          {/* Subtle trust indicators */}
          <div className="flex flex-wrap items-center justify-center gap-6 pt-4">
            {['AGPL-3.0 Open Source', 'Offline-First', 'No Cloud Required', 'OECD Compatible'].map(tag => (
              <span key={tag} className="text-[10px] font-semibold uppercase tracking-widest text-white/20">
                {tag}
              </span>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <div className="relative z-10 mt-20 pt-10 border-t border-white/[0.04] text-center">
        <p className="text-xs text-white/15">
          &copy; {new Date().getFullYear()} Scientific Data Orchestrator — AGPL-3.0 License
        </p>
      </div>
    </section>
  );
};
