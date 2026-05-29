import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from backend.core.hierarchy_engine import HierarchyEngine
from backend.core.lineage_builder import LineageBuilder

@pytest.fixture
def sample_potency_data():
    """Sample dataset mimicking real toxicological dataset with potency roles."""
    return pd.DataFrame({
        'smiles': ['CCO', 'CCC', 'CCO', 'CCN', 'CCC'],
        'species': ['Fish', 'Daphnia', 'Fish', 'Fish', 'Daphnia'],
        'endpoint': ['LC50', 'EC50', 'LC50', 'LC50', 'EC50'],
        'exposure_duration': ['96h', '48h', '96h', '96h', '48h'],
        'lc50': [1.2, 5.4, 1.1, 0.8, 4.9],
        'molecular_weight': [46.07, 44.1, 46.07, 45.08, 44.1],
    })

def test_hierarchy_engine_build(sample_potency_data):
    """Test full hierarchical tree structure build, stats, and charts."""
    mappings = {
        'smiles': 'smiles',
        'species': 'species',
        'endpoint': 'endpoint',
        'exposure_duration': 'exposure_duration',
        'lc50': 'lc50',
        'molecular_weight': 'molecular_weight'
    }
    
    engine = HierarchyEngine(workspace_id='test_ws', mappings=mappings)
    hierarchy_cols = ['species', 'endpoint']
    
    lineage = engine.build(sample_potency_data, hierarchy_cols)
    
    assert lineage['root_id'] == 'root'
    assert lineage['total_nodes'] == 5 # root + Fish + Daphnia + Fish>LC50 + Daphnia>EC50
    assert lineage['max_depth'] == 2
    
    # Check nodes
    nodes_by_id = {n['id']: n for n in lineage['nodes']}
    assert 'root' in nodes_by_id
    
    root_node = nodes_by_id['root']
    assert root_node['row_count'] == 5
    assert root_node['unique_compounds'] == 3 # CCO, CCC, CCN
    
    # Daphnia branch
    daphnia_node = next((n for n in lineage['nodes'] if n['node_name'] == 'Daphnia'), None)
    assert daphnia_node is not None
    assert daphnia_node['parent_id'] == 'root'
    assert daphnia_node['row_count'] == 2
    
    # Precomputed stats and charts verification
    assert 'root' in engine.node_details
    root_detail = engine.node_details['root']
    assert root_detail['stats']['total_rows'] == 5
    assert root_detail['stats']['unique_compounds'] == 3
    assert root_detail['stats']['numeric_cols'] == 2 # lc50, molecular_weight
    
    # Check charts
    assert 'composition_pie' in root_detail['charts']
    assert root_detail['charts']['composition_pie']['title'] == 'species'
    assert set(root_detail['charts']['composition_pie']['labels']) == {'Fish', 'Daphnia'}
    assert root_detail['charts']['composition_pie']['values'] == [3, 2] # sorted by unique value name: Daphnia=2, Fish=3
    
    # Check distributions (potency roles)
    assert 'distributions' in root_detail['charts']
    assert 'lc50' in root_detail['charts']['distributions']
    assert 'molecular_weight' in root_detail['charts']['distributions']
    
    lc50_dist = root_detail['charts']['distributions']['lc50']
    assert 'mean' in lc50_dist
    assert 'median' in lc50_dist
    assert lc50_dist['mean'] == pytest.approx(2.68)

def test_lineage_builder_orchestration(sample_potency_data, tmp_path):
    """Test the LineageBuilder orchestration wrapper."""
    mappings = {
        'smiles': 'smiles',
        'species': 'species',
        'endpoint': 'endpoint'
    }
    
    # Change working dir to tmp_path or let it save to default exports
    import os
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        lineage = LineageBuilder.run(
            df=sample_potency_data,
            hierarchy_cols=['species', 'endpoint'],
            mappings=mappings,
            workspace_id='test_lineage_ws'
        )
        
        assert lineage['total_nodes'] == 5
        assert '_engine' in lineage
        
        # Verify export files exist
        base_dir = Path('exports') / 'test_lineage_ws'
        assert base_dir.exists()
        
        # Check root
        assert (base_dir / 'Root' / 'dataset.parquet').exists()
        assert (base_dir / 'Root' / 'dataset.feather').exists()
        
        # Check leaf (is_leaf = True) has csv/xlsx
        fish_lc50_dir = base_dir / 'Root' / 'Fish' / 'LC50'
        assert (fish_lc50_dir / 'dataset.csv').exists()
        assert (fish_lc50_dir / 'dataset.xlsx').exists()
        
    finally:
        os.chdir(original_cwd)
