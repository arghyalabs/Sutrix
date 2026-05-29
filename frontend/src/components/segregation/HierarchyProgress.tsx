import React, { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Activity, Cpu } from 'lucide-react';

interface HierarchyProgressProps {
  socket: any;
  onComplete: () => void;
}

export const HierarchyProgress: React.FC<HierarchyProgressProps> = ({ socket, onComplete }) => {
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (socket.jobStatus === 'COMPLETED') {
      const timer = setTimeout(() => onComplete(), 1500);
      return () => clearTimeout(timer);
    }
  }, [socket.jobStatus, onComplete]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [socket.logs]);

  const progress = socket.progress || 0;
  const phase = socket.jobStatus === 'COMPLETED' ? '🏁 Offline Segregation & Graphing Complete' : 
                socket.jobStatus === 'FAILED' ? `⚠️ Job Failed: ${socket.error}` : 
                socket.phase || 'Initializing Engine...';
  const logs = socket.logs || [];

  // SVG Circular Progress Calculation
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div className="max-w-3xl mx-auto py-12">
      <div className="glass rounded-[2rem] p-10 border border-white/[0.06] relative overflow-hidden">
        {/* Ambient Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 blur-[100px] rounded-full" />
        
        <div className="relative z-10 flex flex-col items-center">
          
          <div className="relative w-48 h-48 flex items-center justify-center mb-8">
            <svg className="w-full h-full transform -rotate-90">
              {/* Background circle */}
              <circle
                cx="96" cy="96" r={radius}
                className="stroke-white/[0.05] fill-none"
                strokeWidth="8"
              />
              {/* Progress circle */}
              <motion.circle
                cx="96" cy="96" r={radius}
                className="stroke-cyan-400 fill-none"
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </svg>
            
            <div className="absolute flex flex-col items-center">
              <span className="text-4xl font-bold text-white tracking-tighter">
                {Math.round(progress)}<span className="text-xl text-cyan-400/80">%</span>
              </span>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mb-2 flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
            {phase}
          </h2>
          <p className="text-sm text-secondary mb-8">Building DAG topology and computing statistics...</p>

          {/* Terminal Console */}
          <div className="w-full bg-[#0a0d18] rounded-xl border border-white/[0.08] p-4 h-48 overflow-y-auto font-mono text-[10px] sm:text-xs">
            <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/[0.05] text-muted">
              <Cpu className="w-3.5 h-3.5" />
              <span>Engine Terminal Output</span>
            </div>
            
            <div className="space-y-1.5">
              {logs.map((log: string, i: number) => (
                <div key={i} className="flex gap-2">
                  <span className="text-cyan-500/50 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                  <span className="text-slate-300 break-words">{log}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
};
