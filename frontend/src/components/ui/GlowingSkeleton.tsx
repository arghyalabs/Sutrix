
export const GlowingSkeleton = ({ className = "" }) => (
  <div className={`relative overflow-hidden rounded-xl bg-white/[0.02] ${className}`}>
    <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/[0.05] to-transparent animate-[shimmer_2s_infinite]" />
  </div>
);
