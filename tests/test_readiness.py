import pytest
import pandas as pd
import numpy as np
from backend.processing.readiness_engine import (
    DatasetReadinessScorer,
    DescriptorReliabilityEngine,
    ChemicalDiversityScorer,
    ScaffoldLeakageAuditor,
    SuccessEstimator,
    ScientificIntelligenceEngine
)

@pytest.fixture
def sample_tox_dataset():
    """Generates a mock toxicology dataset for readiness auditing."""
    np.random.seed(42)
    n = 120
    
    # 1. Structure SMILES (benzene and aspirin analogues)
    smiles = ["CC(=O)Oc1ccccc1C(=O)O"] * 40 + ["c1ccccc1"] * 40 + [np.nan] * 20 + ["CC(=O)O"] * 20
    
    # 2. Endpoints and values
    endpoints = ["LC50"] * 100 + ["LD50"] * 20
    values = np.random.lognormal(mean=2.0, sigma=0.5, size=n)
    # Add negative values to test anomalous bounds check
    values[0] = -5.0
    # Add duplicate structure with highly divergent potency to test noise checks
    values[1] = 1.0
    values[2] = 1000.0 # 1000x difference -> logrange = 3.0
    
    units = ["uM"] * 110 + ["mg/kg"] * 10
    
    # 3. Descriptor sheets
    # Desc1: constant (near-zero variance check)
    desc_constant = np.ones(n)
    # Desc2: clean continuous descriptor
    desc_clean = np.random.normal(loc=150.0, scale=10.0, size=n)
    # Desc3: moderate sparsity (15% nulls)
    desc_sparse = np.random.normal(loc=5.0, scale=1.0, size=n)
    desc_sparse[:18] = np.nan
    # Desc4: critical calculation failures (80% nulls)
    desc_failed = np.random.normal(loc=0.0, scale=1.0, size=n)
    desc_failed[:96] = np.nan
    
    df = pd.DataFrame({
        "chemical_name": [f"Compound_{i}" for i in range(n)],
        "canonical_smiles": smiles,
        "endpoint": endpoints,
        "value": values,
        "unit": units,
        "MW": desc_clean,
        "LogP": desc_clean,
        "NearZeroVar": desc_constant,
        "SparseDesc": desc_sparse,
        "FailedDesc": desc_failed
    })
    
    mappings = {
        "chemical_name": "chemical_name",
        "canonical_smiles": "canonical_smiles",
        "endpoint": "endpoint",
        "value": "value",
        "unit": "unit"
    }
    
    return df, mappings


def test_dataset_readiness_scorer(sample_tox_dataset):
    df, mappings = sample_tox_dataset
    scorer = DatasetReadinessScorer()
    res = scorer.evaluate(df, mappings)
    
    assert "score" in res
    assert "tier" in res
    assert "breakdown" in res
    assert "deductions" in res
    assert isinstance(res["score"], float)
    
    # Check that structural completeness deducted points
    assert res["breakdown"]["structural_completeness"] < 100.0
    # Check that endpoint uniformity deducted points (mg/kg + uM)
    assert res["breakdown"]["endpoint_uniformity"] < 100.0


def test_descriptor_reliability_engine(sample_tox_dataset):
    df, mappings = sample_tox_dataset
    res = DescriptorReliabilityEngine.evaluate_descriptors(df, mappings)
    
    assert "keep" in res
    assert "moderate_warning" in res
    assert "recommend_pruning" in res
    assert "hard_exclusion" in res
    assert "descriptor_reliability_score" in res
    
    # Verify classifications mapping
    # FailedDesc has 80% missing -> hard_exclusion
    failed_names = [d["name"] for d in res["hard_exclusion"]]
    assert "FailedDesc" in failed_names
    
    # SparseDesc has 15% missing -> moderate_warning
    warning_names = [d["name"] for d in res["moderate_warning"]]
    assert "SparseDesc" in warning_names


def test_chemical_diversity_scorer(sample_tox_dataset):
    df, mappings = sample_tox_dataset
    res = ChemicalDiversityScorer.calculate_diversity(df, mappings)
    
    assert "status" in res
    assert "mean_tanimoto_similarity" in res
    assert "chemical_diversity_score" in res
    # Since RDKit may or may not be available in local environment, we check either skipped or success status
    assert res["status"] in ["Success", "Skipped"]


def test_scaffold_leakage_auditor(sample_tox_dataset):
    df, mappings = sample_tox_dataset
    res = ScaffoldLeakageAuditor.audit_scaffolds(df, mappings)
    
    assert "status" in res
    assert "scaffold_imbalance_level" in res
    assert res["status"] in ["Success", "Skipped"]


def test_success_estimator(sample_tox_dataset):
    df, mappings = sample_tox_dataset
    res = SuccessEstimator.run_level1_quick(df, mappings)
    
    assert "confidence" in res
    assert "baseline_performance" in res
    assert "metric_name" in res


def test_scientific_intelligence_engine(sample_tox_dataset):
    df, mappings = sample_tox_dataset
    
    # Test harmonization audit
    harm_res = ScientificIntelligenceEngine.audit_endpoint_harmonization(df, mappings)
    assert "harmonized" in harm_res
    assert harm_res["harmonized"] is False # Multi-unit present
    
    # Test noise detection
    noise_res = ScientificIntelligenceEngine.detect_experimental_noise(df, mappings)
    assert "noise_detected" in noise_res
    assert noise_res["noise_detected"] is True # 1000x drift present
    assert len(noise_res["conflicts"]) > 0
