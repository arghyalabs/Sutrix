import React, { useRef, useMemo, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Html } from '@react-three/drei';
import * as THREE from 'three';
import { Maximize2, Minimize2, Layers, FlaskConical, Target, Shield, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface PointData {
  x: number; y: number; z: number;
  compound_id: string;
  endpoint: string;
  species: string;
  readiness_score: number;
  outlier_score: number;
  cluster_id: number;
  is_outlier: boolean;
}

interface Props {
  data: PointData[];
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

type ViewMode = 'CHEMICAL_SPACE' | 'APPLICABILITY_DOMAIN' | 'OUTLIERS' | 'VARIANCE' | 'CLUSTERS';

const MODES = [
  { id: 'CHEMICAL_SPACE', label: 'Chemical Space', icon: Layers },
  { id: 'APPLICABILITY_DOMAIN', label: 'Applicability Domain', icon: Shield },
  { id: 'OUTLIERS', label: 'Outlier Landscape', icon: Target },
  { id: 'VARIANCE', label: 'Descriptor Variance', icon: Activity },
  { id: 'CLUSTERS', label: 'Endpoint Clusters', icon: FlaskConical },
];

const CLUSTER_COLORS = [
  new THREE.Color('#38bdf8'), // light blue
  new THREE.Color('#818cf8'), // indigo
  new THREE.Color('#34d399'), // emerald
  new THREE.Color('#f472b6'), // pink
  new THREE.Color('#fbbf24'), // amber
];

const PointsCloud: React.FC<{ data: PointData[]; mode: ViewMode; onHover: (p: PointData | null, e: any) => void }> = ({ data, mode, onHover }) => {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const hoverIdx = useRef<number | null>(null);

  const dummy = useMemo(() => new THREE.Object3D(), []);
  const color = useMemo(() => new THREE.Color(), []);

  // Use memo to prevent re-calculating colors every frame
  const targetColors = useMemo(() => {
    return data.map(p => {
      let c = new THREE.Color();
      if (mode === 'CHEMICAL_SPACE') {
        c.set('#22d3ee'); // cyan default
      } else if (mode === 'APPLICABILITY_DOMAIN') {
        c.set(p.readiness_score > 0.6 ? '#10b981' : '#f59e0b');
      } else if (mode === 'OUTLIERS') {
        c.set(p.is_outlier ? '#ef4444' : '#334155');
      } else if (mode === 'VARIANCE') {
        c.set(p.outlier_score > 0.5 ? '#a855f7' : '#0ea5e9');
      } else if (mode === 'CLUSTERS') {
        c = CLUSTER_COLORS[p.cluster_id % CLUSTER_COLORS.length];
      }
      return c;
    });
  }, [data, mode]);

  const targetSizes = useMemo(() => {
    return data.map(p => {
      if (mode === 'OUTLIERS' && p.is_outlier) return 3.0;
      if (mode === 'APPLICABILITY_DOMAIN' && p.readiness_score < 0.4) return 0.5;
      return 1.0;
    });
  }, [data, mode]);

  useFrame((state) => {
    if (!meshRef.current) return;
    
    // Slow rotation
    meshRef.current.rotation.y += 0.001;

    for (let i = 0; i < data.length; i++) {
      const p = data[i];
      dummy.position.set(p.x, p.y, p.z);
      
      const isHovered = hoverIdx.current === i;
      const targetScale = isHovered ? targetSizes[i] * 2.5 : targetSizes[i];
      
      dummy.scale.setScalar(targetScale);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      // Interpolate color slowly for smooth transitions
      color.copy(targetColors[i]);
      if (isHovered) color.set('#ffffff'); // Highlight hovered
      
      meshRef.current.setColorAt(i, color);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) meshRef.current.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, data.length]}
      onPointerMove={(e) => {
        e.stopPropagation();
        if (e.instanceId !== undefined) {
          hoverIdx.current = e.instanceId;
          onHover(data[e.instanceId], e);
        }
      }}
      onPointerOut={(e) => {
        hoverIdx.current = null;
        onHover(null, e);
      }}
    >
      <sphereGeometry args={[0.08, 16, 16]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
};

export const ChemicalSpace3D: React.FC<Props> = ({ data, isFullscreen, onToggleFullscreen }) => {
  const [mode, setMode] = useState<ViewMode>('CHEMICAL_SPACE');
  const [hoverData, setHoverData] = useState<{ point: PointData; x: number; y: number } | null>(null);

  const handleHover = (point: PointData | null, e: any) => {
    if (point) {
      setHoverData({ point, x: e.clientX, y: e.clientY });
    } else {
      setHoverData(null);
    }
  };

  return (
    <div className={`relative flex flex-col bg-[#050B14] rounded-2xl overflow-hidden border border-white/[0.05] ${isFullscreen ? 'fixed inset-0 z-50 rounded-none border-none' : 'h-[500px] w-full'}`}>
      
      {/* ── Toolbar ── */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-4 bg-gradient-to-b from-[#050B14] to-transparent">
        <div className="flex gap-2">
          {MODES.map(m => {
            const isActive = mode === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setMode(m.id as ViewMode)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive 
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' 
                    : 'bg-white/[0.03] text-white/50 border border-white/[0.05] hover:bg-white/[0.08]'
                }`}
              >
                <m.icon className="w-3.5 h-3.5" />
                {m.label}
              </button>
            );
          })}
        </div>
        
        {onToggleFullscreen && (
          <button 
            onClick={onToggleFullscreen}
            className="p-2 rounded-lg bg-white/[0.03] border border-white/[0.05] text-white/50 hover:text-white"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        )}
      </div>

      {/* ── Legend ── */}
      <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
        <div className="rounded-xl border border-white/[0.05] bg-white/[0.02] backdrop-blur-md p-3 max-w-[200px]">
          <h4 className="text-[10px] font-bold text-white/50 uppercase tracking-wider mb-2">View Legend</h4>
          <div className="space-y-1.5">
            {mode === 'APPLICABILITY_DOMAIN' && (
              <>
                <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-emerald-500" /> High Confidence</div>
                <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-amber-500" /> Low Confidence</div>
              </>
            )}
            {mode === 'OUTLIERS' && (
              <>
                <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-red-500" /> Outlier</div>
                <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-slate-600" /> Normal</div>
              </>
            )}
            {mode === 'CHEMICAL_SPACE' && (
              <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-cyan-400" /> Descriptor Space (PCA)</div>
            )}
            {mode === 'CLUSTERS' && (
              <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-indigo-400" /> Structural Similarity</div>
            )}
            {mode === 'VARIANCE' && (
              <div className="flex items-center gap-2 text-xs text-white/60"><div className="w-2 h-2 rounded-full bg-purple-500" /> High Variance Component</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Stats overlay ── */}
      <div className="absolute bottom-4 right-4 z-10 pointer-events-none text-right">
        <div className="text-3xl font-light text-white/80 tabular-nums">{data.length}</div>
        <div className="text-[10px] uppercase tracking-widest text-white/30 font-semibold">Compounds Rendered</div>
      </div>

      {/* ── Tooltip ── */}
      <AnimatePresence>
        {hoverData && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="fixed z-50 pointer-events-none"
            style={{ left: hoverData.x + 15, top: hoverData.y + 15 }}
          >
            <div className="rounded-xl border border-white/[0.1] bg-[#0A1220]/95 backdrop-blur-xl p-3 shadow-2xl min-w-[200px]">
              <div className="flex items-center justify-between mb-2 pb-2 border-b border-white/[0.05]">
                <div className="font-mono text-xs font-bold text-cyan-400">{hoverData.point.compound_id}</div>
                {hoverData.point.is_outlier && <div className="text-[9px] font-bold bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded">OUTLIER</div>}
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                <div className="text-white/40">Endpoint:</div><div className="text-white/90 text-right">{hoverData.point.endpoint}</div>
                <div className="text-white/40">Species:</div><div className="text-white/90 text-right">{hoverData.point.species}</div>
                <div className="text-white/40">Readiness:</div>
                <div className="text-right font-mono" style={{ color: hoverData.point.readiness_score > 0.6 ? '#10b981' : '#f59e0b' }}>
                  {(hoverData.point.readiness_score * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── WebGL Canvas ── */}
      <div className="flex-1 cursor-move">
        <Canvas camera={{ position: [0, 0, 8], fov: 45 }}>
          <color attach="background" args={['#050B14']} />
          <fog attach="fog" args={['#050B14', 5, 20]} />
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={1} color="#22d3ee" />
          <pointLight position={[-10, -10, -10]} intensity={0.5} color="#c084fc" />
          
          <Stars radius={50} depth={50} count={3000} factor={4} saturation={0} fade speed={0.5} />
          
          {/* Grid Floor */}
          <gridHelper args={[20, 20, '#1e293b', '#0f172a']} position={[0, -4, 0]} />

          <PointsCloud data={data} mode={mode} onHover={handleHover} />
          
          <OrbitControls 
            enablePan={false}
            enableZoom={true}
            minDistance={2}
            maxDistance={15}
            dampingFactor={0.05}
          />
        </Canvas>
      </div>
    </div>
  );
};
