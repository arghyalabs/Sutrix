import re
from typing import Tuple, Dict, Any

class DurationParser:
    """
    Automatically detects exposure durations from scientific columns and normalizes them.
    Supports standard toxicological study designs (e.g. 96h, 48h, 14d, 90d).
    """
    
    DURATION_COLUMN_ALIASES = [
        "duration", "exposure_duration", "timepoint", "incubation", 
        "exposure_time", "study_length", "treatment_period"
    ]

    STANDARD_DURATIONS = [
        "24h", "48h", "72h", "96h", 
        "7d", "14d", "21d", "28d", "30d", "90d", 
        "1y", "2y", "lifetime"
    ]

    @staticmethod
    def is_duration_column(column_name: str) -> bool:
        text_lower = column_name.lower().strip()
        for alias in DurationParser.DURATION_COLUMN_ALIASES:
            if alias in text_lower or text_lower == alias:
                return True
        return False

    @staticmethod
    def detect_duration(text: str) -> Tuple[str, float]:
        """
        Extracts duration from column text.
        Returns (duration_string, confidence_score)
        """
        text_lower = text.lower().strip()
        
        # Check standard durations exactly
        for d in DurationParser.STANDARD_DURATIONS:
            if d == text_lower:
                return d, 1.0
            if re.search(r'\b' + re.escape(d) + r'\b', text_lower):
                return d, 0.9

        # Hour matches: 96h, 96-h, 96 hours
        hour_match = re.search(r'(\d+)\s*-?\s*h(?:our)?s?', text_lower)
        if hour_match:
            return f"{hour_match.group(1)}h", 0.85
            
        # Day matches: 14d, 14-d, 14 days
        day_match = re.search(r'(\d+)\s*-?\s*d(?:ay)?s?', text_lower)
        if day_match:
            return f"{day_match.group(1)}d", 0.85
            
        # Week matches: 4w, 4 weeks
        week_match = re.search(r'(\d+)\s*-?\s*w(?:k|eek)?s?', text_lower)
        if week_match:
            return f"{week_match.group(1)}w", 0.80

        # Month matches: 3m, 3 months
        month_match = re.search(r'(\d+)\s*-?\s*mo(?:nth)?s?', text_lower)
        if month_match:
            return f"{month_match.group(1)}mo", 0.80

        # Year matches: 2y, 2 years
        year_match = re.search(r'(\d+)\s*-?\s*y(?:r|ear)?s?', text_lower)
        if year_match:
            return f"{year_match.group(1)}y", 0.80
            
        return "", 0.0

    @staticmethod
    def normalize_duration(duration_str: str) -> Dict[str, Any]:
        """
        Standardizes duration string to numerical values and parsed units.
        Returns e.g. {"value": 96.0, "unit": "hours", "standardized_days": 4.0}
        """
        if not duration_str:
            return {"value": None, "unit": "unknown", "standardized_days": None}
            
        duration_str = duration_str.lower().strip()
        
        if duration_str == "lifetime":
            return {"value": -1.0, "unit": "lifetime", "standardized_days": -1.0}

        # Parse units
        match = re.match(r'(\d+)\s*(h|d|w|mo|y|hour|day|week|month|year)', duration_str)
        if not match:
            return {"value": None, "unit": "unknown", "standardized_days": None}
            
        val = float(match.group(1))
        unit = match.group(2)
        
        std_days = 0.0
        unit_full = "unknown"
        
        if unit in ["h", "hour"]:
            std_days = val / 24.0
            unit_full = "hours"
        elif unit in ["d", "day"]:
            std_days = val
            unit_full = "days"
        elif unit in ["w", "week"]:
            std_days = val * 7.0
            unit_full = "weeks"
        elif unit in ["mo", "month"]:
            std_days = val * 30.0
            unit_full = "months"
        elif unit in ["y", "year"]:
            std_days = val * 365.0
            unit_full = "years"
            
        return {
            "value": val,
            "unit": unit_full,
            "standardized_days": round(std_days, 3)
        }
