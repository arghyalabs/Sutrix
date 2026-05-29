import React from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { OptimizedPlotly } from './OptimizedPlotly';

export const VisualizationWorkspace: React.FC<{ pcaData: any }> = ({ pcaData }) => {
  // Guard: pcaData must be an object with a .data array to be renderable
  const isValid = pcaData && typeof pcaData === 'object' && !Array.isArray(pcaData) && Array.isArray(pcaData.data);
  if (!isValid) return (
    <div className="flex items-center justify-center h-64 text-secondary text-sm">
      No visualization data available for this audit run.
    </div>
  );

  return (
    <Tabs.Root defaultValue="pca" className="flex flex-col w-full h-[600px]">
      <Tabs.List className="flex border-b border-white/[0.06] bg-white/[0.02]">
        <Tabs.Trigger 
          value="pca"
          className="px-6 py-4 text-sm font-medium text-secondary data-[state=active]:text-cyan-400 data-[state=active]:border-b-2 data-[state=active]:border-cyan-400 hover:text-white transition-colors outline-none"
        >
          3D PCA Map
        </Tabs.Trigger>
        <Tabs.Trigger 
          value="umap"
          className="px-6 py-4 text-sm font-medium text-secondary data-[state=active]:text-violet-400 data-[state=active]:border-b-2 data-[state=active]:border-violet-400 hover:text-white transition-colors outline-none"
        >
          UMAP Projection
        </Tabs.Trigger>
      </Tabs.List>

      <Tabs.Content value="pca" className="flex-1 outline-none relative bg-[#050816]">
        <div className="absolute inset-0">
          <OptimizedPlotly data={pcaData.data} layout={pcaData.layout} useGL={true} />
        </div>
      </Tabs.Content>
      
      <Tabs.Content value="umap" className="flex-1 flex items-center justify-center outline-none bg-[#050816]">
        <div className="text-secondary text-sm">UMAP visualization not generated in this audit run.</div>
      </Tabs.Content>
    </Tabs.Root>
  );
};
