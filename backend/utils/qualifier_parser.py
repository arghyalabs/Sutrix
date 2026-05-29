import re
import math
from typing import Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum

class QualifierType(Enum):
    EXACT = "="
    APPROXIMATE = "~"
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_OR_EQUAL = ">="
    LESS_OR_EQUAL = "<="
    NOT_DETECTED = "ND"
    BELOW_LOD = "<LOD"
    ABOVE_LOQ = ">LOQ"

@dataclass
class QualifiedValue:
    """Represents a numeric value parsed alongside its mathematical qualifier and unit."""
    value: float
    qualifier: QualifierType
    unit: str
    original_string: str
    is_censored: bool
    
    @property
    def qsar_ready(self) -> bool:
        """
        Whether this value is absolute and suitable for QSAR modeling.
        QSAR-Ready if qualifier is EXACT or APPROXIMATE, and it is not censored.
        """
        if self.is_censored:
            return False
        if self.qualifier in [QualifierType.EXACT, QualifierType.APPROXIMATE]:
            return True
        return False

class QualifierParser:
    """Parses scientific values decoupling mathematical operators from numbers and units."""
    
    def __init__(self):
        # Group 1: Qualifiers (>=, <=, >, <, =, ~, ca., ND, <LOD, >LOQ)
        # Group 2: Numbers including scientific notation (e.g., 50.5, 1.2e-05, .5, 100)
        # Group 3: The remainder (typically units)
        self.pattern = re.compile(
            r"^(ca\.|ND|<LOD|>LOQ|[><=~]{1,2})?" # Group 1: Optional qualifier
            r"\s*"                                # Optional space
            r"([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)?" # Group 2: Optional Number
            r"\s*"                                # Optional space
            r"(.*)$",                             # Group 3: Everything else (units)
            re.IGNORECASE
        )
        
        self.qualifier_map = {
            "=": QualifierType.EXACT,
            "~": QualifierType.APPROXIMATE,
            "ca.": QualifierType.APPROXIMATE,
            ">": QualifierType.GREATER_THAN,
            "<": QualifierType.LESS_THAN,
            ">=": QualifierType.GREATER_OR_EQUAL,
            "<=": QualifierType.LESS_OR_EQUAL,
            "nd": QualifierType.NOT_DETECTED,
            "<lod": QualifierType.BELOW_LOD,
            ">loq": QualifierType.ABOVE_LOQ
        }
        
    def parse(self, raw_string: str) -> Optional[QualifiedValue]:
        """Parse a messy string into a QualifiedValue."""
        if not isinstance(raw_string, str):
            if isinstance(raw_string, (int, float)):
                # Handle raw numbers safely
                return QualifiedValue(
                    value=float(raw_string),
                    qualifier=QualifierType.EXACT,
                    unit="",
                    original_string=str(raw_string),
                    is_censored=False
                )
            return None
            
        raw_string = raw_string.strip()
        if not raw_string:
            return None
            
        match = self.pattern.match(raw_string)
        if not match:
            return None
            
        qual_str, num_str, unit_str = match.groups()
        
        # Determine Qualifier
        qualifier = QualifierType.EXACT
        if qual_str:
            qual_lower = qual_str.lower()
            qualifier = self.qualifier_map.get(qual_lower, QualifierType.EXACT)
            
        # Determine Value and Censored status
        is_censored = False
        value = float('nan')
        
        if qualifier in [QualifierType.NOT_DETECTED, QualifierType.BELOW_LOD, QualifierType.ABOVE_LOQ]:
            is_censored = True
            # User requirement: Do NOT set to 0.0 to avoid skewing ML models. Use NaN.
            value = float('nan')
        elif num_str:
            try:
                value = float(num_str)
            except ValueError:
                return None
        elif not num_str and not qual_str:
            return None # Edge case: just a unit was passed
            
        # Determine if it's censored due to limit operators
        if qualifier in [QualifierType.GREATER_THAN, QualifierType.LESS_THAN, 
                         QualifierType.GREATER_OR_EQUAL, QualifierType.LESS_OR_EQUAL]:
            is_censored = True
            
        return QualifiedValue(
            value=value,
            qualifier=qualifier,
            unit=unit_str.strip() if unit_str else "",
            original_string=raw_string,
            is_censored=is_censored
        )
