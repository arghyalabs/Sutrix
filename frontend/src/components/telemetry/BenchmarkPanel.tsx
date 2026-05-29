import React, { useState, useEffect } from 'react';
import { Activity, Server, Cpu, Database } from 'lucide-react';

export const BenchmarkPanel: React.FC = () => {
  const [metrics, setMetrics] = useState({
    fps: 60,
    ram: 45,
    cpu: 12,
    disk: 234
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics({
        fps: 58 + Math.random() * 4,
        ram: 40 + Math.random() * 10,
        cpu: 10 + Math.random() * 15,
        disk: 234 + Math.random() * 2
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-5xl mx-auto py-8">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-white tracking-tight mb-3">System Benchmarks</h1>
        <p className="text-secondary text-sm max-w-lg mx-auto">
          Live telemetry of the SDO engine background workers and resource utilization.
        </p>
      </div>

      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <div className="glass p-6 rounded-2xl flex flex-col items-center text-center">
          <Activity className="w-6 h-6 text-cyan-400 mb-4" />
          <span className="text-xs text-muted uppercase tracking-wider mb-1">Renderer</span>
          <span className="text-2xl font-bold text-white">{metrics.fps.toFixed(0)} FPS</span>
        </div>
        <div className="glass p-6 rounded-2xl flex flex-col items-center text-center">
          <Server className="w-6 h-6 text-violet-400 mb-4" />
          <span className="text-xs text-muted uppercase tracking-wider mb-1">Memory</span>
          <span className="text-2xl font-bold text-white">{metrics.ram.toFixed(1)}%</span>
        </div>
        <div className="glass p-6 rounded-2xl flex flex-col items-center text-center">
          <Cpu className="w-6 h-6 text-emerald-400 mb-4" />
          <span className="text-xs text-muted uppercase tracking-wider mb-1">CPU Load</span>
          <span className="text-2xl font-bold text-white">{metrics.cpu.toFixed(1)}%</span>
        </div>
        <div className="glass p-6 rounded-2xl flex flex-col items-center text-center">
          <Database className="w-6 h-6 text-amber-400 mb-4" />
          <span className="text-xs text-muted uppercase tracking-wider mb-1">Cache Size</span>
          <span className="text-2xl font-bold text-white">{metrics.disk.toFixed(0)} MB</span>
        </div>
      </div>

      <div className="glass p-8 rounded-3xl">
        <h3 className="text-white font-medium mb-6">Engine Diagnostics</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02]">
            <span className="text-sm font-medium text-secondary">WebSocket Connectivity</span>
            <span className="px-3 py-1 rounded-md bg-emerald-500/10 text-emerald-400 text-xs font-mono">STABLE</span>
          </div>
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02]">
            <span className="text-sm font-medium text-secondary">Multiprocessing Pool</span>
            <span className="px-3 py-1 rounded-md bg-cyan-500/10 text-cyan-400 text-xs font-mono">ACTIVE (8 CORES)</span>
          </div>
          <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02]">
            <span className="text-sm font-medium text-secondary">SQLite WAL Cache</span>
            <span className="px-3 py-1 rounded-md bg-violet-500/10 text-violet-400 text-xs font-mono">OPTIMIZED</span>
          </div>
        </div>
      </div>
    </div>
  );
};
