from backend.core.fuzzy_matcher import FuzzyMatcher
from backend.core.unit_normalizer import UnitNormalizer
from backend.core.scientific_ontology import UNIVERSAL_ONTOLOGY

class MappingConfidenceEngine:
    """
    Evaluates headers against the Universal Ontology and assigns AI confidence scores.
    """
    
    @staticmethod
    def evaluate_column(column_name: str) -> dict:
        """
        Returns a structured AI mapping payload.
        """
        reasons = []
        
        # 1. Check for units
        clean_name, unit = UnitNormalizer.detect_and_strip_unit(column_name)
        if unit:
            reasons.append(f"Unit '{unit}' isolated")
            
        # 2. Fuzzy match against standard ontology
        best_key, best_score = FuzzyMatcher.find_best_match(clean_name, UNIVERSAL_ONTOLOGY)
        
        if best_key != "none":
            reasons.append(f"Semantic match ({int(best_score*100)}%) against ontology class '{best_key}'")
            
        # 3. Post-process confidence adjustments
        # E.g. Exact matches get 1.0, high fuzzy gets 0.8-0.95, low fuzzy gets < 0.5
        confidence = best_score
        if unit and best_key in ["value", "ic50", "ec50", "potency", "toxicology"]:
            confidence = min(1.0, confidence + 0.1)
            reasons.append("Contextual boost: Valid unit bounds biological value.")
            
        if confidence < 0.50:
            best_key = "none"
            reasons = ["Below 50% confidence threshold. Manual verification required."]
            
        return {
            "column": column_name,
            "mapped_to": best_key,
            "confidence": round(confidence, 2),
            "confidence_score": int(confidence * 100),
            "exact_match": best_score >= 0.99,
            "fuzzy_match": 0.70 <= best_score < 0.99,
            "semantic_match": best_key != "none" and best_score >= 0.50,
            "reasons": reasons
        }
