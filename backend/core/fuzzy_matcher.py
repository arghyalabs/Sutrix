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
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Helper to compute standard Levenshtein distance."""
        if len(s1) < len(s2):
            return FuzzyMatcher._levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return previous_row[-1]

    @staticmethod
    def compute_similarity(source: str, target: str) -> float:
        """Returns similarity score between 0.0 and 1.0."""
        s_norm = FuzzyMatcher.normalize_column_name(source)
        t_norm = FuzzyMatcher.normalize_column_name(target)
        
        if not s_norm or not t_norm:
            return 0.0
            
        if s_norm == t_norm:
            return 1.0
            
        # Check substring relation only for substrings of length >= 3
        # Or if it matches on a word boundary
        shorter, longer = (s_norm, t_norm) if len(s_norm) < len(t_norm) else (t_norm, s_norm)
        
        is_word_boundary = False
        words = longer.split(" ")
        if shorter in words:
            is_word_boundary = True
            
        if (len(shorter) >= 3 and shorter in longer) or is_word_boundary:
            ratio = len(shorter) / len(longer)
            base_score = 0.85 if is_word_boundary else 0.70
            return round(base_score + 0.14 * ratio, 2)
            
        # Check Levenshtein distance for typo detection
        if HAS_RAPIDFUZZ:
            try:
                from rapidfuzz.distance import Levenshtein
                dist = Levenshtein.distance(s_norm, t_norm)
            except Exception:
                dist = FuzzyMatcher._levenshtein_distance(s_norm, t_norm)
        else:
            dist = FuzzyMatcher._levenshtein_distance(s_norm, t_norm)
            
        max_len = max(len(s_norm), len(t_norm))
        if dist <= 1:
            return round(1.0 - (dist / max_len), 2)
        elif dist == 2 and max_len >= 6:
            return round(1.0 - (dist / max_len), 2)
            
        return 0.0

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
                
                # Check for whole-word occurrence matching
                alias_norm = FuzzyMatcher.normalize_column_name(alias)
                words = normalized_input.split(" ")
                if alias_norm in words:
                    score = max(score, 0.90)
                
                if score > best_score:
                    best_score = score
                    best_key = standard_key
                    
        return best_key, best_score
