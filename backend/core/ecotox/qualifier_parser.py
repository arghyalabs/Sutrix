import re
from typing import Dict, Any, Optional

class QualifierParser:
    """
    Detects mathematical qualifiers, inequality symbols, and extracts structured
    operators, values, and units from messy toxicological cells.
    """
    
    QUALIFIER_COLUMN_ALIASES = [
        "qualifier", "operator", "relation", "comparison", "inequality"
    ]

    # Standardize operators
    OPERATOR_MAP = {
        ">=": ">=",
        "&gt;=": ">=",
        "ge": ">=",
        "<=": "<=",
        "&lt;=": "<=",
        "le": "<=",
        ">": ">",
        "&gt;": ">",
        "gt": ">",
        "<": "<",
        "&lt;": "<",
        "lt": "<",
        "==": "=",
        "=": "=",
        "eq": "=",
        "~": "~",
        "≈": "~",
        "approx": "~",
        "nd": "ND",
        "na": "NA",
        "bql": "BQL",
        "lod": "LOD",
        "loq": "LOQ"
    }

    @staticmethod
    def is_qualifier_column(column_name: str) -> bool:
        text_lower = column_name.lower().strip()
        for alias in QualifierParser.QUALIFIER_COLUMN_ALIASES:
            if alias in text_lower or text_lower == alias:
                return True
        return False

    @staticmethod
    def parse(cell_value: Any) -> Dict[str, Any]:
        """
        Parses a cell value (string, float, etc.) and extracts operator, value, and unit.
        Example: ">= 50 ppm" -> {"operator": ">=", "value": 50.0, "unit": "ppm", "qsar_ready": True}
        Example: "BQL" -> {"operator": "BQL", "value": None, "unit": None, "qsar_ready": False}
        """
        result = {
            "operator": "=",
            "value": None,
            "unit": None,
            "qsar_ready": False
        }

        if cell_value is None:
            return result

        orig_str = str(cell_value).strip()
        val_str = orig_str.lower()
        if not val_str:
            return result

        # 1. Check for standalone non-numeric codes (ND, NA, BQL, LOD, LOQ)
        for code in ["nd", "na", "bql", "lod", "loq"]:
            if val_str == code or re.search(r'\b' + re.escape(code) + r'\b', val_str):
                result["operator"] = code.upper()
                return result

        # 2. Extract operator prefix if present
        operator = "="
        remaining_str = orig_str
        val_lower = val_str
        
        # Sort keys by length in descending order to match multi-character operators first (e.g. >= before >)
        sorted_operators = sorted(QualifierParser.OPERATOR_MAP.keys(), key=len, reverse=True)
        for op in sorted_operators:
            if val_lower.startswith(op):
                operator = QualifierParser.OPERATOR_MAP[op]
                remaining_str = orig_str[len(op):].strip()
                break
            elif re.match(r'^' + re.escape(op) + r'\s+\d', val_lower):
                operator = QualifierParser.OPERATOR_MAP[op]
                remaining_str = re.sub(r'^' + re.escape(op), '', orig_str, flags=re.IGNORECASE).strip()
                break

        result["operator"] = operator

        # 3. Match numeric value and unit (case-insensitive search on original string to preserve unit case)
        num_unit_match = re.search(
            r'([-+]?\d*\.\d+|\d+\.?\d*(?:[eE][-+]?\d+)?)\s*([a-zA-Z%µμ/]+[0-9a-zA-Z%µμ/]*.*)?$', 
            remaining_str,
            re.IGNORECASE
        )
        
        if num_unit_match:
            try:
                result["value"] = float(num_unit_match.group(1))
                result["qsar_ready"] = True
            except ValueError:
                result["value"] = None
                
            unit_str = num_unit_match.group(2)
            if unit_str:
                result["unit"] = unit_str.strip()
        else:
            # Try plain float extraction
            plain_float = re.search(r'([-+]?\d*\.\d+|\d+)', remaining_str)
            if plain_float:
                try:
                    result["value"] = float(plain_float.group(1))
                    result["qsar_ready"] = True
                except ValueError:
                    pass

        return result
