"""
Tests for Phase 2 — Scientific Variable Mapping (synonym mapper + unit converter).
"""
import pytest
from backend.utils.synonym_mapper import ScientificSynonymMapper, ColumnMapping
from backend.utils.unit_converter import UnitConverter


class TestScientificSynonymMapper:

    @pytest.fixture(autouse=True)
    def mapper(self):
        self.mapper = ScientificSynonymMapper()

    def test_exact_match_cas(self):
        result = self.mapper.best_mapping("cas_number")
        assert result is not None
        assert result.scientific_variable == "cas_number"
        assert result.confidence == 1.0

    def test_synonym_match_species(self):
        result = self.mapper.best_mapping("Test Species")
        assert result is not None
        assert result.scientific_variable == "species"

    def test_synonym_match_endpoint(self):
        result = self.mapper.best_mapping("Toxicological Endpoint")
        assert result is not None
        assert result.scientific_variable == "endpoint"

    def test_synonym_match_unit(self):
        result = self.mapper.best_mapping("Unit of Measurement")
        assert result is not None
        assert result.scientific_variable == "unit"

    def test_no_match_returns_none(self):
        result = self.mapper.best_mapping("xyzzy_unknown_col_999")
        assert result is None

    def test_auto_map_columns(self, sample_messy_columns):
        mappings = self.mapper.auto_map_columns(sample_messy_columns)
        assert isinstance(mappings, dict)
        # At least some columns should be mapped
        mapped = [v for v in mappings.values() if v is not None]
        assert len(mapped) >= 3

    def test_list_variables_not_empty(self):
        variables = self.mapper.list_variables()
        assert len(variables) > 10
        assert "cas_number" in variables
        assert "species" in variables
        assert "endpoint" in variables

    def test_confidence_ordering(self):
        suggestions = self.mapper.suggest_mapping("cas_number")
        assert len(suggestions) >= 1
        confidences = [s.confidence for s in suggestions]
        assert confidences == sorted(confidences, reverse=True)


class TestUnitConverter:

    @pytest.fixture(autouse=True)
    def converter(self):
        self.c = UnitConverter()

    def test_normalize_mg_kg(self):
        assert self.c.normalize_unit("mg/kg") == "mg/kg"

    def test_normalize_alias(self):
        assert self.c.normalize_unit("milligram per kilogram") == "mg/kg"

    def test_normalize_unknown_returns_none(self):
        assert self.c.normalize_unit("xyz/abc") is None

    def test_convert_g_to_mg(self):
        result = self.c.convert(1.0, "g", "mg")
        assert result == pytest.approx(1000.0)

    def test_convert_mg_per_kg_to_g_per_kg(self):
        result = self.c.convert(1000.0, "mg/kg", "g/kg")
        assert result == pytest.approx(1.0)

    def test_convert_incompatible_returns_none(self):
        result = self.c.convert(1.0, "mg", "mg/kg")
        assert result is None

    def test_convert_unknown_unit_returns_none(self):
        result = self.c.convert(1.0, "furlongs", "mg")
        assert result is None

    def test_unit_consistency_consistent(self):
        report = self.c.validate_unit_consistency(["mg/kg", "mg/kg", "mg/kg"])
        assert report["is_consistent"] is True
        assert report["unique_units"] == ["mg/kg"]

    def test_unit_consistency_inconsistent(self):
        report = self.c.validate_unit_consistency(["mg/kg", "mg/L", "ppm"])
        assert report["is_consistent"] is False
        assert len(report["unique_units"]) > 1

    def test_unit_consistency_with_missing(self):
        report = self.c.validate_unit_consistency(["mg/kg", None, "mg/kg"])
        assert report["missing_count"] == 1

    def test_list_units_dose_category(self):
        dose_units = self.c.list_units("dose")
        assert "mg/kg" in dose_units
        assert "g/kg" in dose_units
