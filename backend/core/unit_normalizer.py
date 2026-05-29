import re
from typing import Optional, Tuple

class UnitNormalizer:
    """
    Detects and normalizes concentration and measurement units embedded inside messy column headers.
    """
    
    UNIT_PATTERNS = {
        "mg/L": [r"mg/l", r"mg l-1", r"milligram per liter"],
        "µg/L": [r"ug/l", r"µg/l", r"microgram per liter", r"ug l-1"],
        "ng/L": [r"ng/l", r"ng l-1"],
        "ppm": [r"ppm", r"parts per million"],
        "ppb": [r"ppb", r"parts per billion"],
        "mol/L": [r"mol/l", r"moles/l", r"molar", r"\bm\b"],
        "mM": [r"mm", r"mmol/l", r"millimolar"],
        "µM": [r"um", r"µm", r"umol/l", r"micromolar"],
        "nM": [r"nm", r"nmol/l", r"nanomolar"],
        "mg/kg": [r"mg/kg", r"mg kg-1", r"mg/kg/day"],
    }
    
    @staticmethod
    def detect_and_strip_unit(column_name: str) -> Tuple[str, Optional[str]]:
        """
        Scans a column name for known units, returning the cleaned string and the detected unit.
        e.g., 'IC50_uM' -> ('IC50', 'µM')
        """
        col_lower = column_name.lower()
        detected_unit = None
        
        for std_unit, aliases in UnitNormalizer.UNIT_PATTERNS.items():
            for alias in aliases:
                # Match unit as a standalone token or surrounded by standard boundaries
                pattern = r"(?:[\s_\(\[\/\-]|^)" + re.escape(alias) + r"(?:\b|[\s_\)\]\-]|$)"
                match = re.search(pattern, col_lower)
                if match:
                    detected_unit = std_unit
                    # Strip the unit to help the fuzzy matcher
                    col_lower = col_lower.replace(match.group(0), " ").strip()
                    # Also strip dangling underscores or parentheses
                    col_lower = re.sub(r"[\(\)\[\]_]", " ", col_lower).strip()
                    return col_lower, detected_unit
                    
        return column_name, detected_unit
