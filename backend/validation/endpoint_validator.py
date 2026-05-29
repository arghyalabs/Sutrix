from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

class EndpointCategory(Enum):
    ACUTE_TOXICITY = "acute_toxicity"
    CHRONIC_TOXICITY = "chronic_toxicity"
    DEVELOPMENTAL_TOXICITY = "developmental_toxicity"
    GENOTOXICITY = "genotoxicity"
    CARCINOGENICITY = "carcinogenicity"
    ECOTOXICITY = "ecotoxicity"

class UnitType(Enum):
    MASS_WEIGHT = "mass/weight" # e.g. mg/kg
    MASS_VOLUME = "mass/volume" # e.g. mg/L, ug/mL
    CONCENTRATION = "concentration" # e.g. uM, mM
    ANY = "any"

@dataclass
class EndpointDefinition:
    """Definition of a toxicological endpoint."""
    name: str
    category: EndpointCategory
    expected_unit_type: UnitType
    synonyms: List[str]

class EndpointValidator:
    """Validates endpoints and cross-checks with unit types."""
    
    def __init__(self):
        # Core standard set
        self.standard_endpoints = [
            EndpointDefinition(
                name="LD50",
                category=EndpointCategory.ACUTE_TOXICITY,
                expected_unit_type=UnitType.MASS_WEIGHT,
                synonyms=["lethal dose 50", "median lethal dose"]
            ),
            EndpointDefinition(
                name="LC50",
                category=EndpointCategory.ACUTE_TOXICITY,
                expected_unit_type=UnitType.MASS_VOLUME,
                synonyms=["lethal concentration 50", "median lethal concentration"]
            ),
            EndpointDefinition(
                name="NOAEL",
                category=EndpointCategory.CHRONIC_TOXICITY,
                expected_unit_type=UnitType.MASS_WEIGHT,
                synonyms=["no observed adverse effect level", "noael"]
            ),
            EndpointDefinition(
                name="LOAEL",
                category=EndpointCategory.CHRONIC_TOXICITY,
                expected_unit_type=UnitType.MASS_WEIGHT,
                synonyms=["lowest observed adverse effect level", "loael"]
            ),
            EndpointDefinition(
                name="EC50",
                category=EndpointCategory.ECOTOXICITY,
                expected_unit_type=UnitType.MASS_VOLUME,
                synonyms=["effective concentration 50", "median effective concentration"]
            ),
            EndpointDefinition(
                name="IC50",
                category=EndpointCategory.ECOTOXICITY,
                expected_unit_type=UnitType.CONCENTRATION,
                synonyms=["inhibitory concentration 50", "half maximal inhibitory concentration"]
            )
        ]
        
        self._build_index()

    def _build_index(self):
        """Build a fast lookup dictionary for endpoint names and synonyms."""
        self._index: Dict[str, EndpointDefinition] = {}
        for ep in self.standard_endpoints:
            self._index[ep.name.lower()] = ep
            for syn in ep.synonyms:
                self._index[syn.lower()] = ep
                
    def normalize_endpoint(self, raw_endpoint: str) -> Optional[EndpointDefinition]:
        """Attempt to match a raw endpoint string to a standard definition."""
        if not isinstance(raw_endpoint, str):
            return None
        return self._index.get(raw_endpoint.strip().lower())

    def validate_unit_consistency(self, endpoint_name: str, unit_string: str) -> bool:
        """
        Cross-check if the provided unit string is appropriate for the endpoint.
        Returns True if consistent or unknown, False if definitely inconsistent.
        """
        if not isinstance(endpoint_name, str) or not isinstance(unit_string, str):
            return True # Cannot validate
            
        endpoint_def = self.normalize_endpoint(endpoint_name)
        if not endpoint_def:
            return True # Unknown endpoint, can't validate
            
        unit_lower = unit_string.lower().strip()
        
        # Simple heuristic mapping for unit strings to UnitType
        # In a full production system, this would interface with unit_converter.py
        is_mass_weight = any(u in unit_lower for u in ["/kg", "/g", "mg/kg", "g/kg"])
        is_mass_vol = any(u in unit_lower for u in ["/l", "/ml", "mg/l", "ug/ml"])
        
        if endpoint_def.expected_unit_type == UnitType.MASS_WEIGHT:
            if is_mass_vol and not is_mass_weight:
                return False
        elif endpoint_def.expected_unit_type == UnitType.MASS_VOLUME:
            if is_mass_weight and not is_mass_vol:
                return False
                
        return True
