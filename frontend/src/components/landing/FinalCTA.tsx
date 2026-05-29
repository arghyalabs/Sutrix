import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { SUTRIXLogo } from '../ui/SUTRIXLogo';

interface FinalCTAProps {
  onLaunch: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({ onLaunch }) => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

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
          {/* Spinning logo */}
          <div className="flex justify-center">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
            >
              <SUTRIXLogo className="w-14 h-14 opacity-50" />
            </motion.div>
          </div>

          <h2 className="text-5xl font-extrabold text-white leading-tight">
            Build AI-Ready
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-violet-400 to-cyan-400">
              Scientific Datasets
            </span>
          </h2>

          <p className="text-xl text-white/40 leading-relaxed max-w-xl mx-auto">
            Transform raw toxicology data into structured, lineage-aware scientific intelligence
            workflows — without writing a single line of code.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-2">
            <motion.button
              whileHover={{ scale: 1.03, boxShadow: '0 0 40px rgba(34,211,238,0.28)' }}
              whileTap={{ scale: 0.97 }}
              onClick={onLaunch}
              className="group flex items-center gap-2.5 px-8 py-4 rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 text-white font-bold text-sm shadow-[0_0_30px_rgba(34,211,238,0.18)] transition-all"
            >
              Launch Workspace
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </motion.button>
            <motion.a
              whileHover={{ scale: 1.02 }}
              href="#workflow"
              className="flex items-center gap-2 px-8 py-4 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white/60 font-semibold text-sm hover:bg-white/[0.07] hover:text-white transition-all"
            >
              Explore Workflow
              <ExternalLink className="w-3.5 h-3.5" />
            </motion.a>
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
