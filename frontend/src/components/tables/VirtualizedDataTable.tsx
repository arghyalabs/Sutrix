import React, { useState, useMemo } from 'react';
// @ts-ignore
import { FixedSizeList as List } from 'react-window';
import { Search } from 'lucide-react';

interface VirtualizedDataTableProps {
  data: any[];
  columns: string[];
  height?: number;
}

export const VirtualizedDataTable: React.FC<VirtualizedDataTableProps> = ({ 
  data, 
  columns, 
  height = 400 
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredData = useMemo(() => {
    if (!searchTerm) return data;
    const lowerTerm = searchTerm.toLowerCase();
    return data.filter(row => 
      columns.some(col => String(row[col] || '').toLowerCase().includes(lowerTerm))
    );
  }, [data, columns, searchTerm]);

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const row = filteredData[index];
    return (
      <div 
        style={style} 
        className="flex items-center border-b border-white/[0.02] hover:bg-white/[0.02] transition-colors"
      >
        {columns.map(col => (
          <div 
            key={col} 
            className="flex-1 px-4 py-3 text-sm text-white/80 whitespace-nowrap overflow-hidden text-ellipsis"
            title={String(row[col])}
          >
            {String(row[col])}
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="glass rounded-2xl overflow-hidden border-white/[0.06] flex flex-col h-[500px]">
      <div className="p-4 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.01]">
        <h4 className="text-sm font-semibold text-white">Dataset Viewer ({filteredData.length})</h4>
        <div className="relative w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search rows..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg pl-9 pr-4 py-1.5 text-xs text-white placeholder-muted focus:outline-none focus:border-cyan-500/50 transition-colors"
          />
        </div>
      </div>
      
      <div className="flex bg-white/[0.02] border-b border-white/[0.06]">
        {columns.map(col => (
          <div key={col} className="flex-1 px-4 py-3 text-xs font-semibold text-secondary uppercase tracking-wider whitespace-nowrap overflow-hidden text-ellipsis">
            {col}
          </div>
        ))}
      </div>

      <div className="flex-1 relative">
        {filteredData.length > 0 ? (
          <List
            height={height - 100}
            itemCount={filteredData.length}
            itemSize={44}
            width="100%"
          >
            {Row}
          </List>
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-muted">
            No matching records found.
          </div>
        )}
      </div>
    </div>
  );
};
