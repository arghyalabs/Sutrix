import re
from typing import Tuple

class SpeciesDetector:
    """
    Intelligently detects species names even when abbreviated, misspelled, or partially written.
    Behaves like a professional toxicologist and environmental data scientist.
    """
    
    SPECIES_ONTOLOGY = {
        "human": ["human", "homo sapiens", "patient", "clinical", "volunteer", "human_subject", "human_cell", "human_line"],
        "rat": ["rat", "rats", "rattus", "rattus norvegicus", "wistar", "sprague dawley", "sd rat", "f344", "fischer rat"],
        "mouse": ["mouse", "mice", "mus musculus", "balb/c", "c57bl6", "c57bl/6", "murine", "transgenic_mouse"],
        "rabbit": ["rabbit", "rabbits", "oryctolagus", "new zealand white"],
        "dog": ["dog", "beagle", "canine"],
        "primate": ["monkey", "macaque", "primate", "cynomolgus", "rhesus"],
        "fish": ["fish", "fathead minnow", "rainbow trout", "oncorhynchus mykiss", "zebrafish", "danio rerio", "carp", "bluegill", "medaka"],
        "daphnia": ["daphnia", "d magna", "daphnia magna", "water flea"],
        "algae": ["algae", "alga", "green algae", "pseudokirchneriella", "chlorella", "scenedesmus"],
        "bacteria": ["bacteria", "vibrio fischeri", "microbe", "activated_sludge"]
    }

    CELL_LINE_ONTOLOGY = {
        "hela": ["hela"],
        "hek293": ["hek293", "hek 293", "hek-293", "hek293t", "hek-293t"],
        "hepG2": ["hepg2", "hep g2", "hep-g2"],
        "mcf7": ["mcf7", "mcf-7"],
        "a549": ["a549", "a-549"],
        "cho": ["cho cell", "cho-k1", "chinese hamster ovary"],
        "jurkat": ["jurkat"],
        "u2os": ["u2os", "u-2os"]
    }

    SPECIES_COLUMN_ALIASES = [
        "species", "organism", "test_species", "biological_model", "animal_model", 
        "host", "organism_name", "test_organism", "strain", "species_name"
    ]

    @staticmethod
    def is_species_column(column_name: str) -> bool:
        text_lower = column_name.lower().strip()
        for alias in SpeciesDetector.SPECIES_COLUMN_ALIASES:
            if alias in text_lower or text_lower == alias:
                return True
        return False

    @staticmethod
    def detect_species(text: str) -> Tuple[str, float]:
        text_lower = text.lower().strip()
        
        # 1. Exact match pass
        for species, aliases in SpeciesDetector.SPECIES_ONTOLOGY.items():
            for alias in aliases:
                if alias == text_lower:
                    return species, 1.0
        for cell_line, aliases in SpeciesDetector.CELL_LINE_ONTOLOGY.items():
            for alias in aliases:
                if alias == text_lower:
                    return f"cell_line_{cell_line}", 0.95

        # 2. Word boundary match pass
        for species, aliases in SpeciesDetector.SPECIES_ONTOLOGY.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    return species, 0.85
        for cell_line, aliases in SpeciesDetector.CELL_LINE_ONTOLOGY.items():
            for alias in aliases:
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    return f"cell_line_{cell_line}", 0.85

        # 3. Substring match pass
        for species, aliases in SpeciesDetector.SPECIES_ONTOLOGY.items():
            for alias in aliases:
                if alias in text_lower:
                    return species, 0.70
        for cell_line, aliases in SpeciesDetector.CELL_LINE_ONTOLOGY.items():
            for alias in aliases:
                if alias in text_lower:
                    return f"cell_line_{cell_line}", 0.70

        return "unknown", 0.0
