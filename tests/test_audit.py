import pytest
import pandas as pd
from backend.validation.endpoint_validator import EndpointValidator, UnitType
from backend.processing.auditor import ScientificAuditor

@pytest.fixture
def clean_data():
    """Perfectly clean dataset, expecting 100 score."""
    return pd.DataFrame({
        'Chemical': ['ChemA', 'ChemB'],
        'Test_Endpoint': ['LD50', 'LC50'],
        'Result_Value': [500, 250],
        'Result_Unit': ['mg/kg', 'mg/L']
    })

@pytest.fixture
def missing_data_yellow():
    """Dataset with 25% missing values (Moderate/Yellow tier)."""
    return pd.DataFrame({
        'Chemical': ['ChemA', 'ChemB', 'ChemC', 'ChemD'],
        'Test_Endpoint': ['LD50', 'LC50', None, 'NOAEL'],
        'Result_Value': [500, 250, 10, 50],
        'Result_Unit': ['mg/kg', 'mg/L', 'mg/kg', 'mg/kg']
    })

@pytest.fixture
def inconsistent_data():
    """Dataset with Unit-Endpoint mismatch."""
    return pd.DataFrame({
        'Chemical': ['ChemA', 'ChemB'],
        'Test_Endpoint': ['LD50', 'LC50'],
        'Result_Value': [500, 250],
        # LD50 with mg/L is a mismatch (mass/volume for mass/weight endpoint)
        'Result_Unit': ['mg/L', 'mg/L'] 
    })

@pytest.fixture
def high_variance_data():
    """Dataset with delta log10 >= 1."""
    return pd.DataFrame({
        'Chemical': ['ChemA', 'ChemA'],
        'Test_Endpoint': ['LD50', 'LD50'],
        # Min = 10, Max = 100. log10(100) - log10(10) = 2 - 1 = 1.0 (Hits threshold!)
        'Result_Value': [10, 100], 
        'Result_Unit': ['mg/kg', 'mg/kg']
    })

@pytest.fixture
def mappings():
    return {
        'Chemical': 'chemical_name',
        'Test_Endpoint': 'endpoint',
        'Result_Value': 'value',
        'Result_Unit': 'unit'
    }

def test_endpoint_validator():
    validator = EndpointValidator()
    # Test normalization
    assert validator.normalize_endpoint('lethal dose 50').name == 'LD50'
    assert validator.normalize_endpoint('NOAEL').name == 'NOAEL'
    
    # Test unit consistency
    assert validator.validate_unit_consistency('LD50', 'mg/kg') is True
    assert validator.validate_unit_consistency('LD50', 'g/kg') is True
    assert validator.validate_unit_consistency('LD50', 'mg/L') is False  # Mass/volume for LD50
    assert validator.validate_unit_consistency('LC50', 'mg/L') is True
    assert validator.validate_unit_consistency('LC50', 'mg/kg') is False # Mass/weight for LC50

def test_auditor_clean(clean_data, mappings):
    auditor = ScientificAuditor()
    report = auditor.audit(clean_data, mappings)
    
    assert report.data_health_tier == "High Quality (Green)"
    assert report.quality_score == 100.0
    assert len(report.findings) == 0

def test_auditor_missing_values(missing_data_yellow, mappings):
    auditor = ScientificAuditor()
    report = auditor.audit(missing_data_yellow, mappings)
    
    assert report.data_health_tier == "Moderate Quality (Yellow)"
    assert report.quality_score == 90.0 # 100 - 10 penalty for moderate missing
    assert len(report.findings) == 1
    assert report.findings[0].category == 'missing_values'
    assert report.findings[0].severity == 'warning'

def test_auditor_inconsistency(inconsistent_data, mappings):
    auditor = ScientificAuditor()
    report = auditor.audit(inconsistent_data, mappings)
    
    # One inconsistency penalty = -10
    assert report.quality_score == 90.0
    finding = next((f for f in report.findings if f.category == 'scientific_inconsistency'), None)
    assert finding is not None
    assert finding.affected_records == 1 # Only the LD50 mg/L row

def test_auditor_variance_penalty(high_variance_data, mappings):
    auditor = ScientificAuditor()
    report = auditor.audit(high_variance_data, mappings)
    
    # One high variance pair = 2 points penalty
    assert report.quality_score == 98.0
    finding = next((f for f in report.findings if f.category == 'variance_penalty'), None)
    assert finding is not None
    assert finding.affected_records == 1
