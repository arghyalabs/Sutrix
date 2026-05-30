import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, Grid, BarChart2, Zap, Activity, Download,
  LogOut, HelpCircle, FileDigit, Scale, Network, CheckSquare, Settings
} from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import { SUTRIXLogo, LogoLoader } from '../ui/SUTRIXLogo';

// Tabs that need true fullscreen (no scroll wrapper, no padding)
const FULLSCREEN_TABS = new Set(['hierarchy', 'analysis', 'enrichment', 'readiness', 'verification']);

interface SidebarItem {
  id: string;
  name: string;
  icon: React.ReactNode;
  stepNum: number;
}

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onExit: () => void;
  onGoHome: () => void;
  onOpenLicense: () => void;
  onOpenSystem?: () => void;
  telemetryData?: {
    ram_usage_pct: number;
    fps: number;
    active_jobs_count: number;
  };
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  activeTab,
  setActiveTab,
  onExit,
  onGoHome,
  onOpenLicense,
  onOpenSystem,
  telemetryData = { ram_usage_pct: 42, fps: 60, active_jobs_count: 0 }
}) => {
  const [collapsed, setCollapsed] = useState(true);
  const [showHelp, setShowHelp] = useState(false);

  const sidebarItems: SidebarItem[] = [
    { id: 'ingest',       name: 'Upload Dataset',      icon: <Upload className="w-5 h-5" />,    stepNum: 1 },
    { id: 'mapping',      name: 'Variable Map',         icon: <Grid className="w-5 h-5" />,      stepNum: 2 },
    { id: 'hierarchy',    name: 'Hierarchy Builder',    icon: <Network className="w-5 h-5" />,   stepNum: 3 },
    { id: 'analysis',     name: 'Data Analysis',        icon: <BarChart2 className="w-5 h-5" />, stepNum: 4 },
    { id: 'enrichment',   name: 'Enrichment',           icon: <Zap className="w-5 h-5" />,       stepNum: 5 },
    { id: 'readiness',    name: 'Readiness',            icon: <FileDigit className="w-5 h-5" />, stepNum: 6 },
    { id: 'verification', name: 'Compound Explorer',    icon: <CheckSquare className="w-5 h-5" />, stepNum: 7 },
    { id: 'reports',      name: 'Export',               icon: <Download className="w-5 h-5" />,  stepNum: 8 },
  ];

  const currentStep = sidebarItems.find(i => i.id === activeTab);

  return (
    <Tooltip.Provider delayDuration={200}>
      <div className="flex h-screen bg-void text-primary font-sans overflow-hidden selection:bg-cyan-500/30">
        
        {/* Floating Sidebar */}
        <motion.aside
          initial={false}
          animate={{ width: collapsed ? 88 : 280 }}
          className="relative flex flex-col glass-elevated my-4 ml-4 mr-4 rounded-2xl shrink-0 z-20 overflow-hidden"
          onHoverStart={() => setCollapsed(false)}
          onHoverEnd={() => setCollapsed(true)}
        >
          {/* Header */}
          <div className="flex items-center h-24 px-4 border-b border-white/[0.06] shrink-0 gap-4">
            <div className="shrink-0 cursor-pointer" onClick={onGoHome}>
              <LogoLoader size="w-14 h-14" compact />
            </div>
            <AnimatePresence>
              {!collapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  className="whitespace-nowrap min-w-0"
                >
                  <p className="font-extrabold tracking-[0.2em] text-2xl text-white leading-none">SUTRIX</p>
                  <p className="text-[10px] font-semibold tracking-[0.15em] text-white/40 uppercase mt-1">SDO Platform</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Nav Items */}
          <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
            {sidebarItems.map((item) => {
              const isActive = activeTab === item.id;
              
              const ButtonContent = (
                <button
                  id={`sidebar-tab-${item.id}`}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center h-12 rounded-xl transition-all duration-200 group relative
                    ${collapsed ? 'justify-center' : 'justify-start'}
                    ${isActive ? 'bg-white/[0.08] text-white' : 'text-secondary hover:bg-white/[0.04] hover:text-white'}
                  `}
                >
                  {isActive && (
                    <motion.div 
                      layoutId="activeTabIndicator"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-cyan-400 rounded-r-full"
                    />
                  )}
                  <div className="w-12 h-12 flex items-center justify-center shrink-0">
                    <span className={isActive ? 'text-cyan-400' : 'group-hover:text-cyan-400/70 transition-colors'}>
                      {item.icon}
                    </span>
                  </div>
                  <AnimatePresence>
                    {!collapsed && (
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex-1 flex items-center justify-between pr-3 overflow-hidden"
                      >
                        <span className="font-medium text-sm truncate">{item.name}</span>
                        {isActive && <span className="text-[10px] bg-cyan-400/20 text-cyan-400 px-2 py-0.5 rounded-full">S{item.stepNum}</span>}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </button>
              );

              return collapsed ? (
                <Tooltip.Root key={item.id}>
                  <Tooltip.Trigger asChild>
                    {ButtonContent}
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content 
                      side="right" 
                      sideOffset={16}
                      className="glass px-3 py-1.5 rounded-lg text-xs font-medium text-white shadow-xl animate-in fade-in zoom-in-95 z-50"
                    >
                      {item.name}
                      <Tooltip.Arrow className="fill-[rgba(10,15,30,0.8)]" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              ) : (
                <div key={item.id}>{ButtonContent}</div>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-white/[0.06] space-y-1 shrink-0">
            {/* System Monitor — utility shortcut, not a workflow step */}
            <Tooltip.Root>
              <Tooltip.Trigger asChild>
                <button
                  onClick={() => onOpenSystem ? onOpenSystem() : setActiveTab('benchmark')}
                  className={`w-full flex items-center h-12 rounded-xl transition-colors
                    ${collapsed ? 'justify-center' : 'justify-start'}
                    ${activeTab === 'benchmark' ? 'bg-white/[0.08] text-white' : 'text-secondary hover:bg-white/[0.04] hover:text-white'}
                  `}
                >
                  <div className="w-12 h-12 flex items-center justify-center shrink-0">
                    <Activity className={`w-5 h-5 ${activeTab === 'benchmark' ? 'text-cyan-400' : ''}`} />
                  </div>
                  <AnimatePresence>
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="font-medium text-sm truncate"
                      >
                        System Monitor
                      </motion.span>
                    )}
                  </AnimatePresence>
                </button>
              </Tooltip.Trigger>
              {collapsed && (
                <Tooltip.Portal>
                  <Tooltip.Content side="right" sideOffset={16}
                    className="glass px-3 py-1.5 rounded-lg text-xs font-medium text-white shadow-xl animate-in fade-in zoom-in-95 z-50"
                  >
                    System Monitor
                    <Tooltip.Arrow className="fill-[rgba(10,15,30,0.8)]" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              )}
            </Tooltip.Root>
            <button 
              onClick={onOpenLicense}
              className={`w-full flex items-center h-12 rounded-xl text-secondary hover:bg-white/[0.04] hover:text-white transition-colors
                ${collapsed ? 'justify-center' : 'justify-start'}
              `}
            >
              <div className="w-12 h-12 flex items-center justify-center shrink-0"><Scale className="w-5 h-5 text-cyan-400" /></div>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span 
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="font-bold text-xs truncate tracking-wider text-cyan-400"
                  >
                    AGPL-3.0 License
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
            <button 
              onClick={onExit}
              className={`w-full flex items-center h-12 rounded-xl text-rose-500/80 hover:bg-rose-500/10 hover:text-rose-500 transition-colors
                ${collapsed ? 'justify-center' : 'justify-start'}
              `}
            >
              <div className="w-12 h-12 flex items-center justify-center shrink-0"><LogOut className="w-5 h-5" /></div>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span 
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    className="font-medium text-sm truncate whitespace-nowrap"
                  >
                    Exit Workspace
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
          </div>
        </motion.aside>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col min-w-0 relative h-full overflow-hidden">
          {/* Topbar */}
          <header className="h-16 shrink-0 flex items-center justify-between px-6 z-10 border-b border-white/[0.04]">
            <div className="flex items-center gap-4">
              <div className="text-secondary text-sm font-medium flex items-center gap-2">
                <span className="text-white/30 text-xs">Step {currentStep?.stepNum || 1} / 8</span>
                <span className="text-white/[0.15]">&bull;</span> 
                <span className="text-white font-semibold">{currentStep?.name || activeTab}</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {telemetryData.active_jobs_count > 0 && (
                <div className="px-3 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-xs font-medium flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-violet-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-violet-500"></span>
                  </span>
                  Processing
                </div>
              )}
              
              <div className="px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06] text-xs font-mono text-secondary flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${telemetryData.ram_usage_pct > 80 ? 'bg-rose-500' : 'bg-emerald-500'}`} />
                RAM {telemetryData.ram_usage_pct}%
              </div>

              <button 
                onClick={() => setShowHelp(!showHelp)}
                className="w-8 h-8 rounded-full bg-white/[0.03] border border-white/[0.06] flex items-center justify-center text-secondary hover:text-white hover:bg-white/[0.06] transition-all"
              >
                <HelpCircle className="w-4 h-4" />
              </button>
            </div>
          </header>

          {/* Content Area — fullscreen for hierarchy/analysis tabs, padded scroll for others */}
          {FULLSCREEN_TABS.has(activeTab) ? (
            <div className="flex-1 overflow-hidden">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                  className="h-full"
                >
                  {children}
                </motion.div>
              </AnimatePresence>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto">
              <div className="px-8 py-8 pb-16 max-w-6xl mx-auto">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={activeTab}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.2 }}
                  >
                    {children}
                  </motion.div>
                </AnimatePresence>
              </div>
            </div>
          )}
        </main>

      </div>
    </Tooltip.Provider>
  );
};
