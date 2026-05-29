import React, { useEffect, useState, useMemo } from 'react';
import { Play, Ban, ChevronRight, Cpu, Zap, Beaker, Activity, Terminal, Search, CheckSquare, Square, ListFilter, Star } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Progress from '@radix-ui/react-progress';
import { useWorkspaceStore } from '../../store/useWorkspaceStore';
import { enrichmentApi } from '../../services/enrichmentApi';

interface DescriptorEnrichmentProps {
  enrichmentMode: 'fast' | 'standard' | 'full';
  setEnrichmentMode: (mode: 'fast' | 'standard' | 'full') => void;
  includeMordred: boolean;
  setIncludeMordred: (include: boolean) => void;
  handleRunEnrichment: () => Promise<void>;
  handleCancelJob: () => Promise<void>;
  handleFetchEnrichmentResults: () => Promise<void>;
  socket: any;
  ramUsage: number;
  fps: number;
}

const modes = [
  {
    id: 'fast' as const,
    label: 'Fast Mode',
    icon: Zap,
    accent: 'cyan',
    desc: '9 core properties (MW, LogP, TPSA, HBD/A, RB, AROM, QED, SlogP)',
    color: 'from-cyan-500/10 to-cyan-500/5 border-cyan-500/30',
    activeText: 'text-cyan-400',
  },
  {
    id: 'standard' as const,
    label: 'Standard Mode',
    icon: Beaker,
    accent: 'violet',
    desc: 'RDKit 2D+3D suite — ~208 descriptors',
    color: 'from-violet-500/10 to-violet-500/5 border-violet-500/30',
    activeText: 'text-violet-400',
  },
  {
    id: 'full' as const,
    label: 'Full Research',
    icon: Cpu,
    accent: 'rose',
    desc: '2,043 2D/3D descriptors via Mordred',
    color: 'from-rose-500/10 to-rose-500/5 border-rose-500/30',
    activeText: 'text-rose-400',
  },
];

const FAST_DESCRIPTORS = ['MolWt', 'LogP', 'TPSA', 'HBA', 'HBD', 'RotatableBonds', 'RingCount', 'HeavyAtomCount', 'FractionCSP3'];

const RECOMMENDED_RDKIT = [
  'MolWt', 'MolLogP', 'TPSA', 'NumHDonors', 'NumHAcceptors', 
  'NumRotatableBonds', 'RingCount', 'HeavyAtomCount', 'FractionCSP3', 'QED', 'BertzCT', 'MaxPartialCharge'
];

const RECOMMENDED_MORDRED = [
  'ABC', 'ABCGG', 'nAcid', 'nBase', 'SpAbs_A', 'SpMax_A', 'SpDiam_A', 
  'SpAD_A', 'SpMAD_A', 'LogEE_A', 'VE1_A', 'VE2_A', 'VE3_A', 'VR1_A', 'VR2_A', 'VR3_A', 'Vv'
];

