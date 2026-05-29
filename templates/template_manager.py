"""
Template manager — loads, validates, and exposes scientific domain templates.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from backend.utils.logger import setup_logger

logger = setup_logger("sdo.template_manager")


@dataclass
class DomainTemplate:
    """Represents a scientific domain template loaded from JSON."""
    template_id: str
    name: str
    description: str
    version: str
    required_variables: List[str]
    optional_variables: List[str]
    default_hierarchy: List[str]
    validation_rules: Dict = field(default_factory=dict)
    metadata_standards: Dict = field(default_factory=dict)
    quality_thresholds: Dict = field(default_factory=dict)

    @property
    def all_variables(self) -> List[str]:
        return self.required_variables + self.optional_variables


class TemplateManager:
    """Loads all *_template.json files from the templates directory."""

    def __init__(self, templates_dir: str = "templates") -> None:
        self.templates_dir = Path(templates_dir)
        self._templates: Dict[str, DomainTemplate] = {}
        self._load_all()

    def get_template(self, template_id: str) -> Optional[DomainTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[Dict[str, str]]:
        return [
            {"id": t.template_id, "name": t.name,
             "description": t.description, "version": t.version}
            for t in self._templates.values()
        ]

    def template_ids(self) -> List[str]:
        return list(self._templates.keys())

    def validate_columns_against_template(
        self, columns: List[str], template_id: str
    ) -> Dict:
        template = self.get_template(template_id)
        if not template:
            return {"valid": False, "error": f"Template '{template_id}' not found"}

        cols_lower = [c.lower() for c in columns]
        missing_required = [
            rv for rv in template.required_variables
            if not any(rv.lower() in c for c in cols_lower)
        ]
        matched_optional = [
            ov for ov in template.optional_variables
            if any(ov.lower() in c for c in cols_lower)
        ]
        total_optional = len(template.optional_variables)
        coverage = len(matched_optional) / total_optional if total_optional else 1.0

        return {
            "valid": len(missing_required) == 0,
            "template": template.name,
            "missing_required": missing_required,
            "matched_optional": matched_optional,
            "coverage": round(coverage, 3),
        }

    def _load_all(self) -> None:
        if not self.templates_dir.exists():
            logger.warning("Templates directory not found: %s", self.templates_dir)
            return
        loaded = 0
        for json_file in sorted(self.templates_dir.glob("*_template.json")):
            t = self._load_one(json_file)
            if t:
                self._templates[t.template_id] = t
                loaded += 1
        logger.info("Loaded %d template(s)", loaded)

    def _load_one(self, path: Path) -> Optional[DomainTemplate]:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            required_keys = {"template_id", "name", "required_variables", "default_hierarchy"}
            if missing := required_keys - data.keys():
                logger.warning("Template '%s' missing keys: %s", path.name, missing)
                return None
            return DomainTemplate(
                template_id=data["template_id"],
                name=data["name"],
                description=data.get("description", ""),
                version=data.get("version", "1.0.0"),
                required_variables=data["required_variables"],
                optional_variables=data.get("optional_variables", []),
                default_hierarchy=data["default_hierarchy"],
                validation_rules=data.get("validation_rules", {}),
                metadata_standards=data.get("metadata_standards", {}),
                quality_thresholds=data.get("quality_thresholds", {}),
            )
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            logger.error("Failed to load '%s': %s", path.name, exc)
            return None
