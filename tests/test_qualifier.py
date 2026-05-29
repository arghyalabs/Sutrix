import pytest
import math
from backend.utils.qualifier_parser import QualifierParser, QualifierType

@pytest.fixture
def parser():
    return QualifierParser()

def test_exact_numeric(parser):
    result = parser.parse("100.5")
    assert result is not None
    assert result.value == 100.5
    assert result.qualifier == QualifierType.EXACT
    assert result.unit == ""
    assert result.is_censored is False
    assert result.qsar_ready is True

def test_scientific_notation(parser):
    result = parser.parse("1.2e-05")
    assert result is not None
    assert result.value == 1.2e-5
    assert result.qualifier == QualifierType.EXACT
    assert result.is_censored is False
    assert result.qsar_ready is True

def test_approximate_values(parser):
    result1 = parser.parse("~ 50")
    assert result1 is not None
    assert result1.value == 50.0
    assert result1.qualifier == QualifierType.APPROXIMATE
    assert result1.qsar_ready is True
    
    result2 = parser.parse("ca. 100")
    assert result2 is not None
    assert result2.value == 100.0
    assert result2.qualifier == QualifierType.APPROXIMATE
    assert result2.qsar_ready is True

def test_messy_spacing_with_units(parser):
    result = parser.parse(">  50.5 mg/kg")
    assert result is not None
    assert result.value == 50.5
    assert result.qualifier == QualifierType.GREATER_THAN
    assert result.unit == "mg/kg"
    assert result.is_censored is True
    assert result.qsar_ready is False

def test_nd_values(parser):
    result = parser.parse("ND")
    assert result is not None
    assert math.isnan(result.value)
    assert result.qualifier == QualifierType.NOT_DETECTED
    assert result.unit == ""
    assert result.is_censored is True
    assert result.qsar_ready is False

def test_limit_of_detection(parser):
    result = parser.parse("<LOD")
    assert result is not None
    assert math.isnan(result.value)
    assert result.qualifier == QualifierType.BELOW_LOD
    assert result.is_censored is True

def test_inequalities(parser):
    result = parser.parse("<= 10.0")
    assert result is not None
    assert result.value == 10.0
    assert result.qualifier == QualifierType.LESS_OR_EQUAL
    assert result.is_censored is True
    assert result.qsar_ready is False

def test_edge_cases(parser):
    assert parser.parse("") is None
    assert parser.parse(None) is None
    
    # Just a number directly
    result = parser.parse(42.0)
    assert result is not None
    assert result.value == 42.0
    assert result.qualifier == QualifierType.EXACT
