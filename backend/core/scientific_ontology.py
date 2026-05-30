import re
from typing import Dict, Any, List

# Pre-compiled regex patterns for chemical identifiers and numbers
CAS_REGEX = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
INCHI_REGEX = re.compile(r"^inchi=1s?/[a-z0-9\.]+/.*", re.IGNORECASE)
INCHIKEY_REGEX = re.compile(r"^[a-z]{14}-[a-z]{10}-[a-z\d]$", re.IGNORECASE)
# General smiles character validator: check typical letters and bond symbols
SMILES_HEURISTIC_REGEX = re.compile(r"^(?=[CHONSPFIClBrIH])(?=.*[a-zA-Z])[a-zA-Z0-9\(\)\=\#\+\-\[\]\/\@\.\:\\]+$")

SCIENTIFIC_VARIABLES: Dict[str, Dict[str, Any]] = {
    # ── CHEMICAL IDENTITY ──────────────────────────────────────────────────
    "compound_name": {
        "aliases": ["compound name", "compound_name", "compound", "molecule", "molecule name", "drug name", "ligand", "preferred compound name", "analyte"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "Compound Name"
    },
    "chemical_name": {
        "aliases": ["chemical name", "chemical_name", "chemical", "chem name", "iupac name", "preferred name", "synonym"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "Chemical Name"
    },
    "substance_name": {
        "aliases": ["substance name", "substance_name", "substance", "test substance", "test_substance", "material name", "material_name", "sample name", "sample_name"],
        "regex": [],
        "priority": 80,
        "category": "chemical_identifier",
        "label": "Substance Name"
    },
    "test_substance": {
        "aliases": ["test substance", "test_substance", "test material", "test_material", "substance test"],
        "regex": [],
        "priority": 80,
        "category": "chemical_identifier",
        "label": "Test Substance"
    },
    "material_name": {
        "aliases": ["material name", "material_name", "sample name", "sample_name", "material", "sample", "analyte"],
        "regex": [],
        "priority": 80,
        "category": "chemical_identifier",
        "label": "Material Name"
    },

    # ── STRUCTURE IDENTIFIERS ──────────────────────────────────────────────
    "canonical_smiles": {
        "aliases": ["smiles", "smiles string", "smiles_string", "structure", "mol_structure", "chem_structure", "structure_formula", "canonical smiles", "canonical_smiles", "canon smiles", "canon_smiles", "rdkit smiles", "rdkit_smiles", "clean_smiles", "normalized_smiles", "compound_structure", "ligand_smiles"],
        "regex": [SMILES_HEURISTIC_REGEX],
        "priority": 100,
        "category": "chemical_identifier",
        "label": "Canonical SMILES"
    },
    "isomeric_smiles": {
        "aliases": ["isomeric smiles", "isomeric_smiles", "isomeric smiles string", "isomeric_smiles_string", "structural smiles"],
        "regex": [SMILES_HEURISTIC_REGEX],
        "priority": 99,
        "category": "chemical_identifier",
        "label": "Isomeric SMILES"
    },
    "inchi": {
        "aliases": ["inchi", "inchi key", "inchi-code", "inchi_string", "inchi_structure", "ec number", "einecs"],
        "regex": [INCHI_REGEX],
        "priority": 95,
        "category": "chemical_identifier",
        "label": "InChI Code"
    },
    "inchikey": {
        "aliases": ["inchikey", "inchi key", "inchi-key", "inchikey_string"],
        "regex": [INCHIKEY_REGEX],
        "priority": 98,
        "category": "chemical_identifier",
        "label": "InChIKey"
    },
    "molblock": {
        "aliases": ["molblock", "mol block", "molfile", "sdf block", "sdffile"],
        "regex": [],
        "priority": 90,
        "category": "chemical_identifier",
        "label": "MolBlock"
    },
    "selfies": {
        "aliases": ["selfies", "selfie", "selfies string", "selfies_string"],
        "regex": [],
        "priority": 90,
        "category": "chemical_identifier",
        "label": "SELFIES"
    },

    # ── REGULATORY IDENTIFIERS ──────────────────────────────────────────────
    "cas_number": {
        "aliases": ["cas", "cas number", "cas_number", "cas_no", "cas_rn", "casrn", "registry number", "registry_number"],
        "regex": [CAS_REGEX],
        "priority": 90,
        "category": "chemical_identifier",
        "label": "CAS Number"
    },
    "ec_number": {
        "aliases": ["ec number", "ec_number", "einecs", "einsecs", "ec-no", "ec_no"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "EC Number"
    },
    "einecs": {
        "aliases": ["einecs number", "einecs_number", "einecs_no", "einecs-no"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "EINECS"
    },
    "pubchem_cid": {
        "aliases": ["pubchem_cid", "pubchem cid", "cid", "sid", "pubchem id", "cid number", "pubchem compound id"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "PubChem CID"
    },
    "chebi_id": {
        "aliases": ["chebi", "chebi id", "chebi_id", "chebi_key", "chemical entities of biological interest"],
        "regex": [re.compile(r"^chebi:\d+$", re.IGNORECASE)],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "ChEBI ID"
    },
    "dsstox_id": {
        "aliases": ["dsstox", "dsstox id", "dsstox_id", "dtxsid", "dtxcid", "epa_dsstox"],
        "regex": [re.compile(r"^dtxsid\d+$", re.IGNORECASE)],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "DSSTox ID"
    },
    "chemspider_id": {
        "aliases": ["chemspider", "chemspider id", "chemspider_id", "chemspider key"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "ChemSpider ID"
    },

    # ── PHYSICOCHEMICAL DESCRIPTORS ─────────────────────────────────────────
    "molecular_weight": {
        "aliases": ["mw", "mol_weight", "molecular_weight", "formula_weight", "molecularmass", "m_w"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Molecular Weight"
    },
    "exact_mass": {
        "aliases": ["exact mass", "exact_mass", "calculated mass", "theoretical mass"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Exact Mass"
    },
    "monoisotopic_mass": {
        "aliases": ["monoisotopic mass", "monoisotopic_mass", "monoiso mass"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Monoisotopic Mass"
    },
    "tpsa": {
        "aliases": ["tpsa", "polar surface area", "topological polar surface area", "polar_surface_area"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "TPSA"
    },
    "logp": {
        "aliases": ["logp", "partition coefficient", "partition_coefficient", "octanol water partition", "log_kow"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "LogP"
    },
    "xlogp": {
        "aliases": ["xlogp", "xlogp3", "xlogp_value"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "XLogP"
    },
    "clogp": {
        "aliases": ["clogp", "clogp_value", "calculated logp"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "cLogP"
    },
    "hba": {
        "aliases": ["hba", "hydrogen bond acceptor", "hydrogen_bond_acceptors", "h_acceptor", "hacceptor", "hba_count"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "HBA"
    },
    "hbd": {
        "aliases": ["hbd", "hydrogen bond donor", "hydrogen_bond_donors", "h_donor", "hdonor", "hbd_count"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "HBD"
    },
    "rotatable_bonds": {
        "aliases": ["rotatable bonds", "rotatable_bonds", "rotatable bond count", "nrot"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Rotatable Bonds"
    },
    "aromatic_rings": {
        "aliases": ["aromatic rings", "aromatic_rings", "aromatic ring count", "n_aromatic_rings"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Aromatic Rings"
    },
    "ring_count": {
        "aliases": ["ring count", "ring_count", "rings", "n_rings"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Ring Count"
    },
    "heavy_atom_count": {
        "aliases": ["heavy atom count", "heavy_atom_count", "heavy atoms", "n_heavy_atoms", "n_non_h_atoms"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Heavy Atom Count"
    },
    "fraction_csp3": {
        "aliases": ["fraction csp3", "fraction_csp3", "f_csp3", "csp3 fraction"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Fraction Csp3"
    },
    "molar_refractivity": {
        "aliases": ["molar refractivity", "molar_refractivity", "mr", "molarrefractivity"],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Molar Refractivity"
    },

    # ── TOXICOLOGY ENDPOINTS (Unified under "endpoint" key) ──────────────────
    "endpoint": {
        "aliases": [
            "endpoint", "ic50", "ec50", "lc50", "ld50", "noael", "loael", "mic", "gi50", 
            "cc50", "ac50", "ki", "kd", "km", "ic90", "ec10", "ec20", "ec90", 
            "bmd", "bmdl", "benchmarkdose", "ed50", "td50", "tgi", "auc", 
            "cmax", "tmax", "cl", "clearance", "halflife", "bioavailability", 
            "mortality", "reproduction", "growth inhibition", "immobilization", 
            "hatching success", "developmental toxicity", "endocrine disruption", 
            "neurotoxicity", "hepatotoxicity", "cardiotoxicity", "genotoxicity", 
            "mutagenicity", "carcinogenicity", "cytotoxicity", "oxidative stress", 
            "apoptosis", "mitochondrial toxicity", "membrane disruption", "ic_50", 
            "ic-50", "ic50_value", "inhibitory concentration 50", "median lethal concentration", 
            "lethal dose", "noael_mgkg", "lowest observed adverse effect level", 
            "growth_inhib_percent", "acute tox", "chronic tox", "lethal_concentration", 
            "median_lethal_dose", "death", "survival", "fecundity", "offspring", 
            "egg_production", "hatching", "brood_size", "mobility", "swimming", 
            "feeding", "locomotion", "avoidance", "atp", "gst", "catalase", "enzyme_activity",
            "noec", "loec", "bcf", "baf", "biodegradation", "bioconcentration factor", "bioconcentration_factor",
            "bioaccumulation factor", "bioaccumulation_factor", "biodegradability", "half life", "half_life"
        ],
        "regex": [],
        "priority": 95,
        "category": "bioactivity",
        "label": "Toxicity / Bioassay Endpoint"
    },

    # ── QUALIFIERS ──────────────────────────────────────────────────────────
    "qualifier": {
        "aliases": ["qualifier", "operator", "relation", "comparator", "comparison", "inequality", "=", ">", "<", ">=", "<=", "approx", "nd", "not detected", "trace"],
        "regex": [],
        "priority": 75,
        "category": "metadata",
        "label": "Inequality Qualifier"
    },

    # ── SPECIES (Unified under "organism" key) ──────────────────────────────
    "organism": {
        "aliases": [
            "species", "organism", "test_species", "bio_model", "animal model", 
            "taxa", "strain", "test organism", "homo sapiens", "rattus norvegicus", 
            "mus musculus", "danio rerio", "daphnia magna", "pimephales promelas", 
            "oncorhynchus mykiss", "human", "rat", "mouse", "rabbit", "dog", 
            "monkey", "zebrafish", "daphnia", "algae", "bacteria", "yeast", 
            "fish", "trout", "carp", "medaka", "frog", "amphibian", "avian", 
            "bird", "chicken", "pig", "bovine", "insect", "bee", "earthworm", 
            "aquatic organisms", "host", "organism_name", "test_organism", "species_name"
        ],
        "regex": [],
        "priority": 90,
        "category": "metadata",
        "label": "Test Organism / Species"
    },

    # ── SEX ─────────────────────────────────────────────────────────────────
    "sex": {
        "aliases": ["sex", "gender", "biological sex", "male", "female", "mixed", "unknown"],
        "regex": [],
        "priority": 60,
        "category": "metadata",
        "label": "Biological Sex"
    },

    # ── AGE ─────────────────────────────────────────────────────────────────
    "age": {
        "aliases": ["age", "age group", "age_group", "life stage", "life_stage", "adult", "juvenile", "neonate", "larvae", "larval", "embryo", "maturity"],
        "regex": [],
        "priority": 60,
        "category": "metadata",
        "label": "Age / Life Stage"
    },

    # ── EXPOSURE DURATION (Unified under "exposure_time" key) ────────────────
    "exposure_time": {
        "aliases": [
            "exposure_time", "incubation_time", "duration", "observation_period", 
            "exposure duration", "incubation", "study_length", "treatment_period", 
            "timepoint", "hours", "hr", "h", "days", "d", "weeks", "months", "time", "exposure_duration",
            "observation time", "observation_time", "recovery time", "recovery_time"
        ],
        "regex": [],
        "priority": 85,
        "category": "metadata",
        "label": "Exposure Duration"
    },

    # ── TEST TYPES ──────────────────────────────────────────────────────────
    "test_type": {
        "aliases": ["test type", "test_type", "study type", "study_type", "acute", "chronic", "subchronic", "repeated dose", "repeated_dose", "developmental", "reproductive", "experiment_type"],
        "regex": [],
        "priority": 80,
        "category": "metadata",
        "label": "Test Type / Study Design"
    },
    "route": {
        "aliases": ["route", "route of administration", "route_of_administration", "administration route", "exposure route", "exposure_route", "admin route", "dosing route", "admin_route", "dosing_route", "oral", "dermal", "inhalation"],
        "regex": [],
        "priority": 85,
        "category": "metadata",
        "label": "Exposure Route"
    },

    # ── CLINICAL VARIABLES ──────────────────────────────────────────────────
    "patient_id": {
        "aliases": ["patient id", "patient_id", "patient", "subject", "subject id", "subject_id"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Patient ID"
    },
    "cohort": {
        "aliases": ["cohort", "cohort name", "cohort_name", "study group", "study_group"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Cohort"
    },
    "diagnosis": {
        "aliases": ["diagnosis", "disease", "indication", "condition", "pathology"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Diagnosis"
    },
    "biomarker": {
        "aliases": ["biomarker", "marker", "biological marker", "expression"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Biomarker"
    },
    "treatment_group": {
        "aliases": ["treatment group", "treatment_group", "treatment", "intervention"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Treatment Group"
    },
    "dose_group": {
        "aliases": ["dose group", "dose_group", "dose level", "dose_level", "dosage"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Dose Group"
    },

    # ── PHARMACOLOGY ────────────────────────────────────────────────────────
    "target": {
        "aliases": ["target", "protein target", "target name", "target_name", "receptor", "enzyme", "cyp3a4", "cyp2d6", "herg", "egfr", "vegfr", "ppar", "er_alpha", "ar", "ahr"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Target Protein / Receptor"
    },
    "protein": {
        "aliases": ["protein", "protein name", "protein_name", "polypeptide"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Protein"
    },
    "gene": {
        "aliases": ["gene", "gene name", "gene_name", "gene symbol", "gene_symbol"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Gene"
    },
    "receptor": {
        "aliases": ["receptor", "receptor name", "receptor_name"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Receptor"
    },
    "mechanism": {
        "aliases": ["mechanism", "mechanism of action", "moa", "action", "effect"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Mechanism of Action"
    },
    "pathway": {
        "aliases": ["pathway", "biological pathway", "pathway name", "pathway_name", "kegg", "reactome"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Pathway"
    },

    # ── MISC SYSTEM & GENERAL ───────────────────────────────────────────────
    "value": {
        "aliases": ["value", "potency", "result", "measurement", "response", "endpoint_value", "endpoint value", "measured_value"],
        "regex": [],
        "priority": 85,
        "category": "bioactivity",
        "label": "Endpoint Value / Potency"
    },
    "unit": {
        "aliases": ["unit", "measurement unit", "concentration unit", "dose unit"],
        "regex": [],
        "priority": 75,
        "category": "metadata",
        "label": "Measurement Unit"
    },
    "ghs_classification": {
        "aliases": ["ghs", "hazard_class", "signal_word", "danger", "warning", "h_statement", "p_statement", "hazard_category", "ghs_label"],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "GHS Hazard Classification"
    },
    "assay_type": {
        "aliases": ["assay_type", "assay type", "assay_format", "test format"],
        "regex": [],
        "priority": 80,
        "category": "metadata",
        "label": "Assay Type"
    },
    "ph": {
        "aliases": ["ph", "acidity", "hydrogen ion concentration"],
        "regex": [],
        "priority": 80,
        "category": "metadata",
        "label": "pH"
    }
}

# Flat registry mapping for backward compatibility and fast lookups
UNIVERSAL_ONTOLOGY: Dict[str, List[str]] = {}
for standard_key, meta in SCIENTIFIC_VARIABLES.items():
    UNIVERSAL_ONTOLOGY[standard_key] = list(meta["aliases"])
