import pytest
from backend.core.schema_intelligence import SchemaIntelligenceEngine
from backend.core.ecotox.ecotox_classifier import EcotoxClassifier

def test_schema_intelligence_inference():
    # Test a set of headers representing a messy scientific dataset
    columns = [
        "SMILES Structure",
        "CAS RN",
        "96h LC50 Value (mg/L)",
        "Rainbow Trout",
        "OECD 203 framework",
        "Inequality relation"
    ]
    
    results = SchemaIntelligenceEngine.infer_schema(columns)
    
    # Assert correct length
    assert len(results) == len(columns)
    
    # 1. SMILES Structure -> mapped to canonical_smiles
    smiles_res = next(r for r in results if r["column"] == "SMILES Structure")
    assert smiles_res["mapped_to"] == "canonical_smiles"
    assert smiles_res["confidence"] >= 0.8
    
    # 2. CAS RN -> cas_number
    cas_res = next(r for r in results if r["column"] == "CAS RN")
    assert cas_res["mapped_to"] == "cas_number"
    assert cas_res["confidence"] >= 0.8
    
    # 3. 96h LC50 Value (mg/L) -> endpoint with ecotox overlay
    lc50_res = next(r for r in results if r["column"] == "96h LC50 Value (mg/L)")
    assert lc50_res["mapped_to"] in ["endpoint", "regression_target", "value"]  # Ecotox overlay could map it to endpoint or fallback value
    assert lc50_res["ecotox"]["endpoint"] == "LC50"
    assert lc50_res["ecotox"]["duration"] == "96h"
    assert lc50_res["ecotox"]["unit"] == "mg/L"
    
    # 4. Rainbow Trout -> organism / species details
    trout_res = next(r for r in results if r["column"] == "Rainbow Trout")
    assert trout_res["ecotox"]["species"] == "fish"
    
    # 5. OECD 203 framework -> regulatory framework
    oecd_res = next(r for r in results if r["column"] == "OECD 203 framework")
    assert oecd_res["ecotox"]["regulatory_framework"] == "OECD"

def test_messy_headers_fallback():
    # Headers with typos/unusual capitalization and formats
    columns = [
        "cmpd structure",
        "Median Lethal Conc. (LC_50)",
        "organism name"
    ]
    
    results = SchemaIntelligenceEngine.infer_schema(columns)
    
    # Structure mapping fallback
    struct_res = next(r for r in results if r["column"] == "cmpd structure")
    assert struct_res["mapped_to"] == "canonical_smiles"
    
    # LC50 fuzzy parsing fallback
    lc50_res = next(r for r in results if r["column"] == "Median Lethal Conc. (LC_50)")
    assert lc50_res["ecotox"]["endpoint"] == "LC50"
    
    # Organism mapping fallback
    org_res = next(r for r in results if r["column"] == "organism name")
    assert org_res["mapped_to"] in ["organism", "species"] or org_res["ecotox"]["species"] is not None
