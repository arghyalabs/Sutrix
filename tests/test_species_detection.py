import pytest
from backend.core.ecotox.species_detector import SpeciesDetector

def test_species_exact_matches():
    # Test perfect lowercase matches
    species, conf = SpeciesDetector.detect_species("human")
    assert species == "human"
    assert conf == 1.0
    
    species, conf = SpeciesDetector.detect_species("rat")
    assert species == "rat"
    assert conf == 1.0

def test_species_aliases_and_casing():
    # Test case insensitivity and aliases
    species, conf = SpeciesDetector.detect_species("Sprague Dawley Rat")
    assert species == "rat"
    assert conf >= 0.85

    species, conf = SpeciesDetector.detect_species("oncorhynchus mykiss (rainbow trout)")
    assert species == "fish"
    assert conf >= 0.70

    species, conf = SpeciesDetector.detect_species("daphnia magna")
    assert species == "daphnia"
    assert conf >= 0.85

def test_cell_line_detection():
    # Test mammalian cell line aliases
    species, conf = SpeciesDetector.detect_species("HEK-293T cells")
    assert species == "cell_line_hek293"
    assert conf >= 0.85

    species, conf = SpeciesDetector.detect_species("hela cell line")
    assert species == "cell_line_hela"
    assert conf >= 0.85

def test_column_alias_detection():
    # Test species column identifiers
    assert SpeciesDetector.is_species_column("test_species") is True
    assert SpeciesDetector.is_species_column("animal_model") is True
    assert SpeciesDetector.is_species_column("concentration") is False
