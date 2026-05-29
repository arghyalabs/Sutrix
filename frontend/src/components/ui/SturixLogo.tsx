import React from 'react';
import { motion } from 'framer-motion';

export const SturixLogo: React.FC<{ className?: string; isSpinning3D?: boolean }> = ({ className = "w-8 h-8", isSpinning3D = false }) => {
  return (
    <motion.div 
      className={`relative flex items-center justify-center ${className}`}
      animate={isSpinning3D ? { rotateX: 360, rotateY: 360, rotateZ: 180 } : {}}
      transition={isSpinning3D ? { duration: 3, repeat: Infinity, ease: "linear" } : {}}
      style={{ transformStyle: 'preserve-3d', perspective: 1000 }}
    >
      <motion.svg 
        viewBox="0 0 100 100" 
        className="w-full h-full drop-shadow-[0_0_15px_rgba(34,211,238,0.5)]"
        initial="hidden"
        animate="visible"
      >
        <defs>
          <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#22d3ee" /> {/* cyan-400 */}
            <stop offset="100%" stopColor="#8b5cf6" /> {/* violet-500 */}
          </linearGradient>
          <linearGradient id="line-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="rgba(34,211,238,0.6)" />
            <stop offset="100%" stopColor="rgba(139,92,246,0.6)" />
          </linearGradient>
        </defs>

        {/* Connections */}
        <motion.path
          d="M 25 45 L 75 25 L 60 75 L 25 45 Z"
          fill="none"
          stroke="url(#line-grad)"
          strokeWidth="3"
          strokeLinejoin="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 2, ease: "easeInOut" }}
        />
        <motion.line
          x1="25" y1="45" x2="60" y2="75"
          stroke="url(#line-grad)"
          strokeWidth="3"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 2, ease: "easeInOut", delay: 0.2 }}
        />
        <motion.line
          x1="50" y1="50" x2="75" y2="25"
          stroke="url(#line-grad)"
          strokeWidth="3"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ duration: 2, ease: "easeInOut", delay: 0.4 }}
        />

        {/* Nodes */}
        {/* Node 1: Left */}
        <motion.circle
          cx="25" cy="45" r="8"
          fill="url(#logo-grad)"
          animate={{ y: [0, -3, 0], scale: [1, 1.1, 1] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* Node 2: Top Right */}
        <motion.circle
          cx="75" cy="25" r="10"
          fill="url(#logo-grad)"
          animate={{ y: [0, 4, 0], scale: [1, 1.05, 1] }}
          transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        />
        {/* Node 3: Bottom Right */}
        <motion.circle
          cx="60" cy="75" r="9"
          fill="url(#logo-grad)"
          animate={{ y: [0, -4, 0], scale: [1, 1.1, 1] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1 }}
        />
        {/* Node 4: Center */}
        <motion.circle
          cx="50" cy="50" r="12"
          fill="url(#logo-grad)"
          animate={{ y: [0, 2, 0], scale: [1, 1.05, 1] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
        />

      </motion.svg>
    </motion.div>
  );
};
