import re
from typing import Tuple, Dict, Any, List

class GuidelineDetector:
    """
    Detects standard regulatory study guidelines (OECD, US EPA, REACH, IUCLID) 
    from column headers or data strings.
    """
    
    OECD_PATTERNS = {
        "OECD 201": [r"oecd[\s_-]*201", r"alga(?:e)?\s*growth\s*inhibition"],
        "OECD 202": [r"oecd[\s_-]*202", r"daphnia\s*sp\.?\s*acute\s*immobilisation"],
        "OECD 203": [r"oecd[\s_-]*203", r"fish\s*acute\s*toxicity"],
        "OECD 301": [r"oecd[\s_-]*301", r"ready\s*biodegradability"],
        "OECD 404": [r"oecd[\s_-]*404", r"acute\s*dermal\s*irritation"],
        "OECD 423": [r"oecd[\s_-]*423", r"acute\s*oral\s*toxicity\s*-\s*acute\s*toxic\s*class"],
        "OECD 425": [r"oecd[\s_-]*425", r"acute\s*oral\s*toxicity\s*-\s*up\s*and\s*down"]
    }

    EPA_ALIASES = ["epa", "fifra", "toxcast", "tox21", "oppts"]
    REACH_ALIASES = ["reach", "echa", "iuclid"]

    @staticmethod
    def detect_guideline(text: str) -> Dict[str, Any]:
        """
        Scans text for regulatory guideline frameworks.
        Returns e.g. {"guideline": "OECD 203", "framework": "OECD", "confidence": 0.95}
        """
        text_lower = text.lower().strip()
        
        # 1. Check exact OECD guidelines
        for name, patterns in GuidelineDetector.OECD_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return {
                        "guideline": name,
                        "framework": "OECD",
                        "confidence": 0.95,
                        "reasons": [f"matched guideline pattern: {name}"]
                    }

        # 2. General EPA / ToxCast
        sorted_epa = sorted(GuidelineDetector.EPA_ALIASES, key=len, reverse=True)
        for epa_alias in sorted_epa:
            if re.search(r'\b' + re.escape(epa_alias) + r'\b', text_lower):
                return {
                    "guideline": epa_alias.upper(),
                    "framework": "US EPA",
                    "confidence": 0.90,
                    "reasons": [f"matched US EPA framework: {epa_alias}"]
                }

        # 3. REACH / ECHA / IUCLID
        sorted_reach = sorted(GuidelineDetector.REACH_ALIASES, key=len, reverse=True)
        for reach_alias in sorted_reach:
            if re.search(r'\b' + re.escape(reach_alias) + r'\b', text_lower):
                return {
                    "guideline": reach_alias.upper(),
                    "framework": "ECHA / REACH",
                    "confidence": 0.90,
                    "reasons": [f"matched ECHA framework: {reach_alias}"]
                }

        return {
            "guideline": None,
            "framework": None,
            "confidence": 0.0,
            "reasons": []
        }
