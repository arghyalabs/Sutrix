import React, { useState } from 'react';
import { ShieldCheck, Download, ExternalLink, Scale, CheckCircle2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface LicenseGateProps {
  onAccept: () => void;
}

export const LicenseGate: React.FC<LicenseGateProps> = ({ onAccept }) => {
  const [agreed, setAgreed] = useState(false);

  return (
    <div className="min-h-screen bg-void flex items-center justify-center p-6 relative overflow-hidden">
      
      {/* Background ambient glows */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full blur-[120px] pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-2xl glass p-8 rounded-[2.5rem] border-white/[0.06] relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-white/[0.01] to-transparent pointer-events-none" />
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mx-auto mb-4">
            <Scale className="w-8 h-8" />
          </div>
          <h1 className="text-2.5xl font-black text-white tracking-tight">Open Source Compliance Gate</h1>
          <p className="text-secondary text-sm mt-2">
            SDO is licensed under the GNU Affero General Public License v3 (AGPL-3.0).
          </p>
        </div>

        {/* Copyleft legal statement block */}
        <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-5 space-y-4 text-xs text-secondary leading-relaxed">
          <h3 className="text-white font-bold flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            GNU AGPL-3.0 Copyleft Compliance Notice
          </h3>
          <p>
            By using this software over a computer network, you acknowledge that SDO is governed by the <strong>GNU Affero General Public License v3</strong>. 
            All modifications and derived works must be licensed under the identical AGPL-3.0 license and made available to all users.
          </p>
          <p className="border-t border-white/[0.04] pt-3">
            <strong>Section 13 (Remote Network Interaction):</strong> 
            If you modify SDO, you must prominently offer all users interacting with it remotely through a computer network an opportunity to receive the Corresponding Source of your version at no charge.
          </p>
        </div>

        {/* Section 13 Compliant Source Download Card */}
        <div className="mt-6 bg-cyan-500/[0.02] border border-cyan-500/10 rounded-2xl p-5 flex items-center justify-between gap-4">
          <div>
            <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">AGPL-3.0 Section 13 Mandate</h4>
            <p className="text-[10px] text-cyan-400/80 leading-normal max-w-sm">
              Verify compliance. Access or download the complete matching source code repository instantly.
            </p>
          </div>
          <a 
            href="https://github.com/ScientificDataOrchestrator/sdo"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-bold text-xs hover:bg-cyan-500/20 transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            Source Repository
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>

        {/* Agreement checkbox */}
        <label className="flex items-start gap-3 mt-8 cursor-pointer select-none group">
          <input 
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="w-4 h-4 rounded border-white/[0.08] bg-void text-cyan-400 focus:ring-cyan-500/20 mt-0.5"
          />
          <span className="text-xs text-secondary leading-normal group-hover:text-white transition-colors">
            I accept the copyleft terms of the <strong>GNU Affero General Public License v3 (AGPL-3.0)</strong> and acknowledge that all network uses are governed by it.
          </span>
        </label>

        {/* Proceed Action Button */}
        <button
          onClick={onAccept}
          disabled={!agreed}
          className="w-full mt-6 flex items-center justify-center gap-2 px-6 py-4 rounded-xl bg-white text-void font-bold text-sm shadow-xl hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
        >
          <CheckCircle2 className="w-4 h-4" />
          Acknowledge & Proceed to Workspace
        </button>

      </motion.div>
    </div>
  );
};
