import React from 'react';
import { OptimizedPlotly } from './OptimizedPlotly';

export const PCAViewer: React.FC<{ data: any }> = ({ data }) => {
  if (!data) return null;
  return (
    <div className="w-full h-full min-h-[500px] glass rounded-3xl overflow-hidden relative">
      <div className="absolute inset-0 bg-[#050816]">
        <OptimizedPlotly data={data.data} layout={data.layout} useGL={true} />
      </div>
    </div>
  );
};
