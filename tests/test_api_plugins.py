import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from backend.api_clients.base_plugin import PluginResult
from backend.api_clients.pubchem_plugin import PubChemPlugin
from backend.api_clients.plugin_manager import ScientificEnrichmentManager
import json

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
    manager = ScientificEnrichmentManager()
    manager.pubchem.cache_dir = tmp_path # Override cache dir to tmp
    manager.pubchem.cache_file = tmp_path / "test_cache.json"
    manager.pubchem._memory_cache = {}
    manager.pubchem.rate_limit_delay = 0.0 # Fast tests
    return manager

@patch('requests.get')
def test_pubchem_success(mock_get, manager):
    # Mock single result
    mock_get.return_value = MockResponse({
        "PropertyTable": {
            "Properties": [{
                "CID": 2244,
                "MolecularWeight": "180.16",
                "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O"
            }]
        }
    })
    
    result = manager.pubchem.fetch("Aspirin")
    assert result.success is True
    assert result.data["MolecularWeight"] == "180.16"
    assert result.ambiguous is False

@patch('requests.get')
def test_pubchem_ambiguous(mock_get, manager):
    # Mock multiple results
    mock_get.return_value = MockResponse({
        "PropertyTable": {
            "Properties": [
                {"CID": 111, "MolecularWeight": "100.0"},
                {"CID": 222, "MolecularWeight": "100.0"}
            ]
        }
    })
    
    result = manager.pubchem.fetch("GenericName")
    assert result.success is False
    assert result.ambiguous is True
    assert result.candidate_ids == ["111", "222"]
    assert result.error == "AMBIGUOUS_IDENTITY"

def test_enrich_dataframe_smiles_priority(manager):
    df = pd.DataFrame({
        "Name": ["Aspirin"],
        "SMILES": ["CC(=O)OC1=CC=CC=C1C(=O)O"]
    })
    mappings = {"Name": "chemical_id", "SMILES": "smiles"}
    
    # Mock fetch_batch so we don't actually hit API
    with patch.object(manager.pubchem, 'fetch_batch', return_value={
        "CC(=O)OC1=CC=CC=C1C(=O)O": PluginResult(
            success=True, 
            data={"MolecularWeight": "180.16", "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O"}
        )
    }) as mock_fetch_batch:
        enriched_df, logs = manager.enrich_dataframe(df, mappings)
        
        # Ensure it was called with SMILES, not Name
        mock_fetch_batch.assert_called_once()
        assert enriched_df.at[0, "PubChem_MW"] == 180.16

def test_enrich_dataframe_data_discrepancy(manager):
    df = pd.DataFrame({
        "Name": ["Aspirin"],
        "MW": [100.0] # Intentionally wrong MW to trigger discrepancy
    })
    mappings = {"Name": "chemical_id", "MW": "molecular_weight"}
    
    with patch.object(manager.pubchem, 'fetch', return_value=PluginResult(
        success=True, 
        data={"MolecularWeight": "180.16", "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O"}
    )):
        enriched_df, logs = manager.enrich_dataframe(df, mappings)
        
        assert enriched_df.at[0, "PubChem_MW"] == 180.16
        # Assert discrepancy was logged
        assert len(logs) == 1
        assert logs[0]["issue"] == "Data Discrepancy"

def test_local_caching(tmp_path):
    # Test that caching writes to disk and reads from disk
    plugin = PubChemPlugin(cache_enabled=True)
    plugin.cache_dir = tmp_path
    plugin.cache_file = tmp_path / "test_cache.json"
    
    # Pre-populate cache
    result = PluginResult(success=True, data={"MolecularWeight": "123.4"})
    plugin._cache_result("test_id", "name", result)
    
    assert plugin.cache_file.exists()
    
    # Create new plugin instance pointed at same file
    plugin2 = PubChemPlugin(cache_enabled=True)
    plugin2.cache_dir = tmp_path
    plugin2.cache_file = tmp_path / "test_cache.json"
    plugin2._load_local_cache()
    
    # Should fetch from cache without API call
    cached = plugin2._get_cached("test_id", "name")
    assert cached is not None
    assert cached.success is True
    assert cached.data["MolecularWeight"] == "123.4"
