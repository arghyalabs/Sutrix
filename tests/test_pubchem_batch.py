import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from backend.api_clients.pubchem_plugin import PubChemPlugin
from backend.api_clients.plugin_manager import ScientificEnrichmentManager
from backend.api_clients.base_plugin import PluginResult

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP Error {self.status_code}")

@pytest.fixture
def manager(tmp_path):
    mgr = ScientificEnrichmentManager()
    mgr.pubchem.cache_dir = tmp_path
    mgr.pubchem.cache_file = tmp_path / "test_cache.json"
    mgr.pubchem._memory_cache = {}
    mgr.pubchem.rate_limit_delay = 0.0
    return mgr

@patch('requests.post')
def test_fetch_batch_success(mock_post, manager):
    # Mock bulk POST response
    mock_post.return_value = MockResponse({
        "PropertyTable": {
            "Properties": [
                {"CID": 2244, "MolecularWeight": "180.16", "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O"},
                {"CID": 1983, "MolecularWeight": "151.16", "CanonicalSMILES": "CC(=O)NC1=CC=C(C=C1)O"}
            ]
        }
    })
    
    smiles_list = ["CC(=O)OC1=CC=CC=C1C(=O)O", "CC(=O)NC1=CC=C(C=C1)O"]
    results = manager.pubchem.fetch_batch(smiles_list)
    
    assert len(results) == 2
    assert results[smiles_list[0]].success is True
    assert results[smiles_list[0]].data["CID"] == 2244
    assert results[smiles_list[1]].success is True
    assert results[smiles_list[1]].data["CID"] == 1983

@patch('requests.post')
@patch('requests.get')
def test_hybrid_enrichment_logic(mock_get, mock_post, manager):
    # Data has 2 SMILES and 1 Name
    df = pd.DataFrame({
        "Compound": ["Aspirin", "Tylenol", "Advil"],
        "SMILES": ["CC(=O)OC1=CC=CC=C1C(=O)O", "CC(=O)NC1=CC=C(C=C1)O", None],
        "Value_qsar_ready": [True, True, True]
    })
    
    mappings = {"Compound": "chemical_id", "SMILES": "smiles", "Value": "value"}
    
    # Mock Batch POST for SMILES
    mock_post.return_value = MockResponse({
        "PropertyTable": {
            "Properties": [
                {"CID": 2244, "MolecularWeight": "180.16"},
                {"CID": 1983, "MolecularWeight": "151.16"}
            ]
        }
    })
    
    # Mock Single GET for Name (Advil)
    mock_get.return_value = MockResponse({
        "PropertyTable": {
            "Properties": [
                {"CID": 3672, "MolecularWeight": "206.28"} # Advil CID
            ]
        }
    })
    
    enriched_df, logs = manager.enrich_dataframe(df, mappings)
    
    # Assertions
    assert mock_post.called
    assert mock_get.called
    
    # Verify CID overwrite deduplication
    assert enriched_df.at[0, "Compound"] == "Aspirin"
    assert enriched_df.at[1, "Compound"] == "Tylenol"
    assert enriched_df.at[2, "Compound"] == "Advil"
    
    assert enriched_df.at[0, "PubChem_MW"] == 180.16
    assert enriched_df.at[2, "PubChem_MW"] == 206.28
    
    # Verify QSAR ready persists
    assert enriched_df.at[0, "Value_qsar_ready"] == True

@patch('requests.post')
def test_missing_mw_qsar_flag(mock_post, manager):
    df = pd.DataFrame({
        "SMILES": ["FakeSMILES"],
        "Compound": ["FakeComp"],
        "Value_qsar_ready": [True]
    })
    mappings = {"SMILES": "smiles", "Compound": "chemical_id", "Value": "value"}
    
    # Mock returning NO MW
    mock_post.return_value = MockResponse({
        "PropertyTable": {
            "Properties": [
                {"CID": 9999} 
            ]
        }
    })
    
    enriched_df, logs = manager.enrich_dataframe(df, mappings)
    
    # Missing MW means qsar_ready MUST become False
    assert pd.isna(enriched_df.at[0, "PubChem_MW"])
    assert enriched_df.at[0, "Value_qsar_ready"] == False
