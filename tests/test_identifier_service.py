import pytest
import asyncio
import pandas as pd
from unittest.mock import patch, MagicMock
from backend.normalization.identifier_service import ChemicalIdentifierService
from backend.pipeline.orchestrator import AsyncEnrichmentOrchestrator
from backend.database.manager import DatabaseManager
from backend.database.session import init_db

@pytest.fixture(autouse=True)
def setup_test_db():
    # Initialize the centralized DB schema synchronously before running each test
    init_db()

def test_compound_name_to_smiles():
    service = ChemicalIdentifierService()
    # Mock pubchempy response to avoid real network call in unit test
    with patch('pubchempy.get_compounds') as mock_get:
        mock_comp = MagicMock()
        mock_comp.cid = 2244
        mock_comp.isomeric_smiles = "CC(=O)Oc1ccccc1C(=O)O"
        mock_comp.canonical_smiles = "CC(=O)Oc1ccccc1C(=O)O"
        mock_comp.smiles = "CC(=O)Oc1ccccc1C(=O)O"
        mock_comp.synonyms = ["Aspirin"]
        mock_comp.iupac_name = "2-acetyloxybenzoic acid"
        mock_get.return_value = [mock_comp]

        res = service.resolve("Aspirin", id_type="name")
        
        assert res["status"] == "success"
        assert res["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
        assert res["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        assert res["cid"] == "2244"

def test_smiles_to_canonical_smiles():
    service = ChemicalIdentifierService()
    
    # Offline normalization test - should succeed without pubchempy calls
    res = service.resolve("CC(=O)OC1=CC=CC=C1C(=O)O", id_type="smiles")
    
    assert res["status"] == "success"
    assert res["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert res["inchikey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
    assert res["molecular_formula"] == "C9H8O4"

def test_cache_retrieval():
    service = ChemicalIdentifierService()
    
    # Pre-seed cache
    res1 = service.resolve("CC(=O)OC1=CC=CC=C1C(=O)O", id_type="smiles")
    assert res1["status"] == "success"
    
    # Query again - should be cache hit
    res2 = service.resolve("CC(=O)OC1=CC=CC=C1C(=O)O", id_type="smiles")
    assert res2["source"] == "cache"
    assert res2["status"] == "success"
    assert res2["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"

def test_invalid_compounds():
    service = ChemicalIdentifierService()
    
    # Completely invalid string that isn't a valid name/CAS/SMILES
    with patch('pubchempy.get_compounds', return_value=[]):
        res = service.resolve("xyzzy_invalid_compound_999", id_type="name")
        assert res["status"] == "not_found"
        assert res["canonical_smiles"] == ""
        
    # Invalid SMILES
    res_smiles = service.resolve("CCCC(=O)O=O", id_type="smiles")
    assert res_smiles["status"] == "invalid_structure"

def test_batch_processing():
    orchestrator = AsyncEnrichmentOrchestrator()
    orchestrator.initialize()
    
    identifiers = ["CC(=O)OC1=CC=CC=C1C(=O)O", "CC(=O)NC1=CC=C(C=C1)O"]
    
    # Run process_identifiers concurrently
    results = orchestrator.process_identifiers(identifiers, id_type="smiles", include_mordred=False)
    
    assert len(results) == 2
    assert "CC(=O)OC1=CC=CC=C1C(=O)O" in results
    assert results["CC(=O)OC1=CC=CC=C1C(=O)O"]["success"] is True
    assert results["CC(=O)OC1=CC=CC=C1C(=O)O"]["data"]["canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"

def test_dataframe_merge_consistency():
    orchestrator = AsyncEnrichmentOrchestrator()
    
    df = pd.DataFrame({
        "ChemicalName": ["Aspirin", "Acetaminophen"],
        "SMILES": ["CC(=O)OC1=CC=CC=C1C(=O)O", "CC(=O)NC1=CC=C(C=C1)O"]
    })
    
    mappings = {
        "ChemicalName": "chemical_id",
        "SMILES": "canonical_smiles"
    }
    
    selected_descriptors = ["canonical_smiles", "InChIKey", "Molecular_Formula"]
    
    enriched_df, logs = orchestrator.enrich_dataframe_async(
        df=df,
        mappings=mappings,
        selected_descriptors=selected_descriptors,
        api_properties=["canonical_smiles", "InChIKey", "MolecularFormula"]
    )
    
    # Assert column consistency and valid merge
    assert "canonical_smiles" in enriched_df.columns
    assert "InChIKey" in enriched_df.columns
    assert "Molecular_Formula" in enriched_df.columns
    
    # Assert exact standardized SMILES populated
    assert enriched_df.at[0, "canonical_smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
    assert enriched_df.at[1, "canonical_smiles"] == "CC(=O)Nc1ccc(O)cc1"
    assert enriched_df.at[0, "InChIKey"] == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
