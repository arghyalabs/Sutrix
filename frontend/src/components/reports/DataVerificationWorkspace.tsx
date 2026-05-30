import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Loader2, AlertCircle, Database, BarChart3,
  CheckCircle2, FlaskConical, ArrowRight, Table2, Eye
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid
} from 'recharts';

interface DataVerificationWorkspaceProps {
  clientId: string;
  activeJobId: string | null;
}

interface DescriptorData {
  name: string;
  value: number;
}

interface PreviewResult {
  found: boolean;
  message?: string;
  meta?: {
    SMILES: string;
    'Target Endpoint': string;
    'Matched Name/ID': string;
  };
  descriptors?: DescriptorData[];
}

const COLORS = ['#06b6d4', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899', '#3b82f6'];

export const DataVerificationWorkspace: React.FC<DataVerificationWorkspaceProps> = ({
  clientId,
  activeJobId,
}) => {
  const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  const handleSearch = async (e: React.FormEvent | null, overrideQuery?: string) => {
    if (e) e.preventDefault();
    const q = overrideQuery ?? query;
    if (!q.trim()) return;

    setLoading(true);
    setResult(null);
    try {
      const url = `${API_BASE}/api/jobs/${clientId}/compound_preview?query=${encodeURIComponent(q)}${
        activeJobId ? `&job_id=${activeJobId}` : ''
      }`;
      const res = await fetch(url);
      const data = await res.json();
      setResult(res.ok ? data : { found: false, message: data.detail || 'Error searching dataset.' });
      if (res.ok && data.found) {
        setSearchHistory(prev => [q, ...prev.filter(h => h !== q)].slice(0, 5));
      }
    } catch (err: any) {
      setResult({ found: false, message: err.message || 'Network error.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-8">

      {/* ── Header ────────────────────────────────────────────── */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Data Verification</h1>
            <p className="text-white/40 text-sm mt-1">
              Verify calculated descriptors in your enriched dataset by searching compounds
            </p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Enriched Dataset Active
          </div>
        </div>
      </motion.div>

      {/* ── Search Card ────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="rounded-2xl border border-white/[0.06] bg-white/[0.02] backdrop-blur-xl p-6"
      >
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center">
            <Search className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-white">Compound Lookup</h2>
            <p className="text-xs text-white/35 mt-0.5">Search by compound name, SMILES string, or CAS number</p>
          </div>
        </div>

        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. Atenolol, CC(=O)Oc1ccccc1C(=O)O, or 50-78-2"
              className="w-full bg-black/40 border border-white/[0.08] rounded-xl pl-11 pr-4 py-3
                text-sm text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50
                transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-3 rounded-xl bg-cyan-500/20 text-cyan-400 font-semibold text-sm
              hover:bg-cyan-500/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed
              flex items-center gap-2 border border-cyan-500/20 whitespace-nowrap"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Search className="w-4 h-4" /> Verify</>}
          </button>
        </form>

        {/* Recent searches */}
        {searchHistory.length > 0 && (
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            <span className="text-xs text-white/25">Recent:</span>
            {searchHistory.map(h => (
              <button
                key={h}
                onClick={() => { setQuery(h); handleSearch(null, h); }}
                className="text-xs px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.06]
                  text-white/45 hover:text-white/70 hover:bg-white/[0.07] transition-all"
              >
                {h}
              </button>
            ))}
          </div>
        )}
      </motion.div>

      {/* ── Help cards (shown before any search) ──────────────── */}
      {!result && !loading && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          {[
            { icon: FlaskConical, color: '#06b6d4', title: 'Verify by Name', desc: 'Enter a chemical name like "Aspirin" or "Atenolol" to look up its enriched descriptors.' },
            { icon: Database, color: '#10b981', title: 'Verify by SMILES', desc: 'Paste a canonical SMILES string to verify structural descriptors were computed correctly.' },
            { icon: BarChart3, color: '#8b5cf6', title: 'Verify by CAS', desc: 'Enter a CAS registry number (e.g. 50-78-2) to check if the compound was resolved and enriched.' },
          ].map(({ icon: Icon, color, title, desc }) => (
            <div key={title} className="rounded-xl border border-white/[0.05] bg-white/[0.02] p-5">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
                style={{ background: `${color}15`, border: `1px solid ${color}25` }}>
                <Icon className="w-4 h-4" style={{ color }} />
              </div>
              <h3 className="text-sm font-semibold text-white mb-1">{title}</h3>
              <p className="text-xs text-white/35 leading-relaxed">{desc}</p>
            </div>
          ))}
        </motion.div>
      )}

      {/* ── Result ────────────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex items-center justify-center py-20 gap-3 text-white/40"
          >
            <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
            <span className="text-sm">Searching enriched dataset…</span>
          </motion.div>
        )}

        {result && !loading && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="space-y-4"
          >
            {/* Status banner */}
            <div className={`flex items-center gap-3 px-5 py-3.5 rounded-xl border text-sm font-medium
              ${result.found
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              }`}>
              {result.found
                ? <><CheckCircle2 className="w-4 h-4" /> Compound found and verified in enriched dataset</>
                : <><AlertCircle className="w-4 h-4" /> {result.message}</>
              }
            </div>

            {result.found && (
              <div className="grid md:grid-cols-[340px,1fr] gap-4">

                {/* Meta panel */}
                <div className="space-y-3">
                  {[
                    { label: 'Matched Compound', value: result.meta?.['Matched Name/ID'], color: 'text-white', mono: false },
                    { label: 'SMILES Structure', value: result.meta?.SMILES, color: 'text-emerald-400', mono: true },
                    { label: 'Target Endpoint', value: result.meta?.['Target Endpoint'], color: 'text-cyan-400', mono: true },
                  ].map(({ label, value, color, mono }) => (
                    <div key={label} className="rounded-xl bg-black/30 border border-white/[0.06] p-4">
                      <p className="text-white/35 text-[10px] uppercase tracking-wider font-semibold mb-2">{label}</p>
                      <p className={`text-sm break-all ${mono ? 'font-mono' : 'font-medium'} ${color}`}>
                        {value || '—'}
                      </p>
                    </div>
                  ))}

                  {/* Descriptor count badge */}
                  {result.descriptors && (
                    <div className="rounded-xl bg-violet-500/10 border border-violet-500/20 p-4 flex items-center gap-3">
                      <Eye className="w-4 h-4 text-violet-400 flex-shrink-0" />
                      <div>
                        <p className="text-violet-300 font-semibold text-sm">{result.descriptors.length} Descriptors Computed</p>
                        <p className="text-white/35 text-xs mt-0.5">Showing top values by magnitude</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Chart panel */}
                <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="w-4 h-4 text-violet-400" />
                    <h3 className="text-white font-semibold text-sm">Top Calculated Descriptors</h3>
                  </div>
                  <div className="h-[280px]">
                    {result.descriptors && result.descriptors.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={result.descriptors} margin={{ top: 6, right: 8, left: -20, bottom: 40 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                          <XAxis
                            dataKey="name"
                            stroke="rgba(255,255,255,0.2)"
                            fontSize={9}
                            tickMargin={8}
                            angle={-40}
                            textAnchor="end"
                          />
                          <YAxis
                            stroke="rgba(255,255,255,0.2)"
                            fontSize={9}
                            tickFormatter={val => val > 1000 ? `${(val / 1000).toFixed(1)}k` : String(val)}
                          />
                          <Tooltip
                            cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                            contentStyle={{
                              backgroundColor: '#040810',
                              border: '1px solid rgba(255,255,255,0.08)',
                              borderRadius: '10px',
                              fontSize: '12px',
                            }}
                            itemStyle={{ color: '#06b6d4', fontWeight: 'bold' }}
                            labelStyle={{ color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}
                          />
                          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                            {result.descriptors.map((_, i) => (
                              <Cell key={i} fill={COLORS[i % COLORS.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-white/25">
                        <BarChart3 className="w-8 h-8" />
                        <p className="text-xs">No prominent descriptors found for this compound</p>
                      </div>
                    )}
                  </div>
                </div>

              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Proceed to Export CTA ─────────────────────────────── */}
      {result?.found && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex items-center justify-between px-6 py-4 rounded-2xl border border-cyan-500/15
            bg-cyan-500/5"
        >
          <div>
            <p className="text-white font-semibold text-sm">Dataset verified — ready to export</p>
            <p className="text-white/35 text-xs mt-0.5">Proceed to the Export step to download your enriched dataset</p>
          </div>
          <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold">
            Go to Export <ArrowRight className="w-4 h-4" />
          </div>
        </motion.div>
      )}

    </div>
  );
};
