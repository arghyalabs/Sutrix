import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CompoundPreviewRow, VariableMappings, ReadinessResponse, ModelingAnalysis } from '../types';

interface WorkspaceState {
  // Navigation
  inWorkspace: boolean;
  activeTab: string;

  // Pipeline Dataset
  workspaceId: string;
  filename: string;
  parquetPath: string;
  rowCount: number;
  columns: string[];
  preview: CompoundPreviewRow[];

  // Mappings
  mappings: VariableMappings;
  mappingIntelligence: Record<string, { confidence: number; reasons: string[]; ecotox?: any }>;

  // Segregation / Hierarchy
  segStats: any;
  segregationExecuted: boolean;
  activeSegregationResult: any;
  activeLineage: any;
  activeNodeId: string;
  activeNodeDetail: any;

  // Enrichment
  enrichmentMode: 'fast' | 'standard' | 'full';
  includeMordred: boolean;
  selectedDescriptors: string[];
  activeJobId: string;
  activeJobType: 'segregation' | 'enrichment' | null;

  // Readiness (legacy)
  readiness: ReadinessResponse | null;
  readinessLoading: boolean;

  // Modeling Readiness Workspace
  modelingAnalysis: ModelingAnalysis | null;
  modelingLoading: boolean;
  modelingActivePanel: string;

  // Setters
  setWorkspaceId: (id: string) => void;
  setInWorkspace: (inWS: boolean) => void;
  setActiveTab: (tab: string) => void;
  setDataset: (filename: string, parquetPath: string, rowCount: number, columns: string[], preview: CompoundPreviewRow[]) => void;
  setMappings: (mappings: VariableMappings) => void;
  setMappingIntelligence: (intel: Record<string, { confidence: number; reasons: string[]; ecotox?: any }>) => void;
  setSegregation: (stats: any, executed: boolean) => void;
  setActiveSegregationResult: (res: any) => void;
  setActiveLineage: (lineage: any) => void;
  setActiveNodeId: (id: string) => void;
  setActiveNodeDetail: (detail: any) => void;
  setEnrichmentMode: (mode: 'fast' | 'standard' | 'full') => void;
  setIncludeMordred: (include: boolean) => void;
  setSelectedDescriptors: (descriptors: string[]) => void;
  setActiveJobId: (jobId: string) => void;
  setActiveJobType: (type: 'segregation' | 'enrichment' | null) => void;
  setReadiness: (readiness: ReadinessResponse | null) => void;
  setReadinessLoading: (loading: boolean) => void;
  setModelingAnalysis: (data: ModelingAnalysis | null) => void;
  setModelingLoading: (loading: boolean) => void;
  setModelingActivePanel: (panel: string) => void;
  resetWorkspace: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      inWorkspace: false,
      activeTab: 'ingest',

      workspaceId: '',
      filename: '',
      parquetPath: '',
      rowCount: 0,
      columns: [],
      preview: [],

      mappings: {},
      mappingIntelligence: {},

      segStats: {},
      segregationExecuted: false,
      activeSegregationResult: null,
      activeLineage: null,
      activeNodeId: '',
      activeNodeDetail: null,

      enrichmentMode: 'fast',
      includeMordred: false,
      selectedDescriptors: [],
      activeJobId: '',
      activeJobType: null,

      readiness: null,
      readinessLoading: false,

      modelingAnalysis: null,
      modelingLoading: false,
      modelingActivePanel: 'overview',

      setWorkspaceId: (id) => set({ workspaceId: id }),
      setInWorkspace: (inWS) => set({ inWorkspace: inWS }),
      setActiveTab: (tab) => {
        if (typeof window !== 'undefined' && window.location.hash !== `#${tab}`) {
          window.history.pushState(null, '', `#${tab}`);
        }
        set({ activeTab: tab });
      },
      setDataset: (filename, parquetPath, rowCount, columns, preview) =>
        set({ filename, parquetPath, rowCount, columns, preview }),
      setMappings: (mappings) => set({ mappings }),
      setMappingIntelligence: (intel) => set({ mappingIntelligence: intel }),
      setSegregation: (stats, executed) => set({ segStats: stats, segregationExecuted: executed }),
      setActiveSegregationResult: (res) => set({ activeSegregationResult: res }),
      setActiveLineage: (lineage) => set({ activeLineage: lineage }),
      setActiveNodeId: (id) => set({ activeNodeId: id }),
      setActiveNodeDetail: (detail) => set({ activeNodeDetail: detail }),
      setEnrichmentMode: (mode) => set({ enrichmentMode: mode }),
      setIncludeMordred: (include) => set({ includeMordred: include }),
      setSelectedDescriptors: (descriptors) => set({ selectedDescriptors: descriptors }),
      setActiveJobId: (jobId) => set({ activeJobId: jobId }),
      setActiveJobType: (type) => set({ activeJobType: type }),
      setReadiness: (readiness) => set({ readiness }),
      setReadinessLoading: (loading) => set({ readinessLoading: loading }),
      setModelingAnalysis: (data) => set({ modelingAnalysis: data }),
      setModelingLoading: (loading) => set({ modelingLoading: loading }),
      setModelingActivePanel: (panel) => set({ modelingActivePanel: panel }),

      resetWorkspace: () =>
        set({
          workspaceId: '', filename: '', parquetPath: '', rowCount: 0,
          columns: [], preview: [], mappings: {}, mappingIntelligence: {},
          segStats: {}, segregationExecuted: false, activeSegregationResult: null,
          activeLineage: null, activeNodeId: '', activeNodeDetail: null,
          enrichmentMode: 'fast', includeMordred: false, selectedDescriptors: [],
          activeJobId: '', activeJobType: null, readiness: null, readinessLoading: false,
          modelingAnalysis: null, modelingLoading: false, modelingActivePanel: 'overview',
          activeTab: 'ingest',
        }),
    }),
    { 
      name: 'sdo-workspace-storage-v2',
      version: 2,
      migrate: (persistedState: any, version: number) => {
        // Always clear stale job tracking state across versions
        return {
          ...persistedState,
          activeJobId: '',
          activeJobType: null,
        };
      },
    }
  )
);
