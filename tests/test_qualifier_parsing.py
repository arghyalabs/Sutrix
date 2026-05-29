import pytest
from backend.core.ecotox.qualifier_parser import QualifierParser

def test_qualifier_extraction():
    # Test standard values with math prefixes
    res = QualifierParser.parse(">= 50 ppm")
    assert res["operator"] == ">="
    assert res["value"] == 50.0
    assert res["unit"] == "ppm"
    assert res["qsar_ready"] is True

    res = QualifierParser.parse("<= 1 µM")
    assert res["operator"] == "<="
    assert res["value"] == 1.0
    assert res["unit"] == "µM"
    assert res["qsar_ready"] is True

    res = QualifierParser.parse("> 100 mg/L")
    assert res["operator"] == ">"
    assert res["value"] == 100.0
    assert res["unit"] == "mg/L"
    assert res["qsar_ready"] is True

def test_qualifier_codes():
    # Test non-numeric indicators
    res = QualifierParser.parse("BQL")
    assert res["operator"] == "BQL"
    assert res["value"] is None
    assert res["qsar_ready"] is False

    res = QualifierParser.parse("LOD")
    assert res["operator"] == "LOD"
    assert res["value"] is None

def test_qualifier_column_aliases():
    # Test column indicator logic
    assert QualifierParser.is_qualifier_column("inequality") is True
    assert QualifierParser.is_qualifier_column("relation") is True
    assert QualifierParser.is_qualifier_column("smiles") is False
