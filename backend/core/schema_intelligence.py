from typing import List, Dict, Any
from backend.core.mapping_confidence_engine import MappingConfidenceEngine
from backend.core.ecotox.ecotox_classifier import EcotoxClassifier

class SchemaIntelligenceEngine:
    """
    Top-level API interface that orchestrates the detection sequence across all columns.
    Enriched with Ecotoxicology & Regulatory Toxicology Ontology overlay mappings.
    """
    
    @staticmethod
    def infer_schema(columns: List[str]) -> List[Dict[str, Any]]:
        inferred_mappings = []
        
        for col in columns:
            # 1. Base mapping confidence
            mapping_result = MappingConfidenceEngine.evaluate_column(col)
            
            # 2. Advanced Ecotox / Regulatory Classification Overlay
            ecotox_intel = EcotoxClassifier.classify(col)
            
            # Expose ecotox payload to the React frontend
            mapping_result["ecotox"] = ecotox_intel
            
            # If Ecotox found a strong endpoint, it might override a weak base mapping
            if ecotox_intel["endpoint"] and mapping_result["confidence"] < 0.8:
                # Ecotox found a high-value endpoint inside a messy string
                mapping_result["mapped_to"] = "endpoint"
                mapping_result["confidence"] = max(mapping_result["confidence"], ecotox_intel["confidence"])
                
            # Merge reasons
            for r in ecotox_intel["reasons"]:
                if r not in mapping_result["reasons"]:
                    mapping_result["reasons"].append(r)
                
            inferred_mappings.append(mapping_result)
            
        return inferred_mappings
