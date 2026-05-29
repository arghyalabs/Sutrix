import re
import unicodedata
from typing import Tuple

try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False

class FuzzyMatcher:
    """
    Implements similarity techniques to match messy scientific dataset columns.
    """
    
    @staticmethod
    def normalize_column_name(col: str) -> str:
        """
        Normalizes headers before classification.
        Operations: lowercase, remove punctuation, replace underscores, trim, unicode norm.
        """
        # Unicode normalization
        col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
        col = col.lower().strip()
        # Replace non-alphanumeric (except standard math/unit symbols) with space
        col = re.sub(r'[^a-z0-9]', ' ', col)
        # Remove duplicate spaces
        col = re.sub(r'\s+', ' ', col).strip()
        return col

    @staticmethod
    def compute_similarity(source: str, target: str) -> float:
        """Returns similarity score between 0.0 and 1.0."""
        s_norm = FuzzyMatcher.normalize_column_name(source)
        t_norm = FuzzyMatcher.normalize_column_name(target)
        
        if not s_norm or not t_norm:
            return 0.0
            
        if s_norm == t_norm:
            return 1.0
            
        if HAS_RAPIDFUZZ:
            # Token set ratio is great for "IC50 (uM)" matching "IC50"
            score = fuzz.token_set_ratio(s_norm, t_norm) / 100.0
            return score
        else:
            # Fallback to difflib
            return difflib.SequenceMatcher(None, s_norm, t_norm).ratio()

    @staticmethod
    def find_best_match(col_name: str, ontology: dict) -> Tuple[str, float]:
        """
        Iterates over the alias ontology to find the highest scoring match.
        Returns (standard_key, confidence_score)
        """
        best_key = "none"
        best_score = 0.0
        
        normalized_input = FuzzyMatcher.normalize_column_name(col_name)
        
        for standard_key, aliases in ontology.items():
            for alias in aliases:
                score = FuzzyMatcher.compute_similarity(normalized_input, alias)
                # Exact prefix/suffix matching bonus
                if normalized_input == alias:
                    score = 1.0
                elif alias in normalized_input.split(" "):
                    score = min(1.0, score + 0.2)
                
                if score > best_score:
                    best_score = score
                    best_key = standard_key
                    
        return best_key, best_score
