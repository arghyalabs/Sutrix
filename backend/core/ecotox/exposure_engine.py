import re
from typing import Tuple, Dict, Any, List

class ExposureEngine:
    """
    Intelligently identifies study designs, test types, and exposure routes.
    Behaves like a regulatory toxicologist for REACH, GHS, and US EPA guidelines.
    """
    
    ACUTE_ALIASES = ["acute", "acute_toxicity", "acute_oral", "acute_dermal", "acute_inhalation", "short_term", "96h", "48h", "24h"]
    CHRONIC_ALIASES = ["chronic", "subchronic", "long_term", "repeated_dose", "90_day", "28_day", "lifetime"]
    SUBACUTE_ALIASES = ["subacute", "sub_chronic", "repeat_exposure", "sub-chronic", "sub-acute"]
    
    SPECIAL_TEST_ONTOLOGY = {
        "carcinogenicity": ["carcinogenicity", "tumor", "neoplasm", "cancer", "carcinogen"],
        "mutagenicity": ["mutagenicity", "ames", "genotoxicity", "chromosomal_aberration", "mutagen"],
        "reproductive": ["reproductive", "fertility", "developmental", "teratogenicity", "embryotoxicity"],
        "neurotoxicity": ["neurotoxicity", "neurobehavior", "cns", "neuro"]
    }

    TEST_TYPE_COLUMN_ALIASES = [
        "study_type", "test_type", "study_design", "toxicity_type", 
        "assay_category", "experiment_type", "endpoint_category"
    ]

    EXPOSURE_ROUTE_ALIASES = {
        "oral": ["oral", "gavage", "diet", "feed", "ingestion"],
        "dermal": ["dermal", "skin", "cutaneous"],
        "inhalation": ["inhalation", "intranasal", "aerosol", "dust", "gas"],
        "injection": ["injection", "intravenous", "iv", "ip", "intraperitoneal", "sc", "subcutaneous"]
    }

    @staticmethod
    def is_test_type_column(column_name: str) -> bool:
        text_lower = column_name.lower().strip()
        for alias in ExposureEngine.TEST_TYPE_COLUMN_ALIASES:
            if alias in text_lower or text_lower == alias:
                return True
        return False

    @staticmethod
    def infer_test_type(column_name: str, duration_days: float = None) -> Tuple[str, float]:
        """
        Infers the toxicological test type from a column name or contextual metadata.
        Returns (test_type, confidence_score)
        """
        text_lower = column_name.lower().strip()
        
        # 1. Check special test types first
        for category, aliases in ExposureEngine.SPECIAL_TEST_ONTOLOGY.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    return f"{category.capitalize()} Toxicity", 0.95
                if alias in text_lower:
                    return f"{category.capitalize()} Toxicity", 0.80

        # 2. Check Acute / Chronic explicit aliases
        for alias in ExposureEngine.ACUTE_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Acute Toxicity", 0.90
        for alias in ExposureEngine.CHRONIC_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Chronic Toxicity", 0.90
        for alias in ExposureEngine.SUBACUTE_ALIASES:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                return "Subchronic Toxicity", 0.90

        # 3. Fallback to duration boundaries (REACH/EPA rules)
        if duration_days is not None:
            if duration_days <= 4.0: # <= 96 hours
                return "Acute Toxicity", 0.85
            elif duration_days >= 90.0:
                return "Chronic Toxicity", 0.85
            else:
                return "Subchronic Toxicity", 0.80

        return "unknown", 0.0

    @staticmethod
    def detect_exposure_route(text: str) -> Tuple[str, float]:
        text_lower = text.lower().strip()
        for route, aliases in ExposureEngine.EXPOSURE_ROUTE_ALIASES.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    return route, 0.90
                if alias in text_lower:
                    return route, 0.70
        return "unknown", 0.0
