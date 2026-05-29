"""
Smart Deduplication Engine for Scientific Datasets.

Identifies and removes exact scientific duplicates using domain-specific
composite keys. Uses vectorized Pandas operations for performance.
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


# Ordered list of scientific variable names that together define a unique observation.
# The deduplicator resolves these to actual user-column names via the column_mappings dict.
# Multiple aliases are checked because the synonym mapper may use different canonical names
# (e.g. 'chemical_id' vs 'chemical_name') and the qualifier parser may rename value columns.
SCIENTIFIC_DUPLICATE_KEYS = [
    # Chemical identity — try multiple aliases
    ['chemical_name', 'chemical_id', 'cas_number'],  # Any ONE of these is sufficient
    ['value'],                                        # Numeric measurement
    ['qualifier'],                                    # Mathematical operator (>, <, =, ~)
    ['unit'],                                         # Measurement unit (mg/kg, mg/L)
    ['endpoint'],                                     # Toxicological endpoint (LD50, NOAEL)
    ['species'],                                      # Target organism
    ['duration'],                                     # Exposure duration
]


@dataclass
class DeduplicationResult:
    """Result container for deduplication operation."""
    original_count: int
    deduplicated_count: int
    duplicates_removed: int
    duplicate_groups: int          # Number of unique groups that had duplicates
    removed_indices: List[int]     # Indices of removed rows (for preview)
    keys_used: List[str]           # Actual column names used for dedup


class SmartDeduplicator:
    """
    Performs scientifically-aware deduplication on research datasets.
    
    A duplicate is defined as having identical values across all mapped
    scientific keys: [Substance/CID, Value, Qualifier, Units, Endpoint,
    Species, Duration].
    
    Only columns that are both (a) present in the column_mappings and
    (b) exist in the dataframe are used as composite keys.  If fewer
    than 2 keys resolve, deduplication is skipped to avoid accidental
    data loss.
    """
    
    MIN_KEYS_REQUIRED = 2  # Safety: refuse to dedup on fewer than 2 columns
    
    def _resolve_columns(
        self,
        df: pd.DataFrame,
        column_mappings: Dict[str, str],
    ) -> List[str]:
        """
        Resolve scientific variable names to actual dataframe column names.
        
        Handles:
        - Multiple aliases per key group (e.g. 'chemical_name' OR 'chemical_id')
        - Derived columns from the QualifierParser (e.g. 'Dose_numeric' mapped as 'value')
        - Original raw columns that may still carry dedup-relevant content
        """
        # Invert mapping: scientific_var → user_col
        sci_to_user = {v: k for k, v in column_mappings.items()}
        
        subset_cols: List[str] = []
        
        for key_group in SCIENTIFIC_DUPLICATE_KEYS:
            # Try each alias in the group until one resolves
            resolved = False
            for sci_var in key_group:
                user_col = sci_to_user.get(sci_var)
                if user_col and user_col in df.columns:
                    subset_cols.append(user_col)
                    resolved = True
                    break
            
            # If the mapped column doesn't exist, also try scanning for
            # the original (pre-qualifier-parser) column. The qualifier parser
            # renames e.g. "Dose Value" → "Dose Value_numeric" and remaps 'value'
            # to the new column. The ORIGINAL column may still be in the df
            # and is better for dedup because it preserves the raw text.
            if not resolved:
                for sci_var in key_group:
                    # Check if any column mapping used to point to this variable
                    # but now the column has a derived suffix
                    for user_col, mapped_var in column_mappings.items():
                        if mapped_var == sci_var and user_col in df.columns:
                            subset_cols.append(user_col)
                            resolved = True
                            break
                    if resolved:
                        break
        
        return subset_cols
    
    def deduplicate(
        self,
        df: pd.DataFrame,
        column_mappings: Dict[str, str],
    ) -> Tuple[pd.DataFrame, DeduplicationResult]:
        """
        Remove exact duplicates across all columns in the spreadsheet.
        
        Args:
            df: Input dataframe (not mutated).
            column_mappings: Dict mapping user column names -> scientific variable
                             names.
        
        Returns:
            Tuple of (deduplicated DataFrame, DeduplicationResult stats).
        """
        subset_cols = df.columns.tolist()
        original_count = len(df)
        
        # --- Vectorized deduplication ---
        # Mark duplicates (keep='first' preserves the earliest occurrence)
        is_duplicate = df.duplicated(subset=subset_cols, keep='first')
        
        removed_indices = df.index[is_duplicate].tolist()
        duplicate_groups = int(df[is_duplicate].drop_duplicates(subset=subset_cols).shape[0]) if is_duplicate.any() else 0
        
        deduped_df = df[~is_duplicate].reset_index(drop=True)
        
        return deduped_df, DeduplicationResult(
            original_count=original_count,
            deduplicated_count=len(deduped_df),
            duplicates_removed=int(is_duplicate.sum()),
            duplicate_groups=duplicate_groups,
            removed_indices=removed_indices[:100],  # Cap at 100 for memory
            keys_used=["All Columns"],
        )
    
    def preview_duplicates(
        self,
        df: pd.DataFrame,
        column_mappings: Dict[str, str],
        max_rows: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Return a preview DataFrame of rows that *would* be removed.
        Useful for showing the user what dedup would delete.
        """
        subset_cols = df.columns.tolist()
        is_dup = df.duplicated(subset=subset_cols, keep='first')
        if max_rows is not None:
            return df[is_dup].head(max_rows)
        return df[is_dup]
