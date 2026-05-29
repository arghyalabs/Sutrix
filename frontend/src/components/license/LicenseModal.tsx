import React from 'react';
import { X, Scale, FileText, Download, ExternalLink, ShieldAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface LicenseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LicenseModal: React.FC<LicenseModalProps> = ({ isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Overlay backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-void/80 backdrop-blur-sm"
          />

          {/* Modal Container */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 15 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-xl glass border-white/[0.06] rounded-[2rem] p-6 relative overflow-hidden flex flex-col max-h-[90vh]"
          >
            <div className="absolute inset-0 bg-gradient-to-b from-white/[0.01] to-transparent pointer-events-none" />
            
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-white/[0.06] shrink-0">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-cyan-400" />
                <h2 className="text-md font-bold text-white uppercase tracking-wider">GNU AGPL-3.0 Compliance Details</h2>
              </div>
              <button 
                onClick={onClose}
                className="w-8 h-8 rounded-full bg-white/[0.03] flex items-center justify-center text-secondary hover:text-white hover:bg-white/[0.08] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto py-5 space-y-5 pr-1 text-xs text-secondary leading-relaxed">
              
              <div className="flex items-start gap-3 bg-cyan-500/[0.02] border border-cyan-500/10 p-4 rounded-xl">
                <ShieldAlert className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-bold text-white text-xs mb-1">Open-Source Copyleft Enforcement</h3>
                  <p>
                    SDO is distributed 100% free of charge under copyleft terms. You are free to modify, host, and distribute it, provided you release all modifications under the same AGPL-3.0 license.
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-white flex items-center gap-2">
                  <FileText className="w-3.5 h-3.5 text-cyan-400" />
                  Key AGPL-3.0 Compliance Requirements
                </h4>
                <ul className="list-disc pl-5 space-y-1.5">
                  <li><strong>Network Copyleft:</strong> Remote network interaction constitutes standard distribution. Source code MUST be made available to network users.</li>
                  <li><strong>State preservation of changes:</strong> Any changes made to source files must carry prominent date markers.</li>
                  <li><strong>Copyleft Inheritance:</strong> Sub-modules and derived libraries must also inherit GNU AGPL-3.0 rules.</li>
                </ul>
              </div>

              <div className="border-t border-white/[0.06] pt-4 space-y-3">
                <h4 className="font-bold text-white uppercase tracking-wider text-[10px]">Verify Source Compliance (AGPL-3.0 Section 13)</h4>
                <p>
                  To review matching source code or build derived works, you can access the repository or download a compiled snapshot:
                </p>
                <div className="flex flex-col sm:flex-row gap-3 pt-1">
                  <a 
                    href="https://github.com/ScientificDataOrchestrator/sdo"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-white hover:bg-white/[0.08] text-xs font-bold transition-all"
                  >
                    GitHub Repository
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  <a 
                    href="https://github.com/ScientificDataOrchestrator/sdo/archive/refs/heads/main.zip"
                    download
                    className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-cyan-500 text-void hover:bg-cyan-400 text-xs font-black transition-all shadow-md"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Source ZIP
                  </a>
                </div>
              </div>

            </div>

            {/* Footer */}
            <div className="pt-4 border-t border-white/[0.06] flex justify-end shrink-0">
              <button 
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-white/[0.04] text-white text-xs font-bold hover:bg-white/[0.08] transition-colors"
              >
                Close Details
              </button>
            </div>

          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
