import re
from typing import Dict, Any, List

from backend.core.ecotox.species_detector import SpeciesDetector
from backend.core.ecotox.duration_parser import DurationParser
from backend.core.ecotox.qualifier_parser import QualifierParser
from backend.core.ecotox.exposure_engine import ExposureEngine
from backend.core.ecotox.endpoint_ontology import EndpointOntology
from backend.core.ecotox.environmental_fate_detector import EnvironmentalFateDetector
from backend.core.ecotox.guideline_detector import GuidelineDetector
from backend.core.ecotox.dose_normalizer import DoseNormalizer
from backend.core.unit_normalizer import UnitNormalizer

class EcotoxClassifier:
    """
    Orchestration Engine that integrates species, duration, endpoint, 
    exposure model, guidelines, and environmental fate ontologies contextually.
    Behaves like a professional environmental toxicologist.
    """

    @staticmethod
    def classify(column_name: str) -> Dict[str, Any]:
        """
        Extracts structured toxicological ontology parameters from a column name.
        """
        result = {
            "endpoint": None,
            "species": None,
            "duration": None,
            "unit": None,
            "test_type": None,
            "qualifier": None,
            "environmental_fate": None,
            "regulatory_framework": None,
            "confidence": 0.0,
            "reasons": []
        }

        clean_name = column_name.strip()
        text_lower = clean_name.lower()

        # 1. Detect Qualifier
        # e.g. column has specific qualifiers or math expressions
        qual_res = QualifierParser.parse(clean_name)
        if qual_res["operator"] != "=":
            result["qualifier"] = qual_res["operator"]
            result["reasons"].append(f"detected qualifier operator: '{qual_res['operator']}'")

        # 2. Detect standard measurement unit
        clean_stripped, unit = UnitNormalizer.detect_and_strip_unit(clean_name)
        if unit:
            result["unit"] = unit
            result["reasons"].append(f"detected concentration unit: {unit}")
            
        # 3. Detect Duration
        duration, d_conf = DurationParser.detect_duration(clean_stripped)
        if duration:
            result["duration"] = duration
            result["reasons"].append(f"detected exposure duration: {duration}")

        # 4. Detect Species
        species, s_conf = SpeciesDetector.detect_species(clean_stripped)
        if species != "unknown":
            result["species"] = species
            result["reasons"].append(f"detected test species: {species}")

        # 5. Detect Endpoint category
        category, e_conf = EndpointOntology.identify_endpoint_category(clean_stripped)
        if category != "unknown":
            # Extract standard endpoint acronyms
            endpoints = ["lc50", "ld50", "ec50", "noec", "loec", "noael", "loael", "bmd", "bmdl"]
            text_norm = re.sub(r'[^a-z0-9]', '', text_lower)
            for ep in endpoints:
                if ep in text_norm:
                    result["endpoint"] = ep.upper()
                    result["reasons"].append(f"detected endpoint acronym: {ep.upper()}")
                    break
            if not result["endpoint"]:
                result["endpoint"] = category
                result["reasons"].append(f"detected endpoint category: {category}")

        # 6. Detect Environmental Fate
        fate, f_conf = EnvironmentalFateDetector.detect_environmental_fate(clean_stripped)
        if fate != "unknown":
            result["environmental_fate"] = fate
            result["reasons"].append(f"detected environmental fate: {fate}")

        # 7. Detect Regulatory Guideline
        guide_res = GuidelineDetector.detect_guideline(clean_stripped)
        if guide_res["guideline"]:
            result["regulatory_framework"] = guide_res["framework"]
            result["reasons"].append(f"detected regulatory framework: {guide_res['framework']} ({guide_res['guideline']})")

        # 8. Infer Test Type Contextually (Acute vs Chronic / Aquatic vs Mammalian)
        days = None
        if result["duration"]:
            norm_d = DurationParser.normalize_duration(result["duration"])
            days = norm_d.get("standardized_days")
            
        t_type, t_conf = ExposureEngine.infer_test_type(clean_stripped, duration_days=days)
        if t_type != "unknown":
            result["test_type"] = t_type
            result["reasons"].append(f"inferred study design: {t_type}")
            
        # Refine test type with species context if general Acute/Chronic Toxicity or unknown
        if result["test_type"] in ["Acute Toxicity", "Chronic Toxicity", "unknown", None]:
            if result["species"] in ["fish", "daphnia", "algae"]:
                is_acute = (days and days <= 4.0) or (result["test_type"] == "Acute Toxicity") or (result["duration"] in ["24h", "48h", "72h", "96h"])
                result["test_type"] = "Acute Aquatic Toxicity" if is_acute else "Chronic Aquatic Toxicity"
                result["reasons"].append(f"refined aquatic study design: {result['test_type']}")
            elif result["species"] in ["rat", "mouse", "dog", "primate", "rabbit"]:
                is_chronic = (days and days >= 28.0) or (result["test_type"] == "Chronic Toxicity")
                result["test_type"] = "Chronic Mammalian Toxicity" if is_chronic else "Acute Mammalian Toxicity"
                result["reasons"].append(f"refined mammalian study design: {result['test_type']}")

        # 9. GHS Classification detection
        if "ghs" in text_lower or "hazard" in text_lower or "signal_word" in text_lower:
            result["regulatory_framework"] = "GHS / Hazard Classification"
            result["reasons"].append("identified GHS hazard labeling field")

        # Calculate composite confidence score
        if len(result["reasons"]) > 0:
            result["confidence"] = min(1.0, 0.35 + (len(result["reasons"]) * 0.15))

        return result

    @staticmethod
    def classify_dataset_type(columns: List[str], mappings: Dict[str, str]) -> str:
        """
        Classifies the entire dataset category contextually based on the mappings and columns.
        Supports standard categories:
        - Aquatic Toxicity Dataset
        - ADMET Dataset
        - QSAR Descriptor Dataset
        - Environmental Fate Dataset
        - OECD Regulatory Dataset
        - Clinical Toxicology Dataset
        - Bioassay Dataset
        """
        mapped_values = set(mappings.values())
        
        # 1. Gather all ecotox classifications
        classifications = [EcotoxClassifier.classify(col) for col in columns]
        
        has_bcf_or_fate = any(c.get("environmental_fate") is not None for c in classifications)
        has_oecd = any(c.get("regulatory_framework") == "OECD" for c in classifications)
        has_aquatic_species = any(c.get("species") in ["fish", "daphnia", "algae"] for c in classifications)
        has_mammal_species = any(c.get("species") in ["rat", "mouse", "dog", "primate", "human"] for c in classifications)
        has_descriptors = any("descriptor" in col.lower() or "mordred" in col.lower() or col in ["MW", "LogP", "TPSA"] for col in columns)

        # Dataset heuristics
        if has_bcf_or_fate:
            return "Environmental Fate Dataset"
        if has_oecd:
            return "OECD Regulatory Dataset"
        if has_aquatic_species:
            return "Aquatic Toxicity Dataset"
        if has_mammal_species:
            if any(c.get("species") == "human" for c in classifications):
                return "Clinical Toxicology Dataset"
            return "Bioassay Dataset"
        if has_descriptors:
            return "QSAR Descriptor Dataset"
        if "value" in mapped_values and ("smiles" in mapped_values or "canonical_smiles" in mapped_values):
            return "ADMET Dataset"

        return "Bioassay Dataset"

    @staticmethod
    def validate_toxicological_safety(mappings: Dict[str, str], columns: List[str]) -> List[str]:
        """
        Warns users about impossible toxicological or regulatory parameter combinations.
        Examples:
        - LC50 + Human (LC50 is for in vivo animal/environmental testing, not direct human potency)
        - Fish + Oral Exposure (Fish are typically exposed via water/aqueous dissolved medium, not direct oral gavage)
        - NOEC + Missing Duration (NOEC/chronic thresholds require an explicit study time point to be regulatory compliant)
        """
        warnings = []
        
        # Build column index to class maps
        class_map = {col: EcotoxClassifier.classify(col) for col in columns}
        
        has_human = False
        has_fish = False
        has_lc50 = False
        has_oral = False
        has_noec = False
        has_duration = False

        # Scan mapped variables
        for col, target in mappings.items():
            if target == "none":
                continue
                
            intel = class_map.get(col, {})
            species = intel.get("species")
            endpoint = intel.get("endpoint")
            duration = intel.get("duration")
            test_type = intel.get("test_type")
            
            if species == "human":
                has_human = True
            if species == "fish":
                has_fish = True
            if endpoint in ["LC50", "Lethality / Acute Potency"]:
                has_lc50 = True
            if endpoint == "NOEC":
                has_noec = True
            if duration:
                has_duration = True
                
            # Direct route checks
            col_lower = col.lower()
            if "oral" in col_lower or "gavage" in col_lower:
                has_oral = True

        if has_human and has_lc50:
            warnings.append("⚠️ Potentially invalid design: Detected LC50 endpoint mapped with Human species (LC50 is typically an in vivo animal/environmental metric).")
            
        if has_fish and has_oral:
            warnings.append("⚠️ Exposure warning: Fish test species mapped with Oral exposure route (aquatic organisms are standardly exposed via water/ambient dissolved medium rather than direct oral gavage).")
            
        if has_noec and not has_duration:
            warnings.append("⚠️ Regulatory non-compliance: Detected NOEC chronic endpoint without an explicit study Exposure Duration (required for OECD/REACH validation compliance).")

        return warnings
