import React from 'react';
import { HeroSection } from './HeroSection';
import { WorkflowTimeline } from './WorkflowTimeline';
import { DatasetTransformation } from './DatasetTransformation';
import { FeatureExplorer } from './FeatureExplorer';
import { HierarchyVisualizer } from './HierarchyVisualizer';
import { AIReadinessPreview } from './AIReadinessPreview';
import { ExportVisualization } from './ExportVisualization';
import { TechStrip } from './TechStrip';
import { FinalCTA } from './FinalCTA';

interface LandingPageProps {
  onLaunch: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunch }) => {
  return (
    <div className="min-h-screen bg-[#03070f] text-white font-sans overflow-x-hidden selection:bg-cyan-500/20">
      {/* Section 1: Hero */}
      <HeroSection onLaunch={onLaunch} />

      {/* Section 2: Interactive Workflow Timeline */}
      <WorkflowTimeline />

      {/* Section 3: Live Dataset Transformation */}
      <DatasetTransformation />

      {/* Section 4: Feature Explorer */}
      <FeatureExplorer />

      {/* Section 5: Hierarchy Engine Visualizer */}
      <HierarchyVisualizer />

      {/* Section 6: AI/QSAR Readiness Preview */}
      <AIReadinessPreview />

      {/* Section 7: Export System Visualization */}
      <ExportVisualization />

      {/* Section 8: Tech Strip */}
      <TechStrip />

      {/* Section 9: Final CTA */}
      <FinalCTA onLaunch={onLaunch} />
    </div>
  );
};
