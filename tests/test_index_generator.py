import pytest
import numpy as np
import json
from pathlib import Path
from backend.exports.index_generator import MasterIndexGenerator

class MockSegregationResult:
    def __init__(self, root_path):
        self.root_path = str(root_path)
        self.total_folders = 2
        self.total_files = 2
        self.hierarchy_levels = 2
        self.leaf_nodes = [
            {
                'path': 'LD50/rat',
                'filename': 'data_01.csv',
                'records': 100,
                'compounds': 50,
                'hierarchy_tags': {'endpoint': 'LD50', 'species': 'rat'}
            },
            {
                'path': 'NOAEL/mouse',
                'filename': 'data_02.csv',
                'records': 200,
                'compounds': 75,
                'hierarchy_tags': {'endpoint': 'NOAEL', 'species': 'mouse'}
            }
        ]



def test_sanitize_for_json():
    generator = MasterIndexGenerator()
    
    data = {
        "score": 90.5,
        "missing": np.nan,
        "infinity": np.inf,
        "nested": {"val": np.nan}
    }
    
    sanitized = generator._sanitize_for_json(data)
    assert sanitized["score"] == 90.5
    assert sanitized["missing"] is None
    assert sanitized["infinity"] == "Infinity"
    assert sanitized["nested"]["val"] is None

def test_generate_from_segregation_result(tmp_path):
    generator = MasterIndexGenerator()
    mock_result = MockSegregationResult(tmp_path)
    
    manifest_json = generator.generate_from_segregation_result(
        result=mock_result,
        session_id="test_session_123",
        file_hash="abc123hash",
        audit_score=np.nan, # Testing edge case score
        dataset_name="test_data.csv"
    )
    
    assert isinstance(manifest_json, str)
    
    manifest = json.loads(manifest_json)
        
    # Check metadata
    assert manifest['metadata']['session_id'] == "test_session_123"
    assert manifest['metadata']['original_file_sha256'] == "abc123hash"
    assert manifest['metadata']['final_audit_score'] is None
    
    # Check index entries
    assert len(manifest['index']) == 2
    
    entry1 = manifest['index'][0]
    assert entry1['filename'] == 'data_01.csv'
    assert entry1['hierarchy_tags']['endpoint'] == 'LD50'
    assert entry1['hierarchy_tags']['species'] == 'rat'
    assert entry1['record_count'] == 100
