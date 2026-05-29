import pytest
from backend.core.ecotox.ecotox_classifier import EcotoxClassifier

def test_ecotox_column_classification():
    # Test complex messy headers
    res = EcotoxClassifier.classify("96h_LC50_mg/L (Rainbow Trout)")
    assert res["endpoint"] == "LC50"
    assert res["species"] == "fish"
    assert res["duration"] == "96h"
    assert res["unit"] == "mg/L"
    assert res["test_type"] == "Acute Aquatic Toxicity"
    assert res["confidence"] >= 0.8

    res = EcotoxClassifier.classify("OECD 201 Alga EC50 (ug/L)")
    assert res["endpoint"] == "EC50"
    assert res["species"] == "algae"
    assert res["unit"] == "µg/L"
    assert res["regulatory_framework"] == "OECD"
    assert res["confidence"] >= 0.8

    res = EcotoxClassifier.classify("BCF (lipid normalized)")
    assert res["environmental_fate"] == "Bioaccumulation (BCF)"
    assert res["confidence"] >= 0.5

def test_dataset_type_classification():
    # Test aquatic toxicity dataset classification
    columns = ["smiles", "96h_LC50_mg/L (Rainbow Trout)", "daphnia_EC50"]
    mappings = {"smiles": "canonical_smiles", "96h_LC50_mg/L (Rainbow Trout)": "value", "daphnia_EC50": "value"}
    dtype = EcotoxClassifier.classify_dataset_type(columns, mappings)
    assert dtype == "Aquatic Toxicity Dataset"

    # Test environmental fate dataset classification
    columns = ["smiles", "BCF", "biodegradability"]
    mappings = {"smiles": "canonical_smiles", "BCF": "value", "biodegradability": "value"}
    dtype = EcotoxClassifier.classify_dataset_type(columns, mappings)
    assert dtype == "Environmental Fate Dataset"

    # Test OECD regulatory dataset classification
    columns = ["smiles", "oecd_201_ec50", "oecd_202"]
    mappings = {"smiles": "canonical_smiles", "oecd_201_ec50": "value", "oecd_202": "value"}
    dtype = EcotoxClassifier.classify_dataset_type(columns, mappings)
    assert dtype == "OECD Regulatory Dataset"

def test_toxicological_safety_validation():
    # 1. Test LC50 + Human warning
    columns = ["smiles", "human_LC50_value"]
    mappings = {"smiles": "canonical_smiles", "human_LC50_value": "value"}
    warnings = EcotoxClassifier.validate_toxicological_safety(mappings, columns)
    assert any("LC50 endpoint mapped with Human species" in w for w in warnings)

    # 2. Test Fish + Oral route warning
    columns = ["smiles", "fish_oral_gavage_LD50"]
    mappings = {"smiles": "canonical_smiles", "fish_oral_gavage_LD50": "value"}
    warnings = EcotoxClassifier.validate_toxicological_safety(mappings, columns)
    assert any("Fish test species mapped with Oral exposure route" in w for w in warnings)

    # 3. Test NOEC + Missing Duration warning
    columns = ["smiles", "NOEC_mgkg"]
    mappings = {"smiles": "canonical_smiles", "NOEC_mgkg": "value"}
    warnings = EcotoxClassifier.validate_toxicological_safety(mappings, columns)
    assert any("Detected NOEC chronic endpoint without an explicit study Exposure Duration" in w for w in warnings)

    # 4. Correct setup -> No warnings
    columns = ["smiles", "96h_LC50_fish"]
    mappings = {"smiles": "canonical_smiles", "96h_LC50_fish": "value"}
    warnings = EcotoxClassifier.validate_toxicological_safety(mappings, columns)
    assert len(warnings) == 0
