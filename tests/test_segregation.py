import pytest
import pandas as pd
from pathlib import Path
from backend.segregation.engine import HierarchicalSegregationEngine
from backend.segregation.splitter import OptimizedSegregationEngine

@pytest.fixture
def sample_toxicology_data():
    """Sample toxicology dataset for testing."""
    return pd.DataFrame({
        'chemical_name': ['Chemical A', 'Chemical B', 'Chemical C', 'Chemical A'],
        'cas_number': ['123-45-6', '234-56-7', '345-67-8', '123-45-6'],
        'species': ['rat', 'mouse', 'rat', 'rat'],
        'endpoint': ['ld50', 'ld50', 'noael', 'ld50'],
        'value': [500, 250, 10, 500],
        'unit': ['mg/kg', 'mg/kg', 'mg/kg/day', 'mg/kg'],
        'duration': [1, 1, 90, 1],
        'qualifier': ['=', '=', '=', '=']
    })

def test_build_hierarchy_tree(sample_toxicology_data):
    """Test hierarchy tree construction."""
    engine = HierarchicalSegregationEngine()
    hierarchy = ['endpoint', 'species']
    
    root = engine.build_hierarchy_tree(sample_toxicology_data, hierarchy)
    
    assert root.variable == 'root'
    # 'ld50' and 'noael'
    assert len(root.children) == 2 
    
    # Sort children to ensure consistent testing
    children = sorted(root.children, key=lambda x: x.value)
    ld50_node = children[0]
    noael_node = children[1]
    
    assert ld50_node.value == 'ld50'
    assert noael_node.value == 'noael'
    
    # Check ld50 children (species)
    # ld50 has 'rat' and 'mouse'
    assert len(ld50_node.children) == 2
    
    # Check noael children (species)
    # noael only has 'rat'
    assert len(noael_node.children) == 1
    assert noael_node.children[0].value == 'rat'

def test_sanitize_folder_name():
    """Test folder name sanitization."""
    engine = HierarchicalSegregationEngine()
    
    assert engine._sanitize_folder_name("valid_name") == "valid_name"
    assert engine._sanitize_folder_name("invalid/name") == "invalid_name"
    assert engine._sanitize_folder_name('name_with_"quotes"') == "name_with__quotes_"
    assert engine._sanitize_folder_name("a" * 150) == "a" * 100

def test_segregate(sample_toxicology_data, tmp_path):
    """Test full segregation process."""
    engine = HierarchicalSegregationEngine(output_dir=str(tmp_path))
    hierarchy = ['endpoint', 'species']
    
    result = engine.segregate(
        df=sample_toxicology_data,
        hierarchy=hierarchy,
        export_format='csv',
        session_id='test_session'
    )
    
    assert result.total_folders == 5 # ld50, noael + their children
    assert result.total_files == 3 # ld50/rat, ld50/mouse, noael/rat
    assert result.hierarchy_levels == 2
    assert len(result.leaf_nodes) == 3
    
    # Verify buffers in leaf nodes
    assert len(result.leaf_nodes) == 3
    
    # Find the ld50/rat leaf node
    ld50_rat_leaf = next((leaf for leaf in result.leaf_nodes if leaf['path'] == 'ld50/rat'), None)
    assert ld50_rat_leaf is not None
    assert 'buffer' in ld50_rat_leaf
    
    # Verify contents of buffer
    buffer = ld50_rat_leaf['buffer']
    buffer.seek(0)
    df = pd.read_csv(buffer)
    assert len(df) == 2 # 2 ld50 rat records in sample data

def test_optimized_segregate(sample_toxicology_data, tmp_path):
    """Test full segregation process using parallel execution."""
    # Force small chunk size to trigger parallel execution
    engine = OptimizedSegregationEngine(output_dir=str(tmp_path), chunk_size=2)
    hierarchy = ['endpoint', 'species']
    
    result = engine.segregate_parallel(
        df=sample_toxicology_data,
        hierarchy=hierarchy,
        export_format='csv',
        session_id='test_parallel_session'
    )
    
    assert result.total_folders == 5 
    assert result.total_files == 3 
    assert result.hierarchy_levels == 2
    assert len(result.leaf_nodes) == 3
    
    assert len(result.leaf_nodes) == 3
    
    # Verify buffers exist
    ld50_rat_leaf = next((leaf for leaf in result.leaf_nodes if leaf['path'] == 'ld50/rat'), None)
    assert ld50_rat_leaf is not None
    assert 'buffer' in ld50_rat_leaf

def test_local_variance_flagging(tmp_path):
    """Test local file-by-file log10 variance auditing and flagging."""
    df = pd.DataFrame({
        'chemical_name': ['Chemical A', 'Chemical A', 'Chemical B'],
        'cas_number': ['123-45-6', '123-45-6', '234-56-7'],
        'species': ['rat', 'rat', 'rat'],
        'endpoint': ['ld50', 'ld50', 'ld50'],
        'value': [1.0, 100.0, 10.0],
        'unit': ['mg/kg', 'mg/kg', 'mg/kg'],
    })
    
    engine = OptimizedSegregationEngine(output_dir=str(tmp_path))
    hierarchy = ['endpoint', 'species']
    column_mappings = {
        'chemical_name': 'chemical_name',
        'endpoint': 'endpoint',
        'species': 'species',
        'value': 'value',
        'unit': 'unit'
    }
    
    result = engine.segregate_parallel(
        df=df,
        hierarchy=hierarchy,
        export_format='csv',
        session_id='test_variance_session',
        column_mappings=column_mappings
    )
    
    # We should have a single leaf node at path 'ld50/rat'
    assert len(result.leaf_nodes) == 1
    leaf = result.leaf_nodes[0]
    assert leaf['path'] == 'ld50/rat'
    
    # Read the buffer
    buffer = leaf['buffer']
    buffer.seek(0)
    out_df = pd.read_csv(buffer)
    
    # Ensure audit_flag is added
    assert 'audit_flag' in out_df.columns
    
    # Check individual rows
    chem_a_rows = out_df[out_df['chemical_name'] == 'Chemical A']
    chem_b_rows = out_df[out_df['chemical_name'] == 'Chemical B']
    
    # Chemical A has range = log10(100) - log10(1) = 2.0 - 0.0 = 2.0 >= 1.0 => High_Variance_Conflict
    assert (chem_a_rows['audit_flag'] == 'High_Variance_Conflict').all()
    
    # Chemical B is a singleton group => Consistent
    assert (chem_b_rows['audit_flag'] == 'Consistent').all()
