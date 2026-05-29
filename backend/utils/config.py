"""
Configuration management for the Scientific Data Orchestrator.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

@dataclass
class AppConfig:
    """Application-wide configuration settings."""

    # Directory paths
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    templates_dir: str = "templates"
    log_dir: str = "outputs/logs"

    # File ingestion settings
    max_file_size_mb: int = 100
    supported_extensions: tuple = (".csv", ".xlsx", ".xlsm", ".xls")
    encoding_sample_bytes: int = 10_000

    # Segregation settings
    max_hierarchy_depth: int = 5
    max_folder_name_length: int = 100
    default_export_format: str = "xlsx"  # 'xlsx' or 'csv'

    # API plugin settings
    api_rate_limit_delay: float = 0.1   # seconds between requests
    api_cache_enabled: bool = True
    api_request_timeout: int = 30       # seconds

    # Audit / quality thresholds
    quality_missing_pct_critical: float = 30.0
    quality_missing_pct_warning: float = 10.0
    quality_duplicate_deduction: float = 0.3
    quality_missing_deduction: float = 0.5
    quality_critical_finding_deduction: float = 5.0
    quality_warning_finding_deduction: float = 2.0

    # Session settings
    session_id_format: str = "%Y%m%d_%H%M%S"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create config from environment variables (with defaults)."""
        return cls(
            upload_dir=os.getenv("SDO_UPLOAD_DIR", "uploads"),
            output_dir=os.getenv("SDO_OUTPUT_DIR", "outputs"),
            templates_dir=os.getenv("SDO_TEMPLATES_DIR", "templates"),
            max_file_size_mb=int(os.getenv("SDO_MAX_FILE_SIZE_MB", "100")),
            api_rate_limit_delay=float(os.getenv("SDO_API_RATE_LIMIT", "0.1")),
            api_cache_enabled=os.getenv("SDO_API_CACHE", "true").lower() == "true",
        )

    def ensure_directories(self) -> None:
        """Create all configured directories if they don't exist."""
        for dir_attr in ("upload_dir", "output_dir", "templates_dir", "log_dir"):
            Path(getattr(self, dir_attr)).mkdir(parents=True, exist_ok=True)


# Singleton config instance — import this throughout the project
config = AppConfig.from_env()

class MappingPersistence:
    """Handles persistence of column mappings."""
    
    def __init__(self, storage_dir: str = "outputs/mappings"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def save_mapping(self, dataset_id: str, mappings: List[dict]) -> str:
        """Save column mappings to JSON file."""
        mapping_doc = {
            "dataset_id": dataset_id,
            "mappings": mappings,
            "created_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        file_path = self.storage_dir / f"{dataset_id}_mapping.json"
        with open(file_path, 'w') as f:
            json.dump(mapping_doc, f, indent=2)
        
        return str(file_path)
    
    def load_mapping(self, dataset_id: str) -> Optional[dict]:
        """Load column mappings from JSON file."""
        file_path = self.storage_dir / f"{dataset_id}_mapping.json"
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def export_mapping_template(self, output_path: str) -> None:
        """Export a template for manual mapping."""
        template = {
            "dataset_id": "your_dataset_id",
            "mappings": [
                {
                    "user_column": "Column_A_From_Excel",
                    "scientific_variable": "chemical_id",
                    "confidence": 1.0,
                    "method": "manual"
                }
            ],
            "available_variables": [
                "chemical_id", "cas_number", "smiles", "species", 
                "endpoint", "duration", "value", "unit", "qualifier"
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2)
