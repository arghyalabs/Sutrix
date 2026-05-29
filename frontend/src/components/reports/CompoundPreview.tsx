import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2, AlertCircle, Database, LayoutDashboard } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid
} from 'recharts';

interface CompoundPreviewProps {
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
    "Target Endpoint": string;
    "Matched Name/ID": string;
  };
  descriptors?: DescriptorData[];
}

export const CompoundPreview: React.FC<CompoundPreviewProps> = ({ clientId, activeJobId }) => {
  const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PreviewResult | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setLoading(true);
    setResult(null);
    try {
      const url = `${API_BASE}/api/jobs/${clientId}/compound_preview?query=${encodeURIComponent(query)}${activeJobId ? `&job_id=${activeJobId}` : ''}`;
      const res = await fetch(url);
      const data = await res.json();
      
      if (!res.ok) {
        setResult({ found: false, message: data.detail || 'Error searching dataset.' });
      } else {
        setResult(data);
      }
    } catch (err: any) {
      setResult({ found: false, message: err.message || 'Network error.' });
    } finally {
      setLoading(false);
    }
  };

  const colors = ['#06b6d4', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899'];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass p-6 rounded-2xl border border-white/[0.06] mt-6 overflow-hidden relative"
    >
      <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/5 blur-[80px] rounded-full pointer-events-none" />
      
      <div className="flex flex-col md:flex-row gap-6 mb-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <Database className="w-5 h-5 text-cyan-400" />
            <h3 className="text-white font-bold text-lg">Data Verification Preview</h3>
          </div>
          <p className="text-white/40 text-sm">
            Verify the calculated descriptors in your enriched dataset by searching for a specific compound (by name, SMILES, or CAS).
          </p>
        </div>
        
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="e.g. Atenolol, Benzene, or SMILES..."
              className="w-full bg-black/40 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-cyan-500/50 transition-colors"
            />
          </div>
          <button 
            type="submit"
            disabled={loading || !query.trim()}
            className="px-5 py-2.5 rounded-xl bg-cyan-500/20 text-cyan-400 font-bold text-sm hover:bg-cyan-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
          </button>
        </form>
      </div>

      <AnimatePresence mode="wait">
        {result && (
          <motion.div
            key={query}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-white/[0.06] pt-6"
          >
            {!result.found ? (
              <div className="flex flex-col items-center justify-center py-10 bg-white/[0.02] rounded-xl border border-white/[0.05]">
                <AlertCircle className="w-8 h-8 text-white/20 mb-3" />
                <p className="text-white/40 text-sm">{result.message}</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-[1fr,2fr] gap-6">
                {/* Meta Panel */}
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06]">
                    <p className="text-white/40 text-xs mb-1 uppercase tracking-wider font-semibold">Matched Compound</p>
                    <p className="text-white font-mono text-sm break-all">{result.meta?.["Matched Name/ID"]}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06]">
                    <p className="text-white/40 text-xs mb-1 uppercase tracking-wider font-semibold">SMILES Structure</p>
                    <p className="text-emerald-400 font-mono text-xs break-all">{result.meta?.SMILES}</p>
                  </div>
                  <div className="p-4 rounded-xl bg-black/40 border border-white/[0.06]">
                    <p className="text-white/40 text-xs mb-1 uppercase tracking-wider font-semibold">Target Endpoint</p>
                    <p className="text-cyan-400 font-mono text-sm">{result.meta?.["Target Endpoint"]}</p>
                  </div>
                </div>

                {/* Chart Panel */}
                <div className="p-5 rounded-xl bg-black/40 border border-white/[0.06]">
                  <div className="flex items-center gap-2 mb-4">
                    <LayoutDashboard className="w-4 h-4 text-violet-400" />
                    <h4 className="text-white font-bold text-sm">Top Calculated Descriptors</h4>
                  </div>
                  <div className="h-[250px] w-full">
                    {result.descriptors && result.descriptors.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={result.descriptors} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                          <XAxis 
                            dataKey="name" 
                            stroke="rgba(255,255,255,0.3)" 
                            fontSize={10}
                            tickMargin={10}
                            angle={-45}
                            textAnchor="end"
                          />
                          <YAxis 
                            stroke="rgba(255,255,255,0.3)" 
                            fontSize={10}
                            tickFormatter={(val) => val > 1000 ? `${(val/1000).toFixed(1)}k` : val}
                          />
                          <Tooltip 
                            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                            contentStyle={{ backgroundColor: '#040810', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                            itemStyle={{ color: '#06b6d4', fontWeight: 'bold' }}
                            labelStyle={{ color: 'rgba(255,255,255,0.6)', marginBottom: '4px' }}
                          />
                          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                            {result.descriptors.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-white/30 text-xs">
                        No prominent descriptors found.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
