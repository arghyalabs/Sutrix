import re
from typing import Tuple, Dict, Any, List

class EndpointOntology:
    """
    Registry of regulatory toxicity, ecotoxicology, and environmental fate endpoints.
    Ascribes domain concepts automatically to messy laboratory fields.
    """
    
    LETHALITY_ENDPOINTS = ["ld50", "lc50", "ec50", "lethal_concentration", "median_lethal_dose", "mortality", "death", "survival"]
    GROWTH_ENDPOINTS = ["growth", "biomass", "cell_density", "body_weight", "weight_gain"]
    REPRODUCTION_ENDPOINTS = ["fecundity", "offspring", "egg_production", "hatching", "brood_size"]
    BEHAVIORAL_ENDPOINTS = ["mobility", "swimming", "feeding", "locomotion", "avoidance"]
    BIOCHEMICAL_ENDPOINTS = ["oxidative_stress", "enzyme_activity", "atp", "mitochondrial", "gst", "catalase"]
    
    REGULATORY_BOUNDS = {
        "NOEC": ["noec", "no_observed_effect_concentration"],
        "LOEC": ["loec", "lowest_observed_effect_concentration"],
        "NOAEL": ["noael", "no_observed_adverse_effect_level"],
        "LOAEL": ["loael", "lowest_observed_adverse_effect_level"],
        "BMD": ["benchmark_dose", "bmd", "bmdl"]
    }

    CELL_LINES = ["hela", "hek293", "hepG2", "mcf7", "a549", "cho", "jurkat", "u2os"]

    @staticmethod
    def identify_endpoint_category(text: str) -> Tuple[str, float]:
        """
        Determines the biological/toxicological endpoint category.
        Returns (category, confidence)
        """
        text_lower = text.lower().strip()
        text_norm = re.sub(r'[^a-z0-9]', '', text_lower)
        
        # 1. Match specific regulatory bounds
        for reg_type, aliases in EndpointOntology.REGULATORY_BOUNDS.items():
            for alias in aliases:
                alias_norm = re.sub(r'[^a-z0-9]', '', alias)
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    return f"Regulatory {reg_type} Bound", 0.95
                if alias_norm in text_norm:
                    return f"Regulatory {reg_type} Bound", 0.80

        # 2. Match lethality
        for alias in EndpointOntology.LETHALITY_ENDPOINTS:
            alias_norm = re.sub(r'[^a-z0-9]', '', alias)
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Lethality / Acute Potency", 0.90
            if alias_norm in text_norm:
                return "Lethality / Acute Potency", 0.70

        # 3. Sub-lethal endpoints
        for alias in EndpointOntology.GROWTH_ENDPOINTS:
            alias_norm = re.sub(r'[^a-z0-9]', '', alias)
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Growth / Biomass Inhibition", 0.90
            if alias_norm in text_norm:
                return "Growth / Biomass Inhibition", 0.70
                
        for alias in EndpointOntology.REPRODUCTION_ENDPOINTS:
            alias_norm = re.sub(r'[^a-z0-9]', '', alias)
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Reproductive Fecundity", 0.90
            if alias_norm in text_norm:
                return "Reproductive Fecundity", 0.70
                
        for alias in EndpointOntology.BEHAVIORAL_ENDPOINTS:
            alias_norm = re.sub(r'[^a-z0-9]', '', alias)
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Behavioral / Locomotion Impact", 0.90
            if alias_norm in text_norm:
                return "Behavioral / Locomotion Impact", 0.70
                
        for alias in EndpointOntology.BIOCHEMICAL_ENDPOINTS:
            alias_norm = re.sub(r'[^a-z0-9]', '', alias)
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Biochemical Biomarker / Stress", 0.90
            if alias_norm in text_norm:
                return "Biochemical Biomarker / Stress", 0.70

        # 4. Standard endpoints check
        standard_endpoints = ["lc50", "ld50", "ec50", "noec", "loec", "noael", "loael", "bmd", "bmdl"]
        for ep in standard_endpoints:
            if ep in text_norm:
                return f"{ep.upper()} Endpoint", 0.80

        return "unknown", 0.0

    @staticmethod
    def is_cell_line(text: str) -> bool:
        text_lower = text.lower().strip()
        for cell in EndpointOntology.CELL_LINES:
            if cell in text_lower:
                return True
        return False
