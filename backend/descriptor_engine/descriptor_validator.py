import math
from typing import Dict, Any

def validate_descriptors(raw_descriptors: Dict[str, Any], required_keys: list = None) -> Dict[str, Any]:
    """
    Validates a raw descriptor dictionary.
    Replaces NaN, Infinity, and other invalid types with None.
    Ensures all expected keys are present.
    """
    validated = {}
    
    for k, v in raw_descriptors.items():
        if v is None:
            validated[k] = None
        elif isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                validated[k] = None
            else:
                validated[k] = v
        elif isinstance(v, int):
            validated[k] = v
        elif isinstance(v, str):
            validated[k] = v
        else:
            try:
                # try converting to float as fallback
                float_val = float(v)
                if math.isnan(float_val) or math.isinf(float_val):
                    validated[k] = None
                else:
                    validated[k] = float_val
            except (ValueError, TypeError):
                validated[k] = None
                
    if required_keys:
        for key in required_keys:
            if key not in validated:
                validated[key] = None
                
    return validated