export const DescriptorEnrichment: React.FC<DescriptorEnrichmentProps> = ({
  enrichmentMode,
  setEnrichmentMode,
  includeMordred,
  setIncludeMordred,
  handleRunEnrichment,
  handleCancelJob,
  handleFetchEnrichmentResults,
  socket,
}) => {
  const { activeJobType, selectedDescriptors, setSelectedDescriptors } = useWorkspaceStore();
  const isRunning = socket.jobStatus === 'RUNNING' && activeJobType === 'enrichment';
  const isCompleted = socket.jobStatus === 'COMPLETED' && activeJobType === 'enrichment';

  const [rdkitAvailable, setRdkitAvailable] = useState<string[]>([]);
  const [mordredAvailable, setMordredAvailable] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchDescriptors = async () => {
      try {
        const data = await enrichmentApi.fetchAvailableDescriptors();
        if (mounted) {
          setRdkitAvailable(data.rdkit || []);
          setMordredAvailable(data.mordred || []);
        }
      } catch (err) {
        console.error('Failed to fetch descriptors', err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchDescriptors();
    return () => { mounted = false; };
  }, []);

  const searchWords = searchQuery.toLowerCase().split(' ').filter(w => w);

  const filterList = (list: string[]) => {
    if (searchWords.length === 0) return list;
    return list.filter(d => {
      const dLower = d.toLowerCase();
      // Act like Google Search: All keywords must match somewhere in the descriptor name
      return searchWords.every(word => dLower.includes(word));
    });
  };

  const filteredRdkit = useMemo(() => filterList(rdkitAvailable), [rdkitAvailable, searchQuery]);
  const filteredMordred = useMemo(() => filterList(mordredAvailable), [mordredAvailable, searchQuery]);

  const rdkitRecommended = useMemo(() => filteredRdkit.filter(d => RECOMMENDED_RDKIT.includes(d)), [filteredRdkit]);
  const rdkitOther = useMemo(() => filteredRdkit.filter(d => !RECOMMENDED_RDKIT.includes(d)), [filteredRdkit]);

  const mordredRecommended = useMemo(() => filteredMordred.filter(d => RECOMMENDED_MORDRED.includes(d)), [filteredMordred]);
  const mordredOther = useMemo(() => filteredMordred.filter(d => !RECOMMENDED_MORDRED.includes(d)), [filteredMordred]);


  const handleToggle = (desc: string) => {
    if (selectedDescriptors.includes(desc)) {
      setSelectedDescriptors(selectedDescriptors.filter(d => d !== desc));
    } else {
      setSelectedDescriptors([...selectedDescriptors, desc]);
    }
  };

  const handleModeSelect = (modeId: 'fast' | 'standard' | 'full') => {
    setEnrichmentMode(modeId);
    if (modeId === 'fast') {
      setSelectedDescriptors(FAST_DESCRIPTORS.filter(d => rdkitAvailable.includes(d) || FAST_DESCRIPTORS.includes(d)));
      setIncludeMordred(false);
    } else if (modeId === 'standard') {
      setSelectedDescriptors(rdkitAvailable);
      setIncludeMordred(false);
    } else if (modeId === 'full') {
      setSelectedDescriptors([...rdkitAvailable, ...mordredAvailable]);
      setIncludeMordred(true);
    }
  };

  const selectAllRdkit = () => {
    const newSelection = Array.from(new Set([...selectedDescriptors, ...rdkitAvailable]));
    setSelectedDescriptors(newSelection);
  };

  const selectAllMordred = () => {
    const newSelection = Array.from(new Set([...selectedDescriptors, ...mordredAvailable]));
    setSelectedDescriptors(newSelection);
    setIncludeMordred(true);
  };

  const clearAll = () => {
    setSelectedDescriptors([]);
  };

  const renderDescriptorGrid = (title: string, list: string[], iconColor: string) => {
    if (list.length === 0) return null;
    return (
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <p className={`text-[10px] font-bold uppercase tracking-wider ${iconColor}`}>{title} ({list.length})</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {list.map(desc => {
            const isSelected = selectedDescriptors.includes(desc);
            const isRdkit = rdkitAvailable.includes(desc);
            const activeColorBg = isRdkit ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-violet-500/10 border-violet-500/30';
            const activeTextColor = isRdkit ? 'text-cyan-400' : 'text-violet-400';
            const activeTextLightColor = isRdkit ? 'text-cyan-100' : 'text-violet-100';

            return (
              <button
                key={desc}
                onClick={() => handleToggle(desc)}
                className={`flex items-center gap-2 p-1.5 rounded-lg border text-left transition-all ${isSelected ? activeColorBg : 'bg-white/[0.02] border-white/[0.04] hover:border-white/[0.1]'}`}
              >
                {isSelected ? <CheckSquare className={`w-3.5 h-3.5 ${activeTextColor} shrink-0`} /> : <Square className="w-3.5 h-3.5 text-white/20 shrink-0" />}
                <span className={`text-xs truncate ${isSelected ? `${activeTextLightColor} font-medium` : 'text-white/60'}`} title={desc}>{desc}</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* LEFT: Configuration panel */}
      <div className="w-[450px] shrink-0 border-r border-white/[0.06] bg-[#080f1f] flex flex-col overflow-hidden">
        <div className="px-6 py-5 border-b border-white/[0.06] shrink-0">
          <h2 className="text-white font-bold text-base flex items-center gap-2">
            <Zap className="w-4 h-4 text-cyan-400" />
            Descriptor Selection
          </h2>
          <p className="text-white/40 text-xs mt-1 leading-relaxed">
            Select exact properties to calculate offline.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {/* Modes Presets */}
          <div className="p-5 border-b border-white/[0.06]">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-3">
              Compute Presets
            </p>
            <div className="space-y-2">
              {modes.map(mode => {
                const Icon = mode.icon;
                const isActive = enrichmentMode === mode.id;
                return (
                  <button
                    key={mode.id}
                    onClick={() => handleModeSelect(mode.id)}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      isActive
                        ? `bg-gradient-to-br ${mode.color} ring-1 ring-inset ${mode.color.includes('cyan') ? 'ring-cyan-500/20' : mode.color.includes('violet') ? 'ring-violet-500/20' : 'ring-rose-500/20'}`
                        : 'bg-white/[0.02] border-white/[0.06] hover:border-white/[0.12]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`w-4 h-4 ${isActive ? mode.activeText : 'text-white/30'}`} />
                      <div>
                        <span className={`text-sm font-bold block ${isActive ? mode.activeText : 'text-white/60'}`}>
                          {mode.label}
                        </span>
                        <span className="text-[10px] text-white/40">{mode.desc}</span>
                      </div>
                      {isActive && (
                        <span className={`ml-auto shrink-0 text-[9px] font-bold px-2 py-0.5 rounded-full ${
                          mode.accent === 'cyan' ? 'bg-cyan-500/20 text-cyan-300' :
                          mode.accent === 'violet' ? 'bg-violet-500/20 text-violet-300' :
                          'bg-rose-500/20 text-rose-300'
                        }`}>
                          ACTIVE
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Checklist */}
          <div className="p-5">
            <div className="flex items-center gap-2 mb-3">
              <ListFilter className="w-4 h-4 text-white/30" />
              <p className="text-[10px] font-bold uppercase tracking-wider text-white/30">
                Custom Selection
              </p>
              <span className="ml-auto text-[10px] text-white/30">{selectedDescriptors.length} total selected</span>
            </div>
            
            <div className="relative mb-3">
              <Search className="w-4 h-4 text-white/30 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search keywords (e.g. 'log', 'ring')..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-cyan-500/50 transition-colors"
              />
            </div>

            <div className="flex gap-2 mb-4 overflow-x-auto custom-scrollbar pb-1">
              <button onClick={selectAllRdkit} className="whitespace-nowrap px-3 py-1 rounded-lg bg-cyan-500/10 text-cyan-400 text-[11px] font-semibold hover:bg-cyan-500/20 transition-colors">
                + All RDKit
              </button>
              <button onClick={selectAllMordred} className="whitespace-nowrap px-3 py-1 rounded-lg bg-violet-500/10 text-violet-400 text-[11px] font-semibold hover:bg-violet-500/20 transition-colors">
                + All Mordred
              </button>
              <button onClick={clearAll} className="whitespace-nowrap px-3 py-1 rounded-lg bg-white/5 text-white/60 text-[11px] font-semibold hover:bg-white/10 hover:text-white transition-colors">
                Clear All
              </button>
            </div>

            {loading ? (
              <div className="flex flex-col items-center justify-center py-10 opacity-50">
                <Zap className="w-6 h-6 text-cyan-400 animate-pulse mb-3" />
                <p className="text-white/50 text-[10px] uppercase tracking-wider font-bold">Loading Library...</p>
              </div>
            ) : (
              <div className="space-y-6 pb-4">
                
                {/* RDKIT SECTION */}
                {(rdkitRecommended.length > 0 || rdkitOther.length > 0) && (
                  <div>
                    <div className="flex items-center gap-2 border-b border-white/[0.04] pb-2 mb-3">
                      <Zap className="w-4 h-4 text-cyan-400" />
                      <h3 className="text-sm font-bold text-white">RDKit Descriptors</h3>
                      <span className="ml-auto text-[10px] text-white/30">{selectedDescriptors.filter(d => rdkitAvailable.includes(d)).length} selected</span>
                    </div>
                    {renderDescriptorGrid('★ Recommended', rdkitRecommended, 'text-amber-400/70')}
                    {renderDescriptorGrid('All RDKit Properties', rdkitOther, 'text-cyan-400/70')}
                  </div>
                )}

                {/* MORDRED SECTION */}
                {(mordredRecommended.length > 0 || mordredOther.length > 0) && (
                  <div className="mt-8">
                    <div className="flex items-center gap-2 border-b border-white/[0.04] pb-2 mb-3">
                      <Beaker className="w-4 h-4 text-violet-400" />
                      <h3 className="text-sm font-bold text-white">Mordred Engine</h3>
                      <span className="ml-auto text-[10px] text-white/30">{selectedDescriptors.filter(d => mordredAvailable.includes(d)).length} selected</span>
                    </div>
                    {renderDescriptorGrid('★ Recommended', mordredRecommended, 'text-amber-400/70')}
                    {renderDescriptorGrid('All Mordred Properties', mordredOther, 'text-violet-400/70')}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Run button */}
        <div className="p-5 border-t border-white/[0.06] shrink-0 bg-[#080f1f]/80 backdrop-blur-md">
          {!isRunning && !isCompleted ? (
            <button
              onClick={handleRunEnrichment}
              disabled={selectedDescriptors.length === 0}
              className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl
                bg-gradient-to-r from-cyan-500 to-violet-500 text-white font-bold text-sm
                shadow-[0_0_24px_rgba(34,211,238,0.3)] hover:shadow-[0_0_32px_rgba(34,211,238,0.45)]
                transition-all disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4 fill-current" />
              Run ({selectedDescriptors.length} descriptors)
            </button>
          ) : isRunning ? (
            <button
              onClick={handleCancelJob}
              className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl
                bg-rose-500/10 border border-rose-500/30 text-rose-400 font-bold text-sm
                hover:bg-rose-500/20 transition-all"
            >
              <Ban className="w-4 h-4" />
              Cancel Job
            </button>
          ) : isCompleted ? (
            <button
              onClick={handleFetchEnrichmentResults}
              className="w-full flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl
                bg-emerald-500 text-void font-bold text-sm
                shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:bg-emerald-400 transition-all"
            >
              Assemble Dataset <ChevronRight className="w-4 h-4" />
            </button>
          ) : null}
        </div>
      </div>

      {/* RIGHT: Live job telemetry */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-6 py-5 border-b border-white/[0.06] flex items-center gap-3">
          <Activity className="w-4 h-4 text-violet-400" />
          <h3 className="text-white font-bold text-sm">Job Telemetry</h3>
          {isRunning && (
            <span className="ml-auto flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Running
            </span>
          )}
          {isCompleted && (
            <span className="ml-auto text-xs text-cyan-400 font-bold">Completed ✓</span>
          )}
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
          <AnimatePresence>
            {(isRunning || isCompleted) ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                {/* Progress */}
                <div>
                  <div className="flex items-center justify-between text-xs mb-3">
                    <span className="text-white/50 font-medium">Overall Progress</span>
                    <span className="text-cyan-400 font-bold text-base">{socket.progress}%</span>
                  </div>
                  <Progress.Root className="h-2.5 w-full bg-white/[0.04] rounded-full overflow-hidden" value={socket.progress}>
                    <Progress.Indicator
                      className="h-full bg-gradient-to-r from-cyan-500 to-violet-500 rounded-full transition-all duration-500"
                      style={{ width: `${socket.progress}%` }}
                    />
                  </Progress.Root>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-3 gap-4">
                  {[
                    { label: 'Active Phase', value: socket.phase || 'Initializing...', accent: 'text-white' },
                    { label: 'Processing Rate', value: `${socket.speed || 0} cmp/s`, accent: 'text-cyan-400' },
                    { label: 'ETA', value: `${socket.eta || 0}s`, accent: 'text-violet-400' },
                  ].map(s => (
                    <div key={s.label} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                      <p className="text-[10px] uppercase tracking-wider text-white/30 font-bold mb-1.5">{s.label}</p>
                      <p className={`text-sm font-bold ${s.accent} truncate`}>{s.value}</p>
                    </div>
                  ))}
                </div>

                {/* Log console */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Terminal className="w-3.5 h-3.5 text-white/30" />
                    <p className="text-[10px] uppercase tracking-wider text-white/30 font-bold">Worker Log</p>
                  </div>
                  <div className="bg-[#040810] rounded-xl p-4 font-mono text-[11px] text-white/40
                    max-h-96 overflow-y-auto custom-scrollbar space-y-1.5 border border-white/[0.04]">
                    {socket.logs.length > 0 ? (
                      socket.logs.map((log: string, idx: number) => (
                        <div key={idx} className="hover:text-white/60 transition-colors leading-relaxed">
                          <span className="text-cyan-500/40 mr-2 select-none">›</span>{log}
                        </div>
                      ))
                    ) : (
                      <div className="text-white/20 italic">Awaiting worker initialization...</div>
                    )}
                  </div>
                </div>

                {isCompleted && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="p-5 rounded-2xl bg-emerald-500/[0.08] border border-emerald-500/20">
                      <p className="text-emerald-400 font-bold text-sm mb-1">✓ Job Complete</p>
                      <p className="text-white/40 text-xs mb-4">
                        All descriptors have been calculated. Click below to assemble the enriched dataset.
                      </p>
                      <button
                        onClick={handleFetchEnrichmentResults}
                        className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl
                          bg-emerald-500 text-void font-bold text-sm
                          hover:bg-emerald-400 transition-all"
                      >
                        Assemble Enriched Dataset <ChevronRight className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center py-24">
                <div className="w-20 h-20 rounded-3xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-center mb-5">
                  <Cpu className="w-10 h-10 text-white/10" />
                </div>
                <p className="text-white/30 text-sm font-medium">Ready</p>
                <p className="text-white/20 text-xs mt-1 max-w-xs">
                  Select your desired descriptors on the left and click Run to start generating features.
                </p>
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};
