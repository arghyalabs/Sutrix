"""
Pytest configuration and shared fixtures for the Scientific Data Orchestrator test suite.
"""
import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def sample_toxicology_data() -> pd.DataFrame:
    """Realistic toxicology dataset for testing."""
    return pd.DataFrame({
        "chemical_name": ["Chemical A", "Chemical B", "Chemical C", "Chemical A", "Chemical D"],
        "cas_number":    ["123-45-6",   "234-56-7",   "345-67-8",   "123-45-6",   "456-78-9"],
        "species":       ["rat",        "mouse",      "rat",        "rat",        "mouse"],
        "endpoint":      ["ld50",       "ld50",       "noael",      "ld50",       "lc50"],
        "value":         [500,          250,          10,           500,          75],
        "unit":          ["mg/kg",      "mg/kg",      "mg/kg/day",  "mg/kg",      "mg/L"],
        "duration":      [1,            1,            90,           1,            4],
        "qualifier":     ["=",          "=",          "=",          "=",          "="],
    })


@pytest.fixture
def sample_messy_columns() -> list:
    """Column names typical of real-world messy datasets."""
    return [
        "Chemical Name",
        "CAS No.",
        "Test Species",
        "Toxicological Endpoint",
        "Value",
        "Unit of Measurement",
        "Duration (days)",
        "Qualifier/Operator",
    ]


@pytest.fixture
def sample_mapping() -> dict:
    """Standard column mapping for testing."""
    return {
        "chemical_id": "chemical_name",
        "cas_number":  "cas_number",
        "species":     "species",
        "endpoint":    "endpoint",
        "value":       "value",
        "unit":        "unit",
        "duration":    "duration",
        "qualifier":   "qualifier",
    }


@pytest.fixture
def temp_output_dir(tmp_path) -> Path:
    """Temporary output directory for each test."""
    out = tmp_path / "outputs"
    out.mkdir()
    return out


@pytest.fixture
def sample_csv_file(tmp_path, sample_toxicology_data) -> Path:
    """Write sample data to a temporary CSV file."""
    path = tmp_path / "sample_tox.csv"
    sample_toxicology_data.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_excel_file(tmp_path, sample_toxicology_data) -> Path:
    """Write sample data to a temporary Excel file with two sheets."""
    path = tmp_path / "sample_tox.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        sample_toxicology_data.to_excel(writer, sheet_name="Toxicology", index=False)
        sample_toxicology_data.head(2).to_excel(writer, sheet_name="Summary", index=False)
    return path
