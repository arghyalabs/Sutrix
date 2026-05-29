import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import math

from backend.validation.endpoint_validator import EndpointValidator

@dataclass
class AuditFinding:
    """Represents a single audit finding."""
    category: str
    severity: str  # 'critical', 'warning', 'info'
    description: str
    affected_records: int
    details: dict

@dataclass
class VarianceSummary:
    """Summary of log10 variance audit results."""
    consistent_count: int      # Groups with Range < 0.5
    moderate_count: int        # Groups with 0.5 <= Range < 1.0
    conflict_count: int        # Groups with Range >= 1.0
    conflict_compounds: list   # List of dicts with compound details
    consistency_score: float   # Percentage of groups that passed (Range < 1.0)
    total_groups_analyzed: int

@dataclass
class AuditReport:
    """Complete audit report."""
    dataset_id: str
    total_records: int
    total_columns: int
    findings: List[AuditFinding]
    quality_score: float
    data_health_tier: str # 'High Quality (Green)', 'Moderate Quality (Yellow)', 'Critical/Low Quality (Red)'
    summary: dict
    variance_summary: Optional[VarianceSummary] = None

class ScientificAuditor:
    """Performs comprehensive audit of scientific datasets."""
    
    def __init__(self):
        self.findings: List[AuditFinding] = []
        self.endpoint_validator = EndpointValidator()
        
    def audit(self, df: pd.DataFrame, 
              column_mappings: dict,
              dataset_id: str = "unknown") -> AuditReport:
        """Run complete audit on dataset."""
        self.findings = []
        
        # Invert column_mappings to lookup by scientific variable
        # For this logic, we assume column_mappings is {user_col: scientific_var}
        sci_to_user = {v: k for k, v in column_mappings.items()}
        
        # Run checks
        missing_pct_max = self._check_missing_values(df)
        self._check_endpoint_consistency(df, sci_to_user)
        variance_penalty = self._check_log10_variance(df, sci_to_user)
        
        # Calculate quality score and tier
        quality_score = self._calculate_quality_score(df, missing_pct_max, variance_penalty)
        data_health_tier = self._determine_health_tier(missing_pct_max)
        
        # Generate summary
        summary = {
            'total_findings': len(self.findings),
            'critical_findings': len([f for f in self.findings if f.severity == 'critical']),
            'warning_findings': len([f for f in self.findings if f.severity == 'warning']),
            'info_findings': len([f for f in self.findings if f.severity == 'info']),
            'max_missing_pct': missing_pct_max,
            'variance_penalty_applied': variance_penalty
        }
        
        return AuditReport(
            dataset_id=dataset_id,
            total_records=len(df),
            total_columns=len(df.columns),
            findings=self.findings,
            quality_score=quality_score,
            data_health_tier=data_health_tier,
            summary=summary
        )
    
    def _check_missing_values(self, df: pd.DataFrame) -> float:
        """
        Check for missing values in each column.
        Returns the maximum missing percentage across mapped columns to inform overall health tier.
        """
        missing_counts = df.isnull().sum()
        total = len(df)
        
        if total == 0:
            return 0.0
            
        max_missing_pct = 0.0
        
        for col, count in missing_counts.items():
            pct = (count / total) * 100
            if pct > 0:
                max_missing_pct = max(max_missing_pct, pct)
                # Apply tiered scoring rules requested by user
                if pct > 30.0:
                    severity = 'critical'
                elif pct >= 10.0:
                    severity = 'warning'
                else:
                    severity = 'info'
                    
                self.findings.append(AuditFinding(
                    category='missing_values',
                    severity=severity,
                    description=f"Column '{col}' has {pct:.1f}% missing values.",
                    affected_records=int(count),
                    details={'column': col, 'missing_pct': pct}
                ))
        return max_missing_pct
        
    def _determine_health_tier(self, missing_pct_max: float) -> str:
        """Determine Data Health Tier based on user specification."""
        if missing_pct_max > 30.0:
            return "Critical/Low Quality (Red)"
        elif missing_pct_max >= 10.0:
            return "Moderate Quality (Yellow)"
        else:
            return "High Quality (Green)"

    def _check_endpoint_consistency(self, df: pd.DataFrame, sci_to_user: dict) -> None:
        """
        Unit-Endpoint Cross-Check optimized using unique combinations to avoid row-by-row iteration.
        Flags mismatch (e.g. LD50 in mg/L) as 'Scientific Inconsistency'.
        """
        endpoint_col = sci_to_user.get('endpoint')
        unit_col = sci_to_user.get('unit')
        
        if not endpoint_col or not unit_col or endpoint_col not in df.columns or unit_col not in df.columns:
            return
            
        # Get unique endpoint and unit combinations to avoid O(N) loop
        unique_pairs = df[[endpoint_col, unit_col]].dropna().drop_duplicates()
        
        inconsistent_combinations = []
        for _, row in unique_pairs.iterrows():
            ep = str(row[endpoint_col]).strip()
            unit = str(row[unit_col]).strip()
            
            if ep and unit:
                is_consistent = self.endpoint_validator.validate_unit_consistency(ep, unit)
                if not is_consistent:
                    inconsistent_combinations.append((ep, unit))
                    
        if not inconsistent_combinations:
            return
            
        # Sum up all matching rows in a single vectorized filter
        inconsistent_records = 0
        details = []
        
        for ep, unit in inconsistent_combinations:
            match_mask = (df[endpoint_col].astype(str).str.strip() == ep) & (df[unit_col].astype(str).str.strip() == unit)
            count = int(match_mask.sum())
            inconsistent_records += count
            
            # Find up to 5 total examples
            if len(details) < 5:
                matching_indices = df[match_mask].index[:5 - len(details)]
                for idx in matching_indices:
                    details.append({'row': int(idx), 'endpoint': ep, 'unit': unit})
                    
        if inconsistent_records > 0:
            self.findings.append(AuditFinding(
                category='scientific_inconsistency',
                severity='critical',
                description=f"Found {inconsistent_records} records with Unit-Endpoint mismatch (e.g. Dose vs Concentration).",
                affected_records=inconsistent_records,
                details={'examples': details[:5]} # store up to 5 examples to avoid huge payloads
            ))

    def _check_log10_variance(self, df: pd.DataFrame, sci_to_user: dict) -> float:
        """
        Log10 Variance Logic — now delegates to the vectorized engine.
        Returns the total penalty to deduct from the quality score.
        """
        chem_col = sci_to_user.get('chemical_name') or sci_to_user.get('chemical_id') or sci_to_user.get('cas_number')
        val_col = sci_to_user.get('value')
        ep_col = sci_to_user.get('endpoint')
        unit_col = sci_to_user.get('unit')
        
        if not chem_col or not val_col or not ep_col:
            return 0.0
        if chem_col not in df.columns or val_col not in df.columns or ep_col not in df.columns:
            return 0.0
        
        # Build group keys — include Units if available
        group_keys = [chem_col, ep_col]
        if unit_col and unit_col in df.columns:
            group_keys.append(unit_col)
        
        # Use the vectorized computation to get per-row flags
        _, variance_summary = self.compute_variance_flags(
            df, 
            {v: k for k, v in sci_to_user.items()},  # invert back to user_col → sci_var
            _internal=True
        )
        
        if variance_summary is None:
            return 0.0
        
        high_variance_count = variance_summary.conflict_count
        
        if high_variance_count > 0:
            self.findings.append(AuditFinding(
                category='variance_penalty',
                severity='warning',
                description=f"Found {high_variance_count} compound/endpoint/unit groups with high intra-record variance (delta log10 >= 1).",
                affected_records=high_variance_count,
                details={'examples': variance_summary.conflict_compounds[:5]}
            ))
            
            # 2 points penalty per high variance compound, capped at 20 points
            return min(20.0, high_variance_count * 2.0)
            
        return 0.0

    # ─── Vectorized Log₁₀ Variance Engine ─────────────────────────────

    def compute_variance_flags(
        self,
        df: pd.DataFrame,
        column_mappings: dict,
        _internal: bool = False,
    ) -> tuple:
        """
        Fully-vectorized log₁₀ variance audit.
        
        Groups by [Substance/CID, Endpoint, Units] and computes the log₁₀
        range for each group.  Adds an ``audit_flag`` column to the returned
        dataframe with one of three labels:
        
            * ``Consistent``              — Range < 0.5
            * ``Moderate_Variance``        — 0.5 ≤ Range < 1.0
            * ``High_Variance_Conflict``   — Range ≥ 1.0
        
        Rows whose numeric value is non-positive (cannot take log₁₀) or
        that belong to singleton groups receive ``Consistent``.
        
        Args:
            df:               Input dataframe (not mutated).
            column_mappings:  ``{user_col: scientific_var}`` dict.
            _internal:        When True, skip the audit_flag column write to
                              avoid double-writing during the audit pipeline.
        
        Returns:
            Tuple of ``(flagged_df, VarianceSummary | None)``.
            Returns ``(df.copy(), None)`` if required columns are missing.
        """
        sci_to_user = {v: k for k, v in column_mappings.items()}
        
        chem_col = sci_to_user.get('chemical_name') or sci_to_user.get('chemical_id') or sci_to_user.get('cas_number')
        val_col  = sci_to_user.get('value')
        ep_col   = sci_to_user.get('endpoint')
        unit_col = sci_to_user.get('unit')
        
        if not chem_col or not val_col or not ep_col:
            return df.copy(), None
        if chem_col not in df.columns or val_col not in df.columns or ep_col not in df.columns:
            return df.copy(), None
        
        out = df.copy()
        
        # ── 1. Numeric coercion & log₁₀ ────────────────────────────────
        numeric_vals = pd.to_numeric(out[val_col], errors='coerce')
        # Mask non-positive values (log₁₀ undefined for ≤ 0)
        valid_mask = numeric_vals > 0
        log_vals = np.full(len(out), np.nan)
        log_vals[valid_mask] = np.log10(numeric_vals[valid_mask].values)
        out['_log10_val'] = log_vals
        
        # ── 2. Build group keys ─────────────────────────────────────────
        group_keys = [chem_col, ep_col]
        if unit_col and unit_col in out.columns:
            group_keys.append(unit_col)
        
        # ── 3. Vectorized group range: max(log) - min(log) ─────────────
        grouped = out.groupby(group_keys, dropna=False)['_log10_val']
        out['_log_max'] = grouped.transform('max')
        out['_log_min'] = grouped.transform('min')
        out['_log_range'] = out['_log_max'] - out['_log_min']
        # Groups with a single valid entry (or all-NaN) get range = 0
        out['_log_range'] = out['_log_range'].fillna(0.0)
        
        # ── 4. Threshold labeling via np.select (fully vectorized) ──────
        conditions = [
            out['_log_range'] >= 1.0,
            out['_log_range'] >= 0.5,
        ]
        choices = ['High_Variance_Conflict', 'Moderate_Variance']
        flag_col = np.select(conditions, choices, default='Consistent')
        
        if not _internal:
            out['audit_flag'] = flag_col
        
        # ── 5. Build per-group summary for reporting ────────────────────
        # Deduplicate to group level for counting
        group_df = out.drop_duplicates(subset=group_keys)
        group_ranges = group_df['_log_range']
        
        consistent_count = int((group_ranges < 0.5).sum())
        moderate_count   = int(((group_ranges >= 0.5) & (group_ranges < 1.0)).sum())
        conflict_count   = int((group_ranges >= 1.0).sum())
        total_groups     = len(group_df)
        
        # Conflict compound details (for PDF report)
        conflict_mask = group_df['_log_range'] >= 1.0
        conflict_compounds = []
        if conflict_mask.any():
            for _, row in group_df[conflict_mask].head(50).iterrows():
                entry = {
                    'chemical': str(row[chem_col]),
                    'endpoint': str(row[ep_col]),
                    'log_range': round(float(row['_log_range']), 3),
                    'min_log10': round(float(row['_log_min']), 3),
                    'max_log10': round(float(row['_log_max']), 3),
                }
                if unit_col and unit_col in row.index:
                    entry['unit'] = str(row[unit_col])
                conflict_compounds.append(entry)
        
        # Consistency score: % of groups with Range < 1.0
        passed = consistent_count + moderate_count
        consistency_score = (passed / total_groups * 100) if total_groups > 0 else 100.0
        
        variance_summary = VarianceSummary(
            consistent_count=consistent_count,
            moderate_count=moderate_count,
            conflict_count=conflict_count,
            conflict_compounds=conflict_compounds,
            consistency_score=round(consistency_score, 1),
            total_groups_analyzed=total_groups,
        )
        
        # ── 6. Cleanup scratch columns ──────────────────────────────────
        out.drop(columns=['_log10_val', '_log_max', '_log_min', '_log_range'], inplace=True)
        
        return out, variance_summary

    def _calculate_quality_score(self, df: pd.DataFrame, max_missing_pct: float, variance_penalty: float) -> float:
        """
        Calculates a 0-100 quality score based on findings and penalties.
        """
        score = 100.0
        
        # Deduct based on overall missing data
        if max_missing_pct > 30.0:
            score -= 30.0
        elif max_missing_pct >= 10.0:
            score -= 10.0
            
        # Deduct based on critical scientific inconsistencies
        inconsistencies = sum(1 for f in self.findings if f.category == 'scientific_inconsistency')
        if inconsistencies > 0:
            score -= (inconsistencies * 10.0) # 10 points per inconsistency category hit (typically 1)
            
        # Deduct Variance Penalty
        score -= variance_penalty
        
        return max(0.0, float(score))
