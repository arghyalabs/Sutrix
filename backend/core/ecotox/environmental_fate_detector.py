import re
from typing import Tuple, Dict, Any

class EnvironmentalFateDetector:
    """
    Identifies and classifies environmental fate, transport, and exposure columns.
    Enables automatic matching for biodegradation, soil partition, BCF, and DT50 parameters.
    """
    
    BIODEGRADATION_ALIASES = ["biodegradation", "ready_biodegradable", "inherent_biodegradation", "biodegradability"]
    BIOACCUMULATION_ALIASES = ["bcf", "bioaccumulation", "bio_concentration_factor", "bioconcentration"]
    ADSORPTION_ALIASES = ["koc", "soil_adsorption", "organic_carbon_partition", "sorption"]
    PERSISTENCE_ALIASES = ["persistent", "half_life_soil", "half_life_water", "dt50", "dt90", "half-life"]

    @staticmethod
    def detect_environmental_fate(column_name: str) -> Tuple[str, float]:
        """
        Detects if a column is related to environmental fate and transport.
        Returns (parameter_category, confidence)
        """
        text_lower = column_name.lower().strip()
        
        # 1. Bioaccumulation / BCF
        for alias in EnvironmentalFateDetector.BIOACCUMULATION_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Bioaccumulation (BCF)", 0.95
            if alias in text_lower:
                return "Bioaccumulation (BCF)", 0.80

        # 2. Biodegradation
        for alias in EnvironmentalFateDetector.BIODEGRADATION_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Biodegradation", 0.95
            if alias in text_lower:
                return "Biodegradation", 0.80

        # 3. Adsorption / Soil Partition Koc
        for alias in EnvironmentalFateDetector.ADSORPTION_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Soil Adsorption (Koc)", 0.95
            if alias in text_lower:
                return "Soil Adsorption (Koc)", 0.80

        # 4. Persistence / Half-Life DT50
        for alias in EnvironmentalFateDetector.PERSISTENCE_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Persistence / Half-Life (DT50)", 0.95
            if alias in text_lower:
                return "Persistence / Half-Life (DT50)", 0.80

        return "unknown", 0.0
