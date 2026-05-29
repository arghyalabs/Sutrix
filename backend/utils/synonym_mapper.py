"""
Scientific synonym mapper for automatic column name recognition.

Maps user-supplied column names (in any common variant spelling) to
standardised scientific variable names used throughout the platform.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from backend.utils.logger import setup_logger

logger = setup_logger("sdo.synonym_mapper")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ColumnMapping:
    """A single suggestion for mapping a user column to a scientific variable."""
    user_column: str
    scientific_variable: str
    confidence: float          # 0.0 – 1.0
    method: str                # 'exact' | 'fuzzy' | 'synonym' | 'manual'

    def __repr__(self) -> str:
        return (
            f"ColumnMapping('{self.user_column}' → '{self.scientific_variable}' "
            f"[{self.method}, {self.confidence:.2f}])"
        )


# ---------------------------------------------------------------------------
# Synonym dictionaries
# ---------------------------------------------------------------------------

# Each dict maps a canonical variable name → list of accepted synonyms (lowercase).
# These are intentionally exhaustive so real-world messy datasets are handled.

_SPECIES_SYNONYMS: Dict[str, List[str]] = {
    "species": [
        "species", "animal", "test_species", "test animal", "organism",
        "subject", "test_subject", "experimental_species", "sp.", "strain",
        "breed", "test organism",
    ],
    "rat": [
        "rat", "rattus", "rattus norvegicus", "wistar", "sprague-dawley",
        "sd rat", "wistar rat", "long-evans", "fischer 344", "f344",
        "brown norway",
    ],
    "mouse": [
        "mouse", "mus", "mus musculus", "c57bl/6", "balb/c", "cd-1",
        "swiss webster", "nmri", "c3h", "dba/2", "129/sv", "fvb",
    ],
    "human": [
        "human", "homo sapiens", "people", "patient", "subject",
        "volunteer", "participant", "man", "woman", "donor",
    ],
    "dog": [
        "dog", "canis", "canis familiaris", "beagle", "labrador",
        "german shepherd",
    ],
    "rabbit": [
        "rabbit", "oryctolagus", "oryctolagus cuniculus",
        "new zealand white", "dutch belted", "flemish giant",
    ],
    "fish": [
        "fish", "zebrafish", "danio rerio", "fathead minnow",
        "pimephales promelas", "rainbow trout", "oncorhynchus mykiss",
        "medaka", "oryzias latipes",
    ],
}

_ENDPOINT_SYNONYMS: Dict[str, List[str]] = {
    "endpoint": [
        "endpoint", "effect_type", "toxicological_endpoint", "effect",
        "outcome", "response", "parameter", "measurement",
        "assay_endpoint", "toxicity_endpoint",
    ],
    # Acute Toxicity Endpoints
    "ld50": [
        "ld50", "lethal dose 50", "median lethal dose", "ld_50",
        "ld50 value", "acute toxicity",
    ],
    "lc50": [
        "lc50", "lethal concentration 50", "median lethal concentration",
        "lc_50", "lc50 value",
    ],
    "ed50": [
        "ed50", "effective dose 50", "median effective dose", "ed_50",
    ],
    "ec50": [
        "ec50", "effective concentration 50", "half maximal effective concentration",
        "ec_50", "ec50 value",
    ],
    "ic50": [
        "ic50", "inhibitory concentration 50", "half maximal inhibitory concentration",
        "ic_50", "ic50 value",
    ],
    "mdtd": [
        "mdtd", "maximum tolerated dose", "mtd", "max tolerated dose",
    ],
    # Repeat-Dose / Subchronic / Chronic
    "noael": [
        "noael", "no observed adverse effect level",
        "no-observed-adverse-effect-level", "noael_value",
    ],
    "loael": [
        "loael", "lowest observed adverse effect level",
        "lowest-observed-adverse-effect-level", "loael_value",
    ],
    "noel": [
        "noel", "no observed effect level", "no-observed-effect-level",
    ],
    "noaec": [
        "noaec", "no observed adverse effect concentration",
        "no-observed-adverse-effect-concentration",
    ],
    "loaec": [
        "loaec", "lowest observed adverse effect concentration",
        "lowest-observed-adverse-effect-concentration",
    ],
    "bmd10": [
        "bmd10", "benchmark dose 10", "bmd_10", "bmd 10%",
        "benchmark dose lower confidence limit",
    ],
    "bmdl10": [
        "bmdl10", "benchmark dose lower 10", "bmdl_10", "bmdl 10%",
    ],
    "aed": [
        "aed", "adverse effect dose", "developmental aed",
    ],
    "duration": [
        "duration", "exposure_duration", "treatment_duration", "time",
        "exposure_time", "study_duration", "days", "exposure_period",
        "study length", "treatment period",
    ],
    "chronic": [
        "chronic", "chronic exposure", "chronic toxicity", "long-term",
        "long term", "longterm",
    ],
    "subchronic": [
        "subchronic", "subchronic exposure", "subchronic toxicity",
        "sub-chronic", "mid-term", "medium term", "sub_chronic",
    ],
    "acute": [
        "acute", "acute exposure", "acute toxicity", "short-term",
        "short term", "shortterm", "single-dose",
    ],
}

# Physicochemical & Fate
_PHYSICOCHEMICAL_FATE_SYNONYMS: Dict[str, List[str]] = {
    "bcf": [
        "bcf", "bioconcentration factor", "bioconcentration_factor",
        "bio concentration factor",
    ],
    "baf": [
        "baf", "bioaccumulation factor", "bioaccumulation_factor",
        "bio accumulation factor",
    ],
    "half_life_dt50": [
        "half_life_dt50", "dt50", "half life", "half-life",
        "degradation half life", "half_life", "environmental half life",
        "dt_50", "dissipation time 50",
    ],
    "adsorption_koc": [
        "adsorption_koc", "koc", "k_oc", "soil adsorption coefficient",
        "organic carbon partition coefficient", "soil sorption",
    ],
    "pka": [
        "pka", "acid dissociation constant", "pk_a", "dissociation constant"
    ],
}

# Physicochemical Properties
_PHYSICOCHEMICAL_SYNONYMS: Dict[str, List[str]] = {
    "logp_logkow": [
        "logp_logkow", "logp", "log p", "logkow", "log kow",
        "octanol water partition", "partition coefficient",
        "xlogp", "xlogp3", "log_p",
    ],
    "water_solubility": [
        "water_solubility", "solubility", "aqueous solubility",
        "water solubility", "sol", "ws",
    ],
    "melting_point": [
        "melting_point", "melting point", "mp", "m.p.",
        "fusion point", "solidification point",
    ],
    "boiling_point": [
        "boiling_point", "boiling point", "bp", "b.p.",
        "evaporation point",
    ],
    "vapor_pressure": [
        "vapor_pressure", "vapour pressure", "vapor pressure", "vp",
        "saturated vapor pressure", "pvap",
    ],
    "molecular_weight": [
        "molecular_weight", "molecular weight", "mw", "mol_weight",
        "formula weight", "fw",
    ],
}

# In Vitro / Genetic / ADME Assays
_INVITRO_SYNONYMS: Dict[str, List[str]] = {
    "ames_mutagenicity": [
        "ames_mutagenicity", "ames", "ames test", "mutagenicity",
        "ames mutagenicity", "bacterial reverse mutation",
    ],
    "herg_inhibition": [
        "herg_inhibition", "herg", "herg inhibition", "herg channel",
        "herg ic50", "herg block", "cardiac safety",
    ],
    "chromosomal_aberration": [
        "chromosomal_aberration", "chromosomal aberration", "chromosome aberration",
        "clastogenicity", "micronucleus", "mnvit",
    ],
    "cyp450_substrate": [
        "cyp450_substrate", "cyp450", "cyp substrate", "cyp inhibition",
        "cytochrome p450", "cyp3a4", "cyp2d6", "cyp1a2", "cyp2c9",
    ],
    "plasma_protein_binding": [
        "plasma_protein_binding", "ppb", "protein binding",
        "plasma protein binding", "serum protein binding",
        "fraction unbound", "fu",
    ],
}

# Chemical Identifiers
_CHEMICAL_IDENTIFIER_SYNONYMS: Dict[str, List[str]] = {
    "chemical_id": [
        "chemical_id", "chemical", "chemical_name", "compound",
        "compound_name", "substance", "substance_name", "test_substance",
        "test_chemical", "test_compound", "active_ingredient",
        "active substance", "drug", "drug_name", "chemical name",
    ],
    "cas_number": [
        "cas_number", "cas", "cas_no", "cas #", "casrn",
        "cas_rn", "cas registry number", "cas number",
    ],
    "canonical_smiles": [
        "smiles", "canonical_smiles", "canonical smiles",
        "isomeric_smiles", "isomeric smiles", "smi",
    ],
    "inchikey": [
        "inchikey", "inchi_key", "inchi key", "standard_inchikey",
        "standard inchikey",
    ],
    "inchi": [
        "inchi", "standard_inchi", "standard inchi",
    ],
    "pubchem_cid": [
        "pubchem_cid", "cid", "pubchem cid", "pubchem_compound_id",
    ],
}

_QUALIFIER_SYNONYMS: Dict[str, List[str]] = {
    "qualifier": [
        "qualifier", "operator", "relation", "comparison",
        "inequality", "ineq", "sign",
    ],
    "=": ["=", "equals", "equal to", "eq", "exactly", "exact"],
    ">": [">", "greater than", "gt", "above", "more than"],
    "<": ["<", "less than", "lt", "below"],
    ">=": [">=", "greater than or equal", "gte", "at least", "minimum"],
    "<=": ["<=", "less than or equal", "lte", "at most", "maximum"],
}

_MEASUREMENT_SYNONYMS: Dict[str, List[str]] = {
    "value": [
        "value", "result", "measurement", "numeric_value", "dose",
        "concentration", "amount", "quantity", "observed_value",
        "measured_value", "test_value",
    ],
    "unit": [
        "unit", "units", "unit_of_measurement", "measure",
        "measurement_unit", "dose_unit", "concentration_unit",
    ],
    "toxicity_category": [
        "toxicity_category", "toxicity_type", "category",
        "toxicity_class", "effect_category", "organ_system",
        "target_organ", "system", "organ",
    ],
    "study_type": [
        "study_type", "study type", "test_type", "testtype", "assay_type", "assaytype",
        "study design", "test design", "studytype",
    ],
    "route": [
        "route", "route_of_administration", "administration_route",
        "exposure_route", "admin_route", "dosing_route",
    ],
    "sex": [
        "sex", "gender", "animal_sex", "subject_sex",
    ],
    "strain": [
        "strain", "animal_strain", "genetic_background", "substrain",
    ],
    "age": [
        "age", "animal_age", "subject_age", "age_at_treatment",
        "postnatal_day", "gestational_age",
    ],
    "weight": [
        "weight", "body_weight", "bw", "bodyweight",
        "animal_weight", "initial_body_weight",
    ],
}

# Combined lookup table
_ALL_SYNONYM_GROUPS: List[Dict[str, List[str]]] = [
    _SPECIES_SYNONYMS,
    _ENDPOINT_SYNONYMS,
    _PHYSICOCHEMICAL_FATE_SYNONYMS,
    _PHYSICOCHEMICAL_SYNONYMS,
    _INVITRO_SYNONYMS,
    _CHEMICAL_IDENTIFIER_SYNONYMS,
    _QUALIFIER_SYNONYMS,
    _MEASUREMENT_SYNONYMS,
]


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

class ScientificSynonymMapper:
    """
    Detects and suggests mappings between arbitrary column names and
    standardised scientific variables.

    Three-tier matching:
        1. Exact match (normalised) -> confidence 1.0
        2. Synonym match            -> confidence 0.9
        3. Partial / fuzzy match    -> confidence 0.6
    """

    def __init__(self) -> None:
        self._synonym_to_variable: Dict[str, str] = {}
        self._build_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def suggest_mapping(self, column_name: str) -> List[ColumnMapping]:
        """
        Suggest scientific variable mappings for a single column name.

        Returns a list sorted by descending confidence.  An empty list
        means no suggestion could be made.
        """
        normalised = self._normalise(column_name)
        seen_variables: Dict[str, float] = {}  # variable -> best confidence
        suggestions: List[ColumnMapping] = []

        # Tier 1 -- exact normalised match
        if normalised in self._synonym_to_variable:
            var = self._synonym_to_variable[normalised]
            suggestions.append(ColumnMapping(
                user_column=column_name,
                scientific_variable=var,
                confidence=1.0,
                method="exact",
            ))
            seen_variables[var] = 1.0

        # Tier 2 -- synonym match (normalised synonym == normalised column)
        for synonym, var in self._synonym_to_variable.items():
            if self._normalise(synonym) == normalised:
                if var not in seen_variables:
                    suggestions.append(ColumnMapping(
                        user_column=column_name,
                        scientific_variable=var,
                        confidence=0.9,
                        method="synonym",
                    ))
                    seen_variables[var] = 0.9

        # Tier 3 -- partial / substring match
        for synonym, var in self._synonym_to_variable.items():
            norm_syn = self._normalise(synonym)
            if len(norm_syn) >= 2 and (normalised in norm_syn or norm_syn in normalised):
                if var not in seen_variables:
                    suggestions.append(ColumnMapping(
                        user_column=column_name,
                        scientific_variable=var,
                        confidence=0.6,
                        method="fuzzy",
                    ))
                    seen_variables[var] = 0.6

        suggestions.sort(key=lambda m: m.confidence, reverse=True)
        logger.debug("Column '%s' -> %d suggestion(s)", column_name, len(suggestions))
        return suggestions

    def best_mapping(self, column_name: str) -> Optional[ColumnMapping]:
        """Return the highest-confidence suggestion, or None."""
        suggestions = self.suggest_mapping(column_name)
        return suggestions[0] if suggestions else None

    def auto_map_columns(
        self, columns: List[str], threshold: float = 0.6
    ) -> Dict[str, Optional[ColumnMapping]]:
        """
        Auto-map a list of column names.

        Args:
            columns:   Column names from the uploaded dataset.
            threshold: Minimum confidence to include a mapping.

        Returns:
            Dict of {column_name: best_ColumnMapping_or_None}.
        """
        result: Dict[str, Optional[ColumnMapping]] = {}
        for col in columns:
            best = self.best_mapping(col)
            result[col] = best if (best and best.confidence >= threshold) else None
        return result

    def get_all_scientific_variables(self) -> Dict[str, List[str]]:
        """Return all variable groups with their synonym lists."""
        return {
            "species": _SPECIES_SYNONYMS,
            "endpoints": _ENDPOINT_SYNONYMS,
            "physicochemical_fate": _PHYSICOCHEMICAL_FATE_SYNONYMS,
            "physicochemical": _PHYSICOCHEMICAL_SYNONYMS,
            "invitro_adme": _INVITRO_SYNONYMS,
            "chemical_identifiers": _CHEMICAL_IDENTIFIER_SYNONYMS,
            "qualifiers": _QUALIFIER_SYNONYMS,
            "measurements": _MEASUREMENT_SYNONYMS,
        }

    def list_variables(self) -> List[str]:
        """Return a flat sorted list of all recognised scientific variables."""
        return sorted(set(self._synonym_to_variable.values()))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        """Populate the reverse synonym → variable lookup."""
        for group in _ALL_SYNONYM_GROUPS:
            for variable, synonyms in group.items():
                for synonym in synonyms:
                    key = self._normalise(synonym)
                    if key not in self._synonym_to_variable:
                        self._synonym_to_variable[key] = variable
        logger.debug(
            "Synonym index built: %d entries -> %d variables",
            len(self._synonym_to_variable),
            len(set(self._synonym_to_variable.values())),
        )

    @staticmethod
    def _normalise(text: str) -> str:
        """Lowercase, collapse whitespace/punctuation to underscore."""
        text = text.strip().lower()
        text = re.sub(r"[\s\-./\\]+", "_", text)
        text = re.sub(r"[^a-z0-9_]", "", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text
