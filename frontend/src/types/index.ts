export type JobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface JobTelemetry {
  progress_pct: number;
  eta_seconds: number;
  compounds_per_sec: number;
  elapsed_seconds: number;
  phase: string;
  logs: string[];
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  eta_seconds: number;
  compounds_per_sec: number;
  result_path: string | null;
  error_message: string | null;
  created_at: number;
  completed_at: number | null;
}

export interface SystemTelemetry {
  total_ram_gb: number;
  available_ram_gb: number;
  ram_usage_pct: number;
  current_process_ram_mb: number;
  child_processes_ram_mb: number;
  is_critical: boolean;
  is_locked: boolean;
  cache_hit_rate_pct: number;
  total_cached_compounds: number;
  active_jobs_count: number;
}

export interface CompoundPreviewRow {
  [key: string]: string | number | boolean | null;
}

export interface DatasetIngestResponse {
  success: boolean;
  filename: string;
  row_count: number;
  columns: string[];
  preview: CompoundPreviewRow[];
  parquet_path: string;
}

export interface VariableMappings {
  [columnName: string]: 'chemical_name' | 'chemical_id' | 'cas_number' | 'canonical_smiles' | 'endpoint' | 'value' | 'unit' | 'qualifier' | 'species' | 'duration' | 'route' | 'study_type' | 'none';
}

export interface ReadinessResponse {
  score: number;
  tier: string;
  breakdown: {
    missing_values: number;
    structural_completeness: number;
    variance_quality: number;
    sample_size: number;
    class_balance: number;
    duplicate_ratio: number;
    endpoint_uniformity: number;
  };
  deductions: string[];
  harmonized: boolean;
  findings: any[];
  pca?: any;
}

// ── Modeling Readiness Workspace types ──────────────────────────────────────

export interface OECDCheck {
  principle: number;
  name: string;
  status: boolean;
  evidence: string;
}

export interface DescriptorReadiness {
  category: string;
  count: number;
  completeness: number;
  recommendation: string;
}

export interface FeatureRecommendation {
  id: string;
  action: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  affected_columns: string[];
  affected_count: number;
  reasoning: string;
  expected_impact: string;
  auto_applicable: boolean;
  code_hint?: string;
}

export interface ModelRecommendation {
  algorithm: string;
  category: string;
  suitability_score: number;
  pros: string[];
  cons: string[];
  expected_robustness: 'HIGH' | 'MEDIUM' | 'LOW';
  scientific_reasoning: string;
  unsupervised: boolean;
}

export interface Risk {
  risk: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  probability: number;
  impact: string;
  mitigation: string;
  affected_stage: string;
}

export interface Anomaly {
  type: string;
  severity: string;
  affected_rows: number;
  description: string;
  suggested_action: string;
}

export interface QualityFunnelPoint {
  stage: string;
  count: number;
}

export interface ModelingAnalysis {
  readiness: {
    ai_score: number;
    qsar_score: number;
    stability_score: number;
    integrity_score: number;
    confidence_tier: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT';
    breakdown: Record<string, number>;
    deductions: string[];
    tier: string;
    diversity_score: number;
    descriptor_reliability_score: number;
    baseline_performance: number;
    success_confidence: string;
    n_samples: number;
    n_features: number;
    n_to_p_ratio: number;
  };
  feasibility: {
    axes: string[];
    values: number[];
    confidence_lower: number[];
    confidence_upper: number[];
    interpretation: string;
    mean_score: number;
  };
  qsar: {
    oecd_checks: OECDCheck[];
    descriptor_readiness: DescriptorReadiness[];
    endpoint_status: { harmonized: boolean; findings: any[] };
    overall_oecd_tier: string;
    oecd_pass_count: number;
  };
  features: FeatureRecommendation[];
  models: ModelRecommendation[];
  quality: {
    anomalies: Anomaly[];
    funnel: QualityFunnelPoint[];
    health_score: number;
    recommendations: string[];
  };
  risks: Risk[];
  visualizations: {
    missing_heatmap?: { z: number[][]; x: string[]; y: number[] };
    endpoint_distribution?: { values: number[]; bin_edges: number[]; counts: number[] };
    variance_data?: { names: string[]; variances: number[] };
    class_balance?: { labels: string[]; counts: number[] };
    correlation_matrix?: { z: number[][]; labels: string[] };
    outliers?: { x: number[]; y: number[]; x_label: string; y_label: string; is_outlier: boolean[] };
  };
  meta: { elapsed_seconds: number; n_samples: number; n_features: number; analysis_timestamp: number };
}

