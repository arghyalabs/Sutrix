import re
from typing import Dict, Any, List

# Pre-compiled regex patterns for chemical identifiers and numbers
CAS_REGEX = re.compile(r"\b\d{2,7}-\d{2}-\d\b")
INCHI_REGEX = re.compile(r"^inchi=1s?/[a-z0-9\.]+/.*", re.IGNORECASE)
INCHIKEY_REGEX = re.compile(r"^[a-z]{14}-[a-z]{10}-[a-z\d]$", re.IGNORECASE)
# General smiles character validator: check typical letters and bond symbols
SMILES_HEURISTIC_REGEX = re.compile(r"^(?=[CHONSPFIClBrIH])(?=.*[a-zA-Z])[a-zA-Z0-9\(\)\=\#\+\-\[\]\/\@\.\:\\]+$")

SCIENTIFIC_VARIABLES: Dict[str, Dict[str, Any]] = {
    "canonical_smiles": {
        "aliases": [
            "smiles", "canonical_smiles", "canon_smiles", "isomeric_smiles", 
            "smiles_string", "structure", "mol_structure", "mol", 
            "chem_structure", "rdkit_smiles", "clean_smiles", 
            "normalized_smiles", "compound_structure", "ligand_smiles", 
            "structure_formula", "structural_smiles"
        ],
        "regex": [SMILES_HEURISTIC_REGEX],
        "priority": 100,
        "category": "chemical_identifier",
        "label": "Canonical SMILES"
    },
    "inchi": {
        "aliases": ["inchi", "inchi_key", "inchi-code", "inchi_string", "inchi_structure", "ec number", "einecs"],
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
    "cas_number": {
        "aliases": [
            "cas", "cas_number", "cas_no", "cas_rn", "registry_number", 
            "casid", "chemical_registry", "casrn", "cas rn", "registry number"
        ],
        "regex": [CAS_REGEX],
        "priority": 90,
        "category": "chemical_identifier",
        "label": "CAS Number"
    },
    "pubchem_cid": {
        "aliases": ["pubchem_cid", "cid", "sid", "pubchem compound id", "cid_number", "pubchem_id", "sid_number"],
        "regex": [],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "PubChem CID"
    },
    "chembl_id": {
        "aliases": ["chembl_id", "chembl", "chembl_molecule_id", "chembl_compound_id"],
        "regex": [re.compile(r"^chembl\d+$", re.IGNORECASE)],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "ChEMBL ID"
    },
    "drugbank_id": {
        "aliases": ["drugbank_id", "drugbank", "drugbank_accession"],
        "regex": [re.compile(r"^db\d+$", re.IGNORECASE)],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "DrugBank ID"
    },
    "dsstox_id": {
        "aliases": ["dsstox_id", "dsstox", "dtxsid", "dtxcid", "epa_dsstox"],
        "regex": [re.compile(r"^dtxsid\d+$", re.IGNORECASE)],
        "priority": 85,
        "category": "chemical_identifier",
        "label": "DSSTox ID"
    },
    "echa_id": {
        "aliases": ["echa_id", "echa", "reach_reg", "substance_id", "compoundid", "cmpd", "substance_uuid"],
        "regex": [],
        "priority": 80,
        "category": "chemical_identifier",
        "label": "ECHA ID"
    },
    "chemical_name": {
        "aliases": [
            "compound", "compound_name", "molecule", "molecule_name", "drug", 
            "drug_name", "chemical", "chemical_name", "ligand", "substance", 
            "analyte", "sample_name", "iupac_name", "preferred_name", "synonym", 
            "substance_name", "preferred compound name", "chem_name"
        ],
        "regex": [],
        "priority": 75,
        "category": "chemical_identifier",
        "label": "Chemical Name"
    },
    "molecular_formula": {
        "aliases": ["molecular_formula", "formula", "chemical_formula", "stoichiometry"],
        "regex": [],
        "priority": 70,
        "category": "chemical_identifier",
        "label": "Molecular Formula"
    },
    "molecular_weight": {
        "aliases": [
            "mw", "mol_weight", "molecular_weight", "exact_mass", 
            "formula_weight", "monoisotopic_mass", "m_w", "molecularmass"
        ],
        "regex": [],
        "priority": 70,
        "category": "physicochemical",
        "label": "Molecular Weight"
    },
    "value": {
        "aliases": ["value", "potency", "result", "measurement", "response", "endpoint_value", "endpoint value", "measured_value"],
        "regex": [],
        "priority": 85,
        "category": "bioactivity",
        "label": "Endpoint Value / Potency"
    },
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
            "feeding", "locomotion", "avoidance", "atp", "gst", "catalase", "enzyme_activity"
        ],
        "regex": [],
        "priority": 95,
        "category": "bioactivity",
        "label": "Toxicity / Bioassay Endpoint"
    },
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
    "sex": {
        "aliases": ["sex", "gender", "biological sex", "male", "female", "mixed", "unknown"],
        "regex": [],
        "priority": 60,
        "category": "metadata",
        "label": "Biological Sex"
    },
    "age": {
        "aliases": [
            "age", "life_stage", "developmental_stage", "maturity", "juvenile", 
            "adult", "neonatal", "embryo", "larval", "adolescent", "aged", "stage"
        ],
        "regex": [],
        "priority": 60,
        "category": "metadata",
        "label": "Age / Life Stage"
    },
    "exposure_time": {
        "aliases": [
            "exposure_time", "incubation_time", "duration", "observation_period", 
            "exposure duration", "incubation", "study_length", "treatment_period", 
            "timepoint", "hours", "hr", "h", "days", "d", "weeks", "months", "time", "exposure_duration"
        ],
        "regex": [],
        "priority": 85,
        "category": "metadata",
        "label": "Exposure Duration"
    },
    "qualifier": {
        "aliases": ["qualifier", "operator", "relation", "comparator", "comparison", "inequality"],
        "regex": [],
        "priority": 75,
        "category": "metadata",
        "label": "Inequality Qualifier"
    },
    "unit": {
        "aliases": ["unit", "measurement unit", "concentration unit", "dose unit"],
        "regex": [],
        "priority": 75,
        "category": "metadata",
        "label": "Measurement Unit"
    },
    "target": {
        "aliases": [
            "target", "target_name", "protein_target", "gene_symbol", "biomarker", 
            "cyp3a4", "cyp2d6", "herg", "egfr", "vegfr", "ppar", "er_alpha", "ar", 
            "ahr", "protein", "receptor", "enzyme", "transporter", "ion_channel"
        ],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "Target Protein / Receptor"
    },
    "metabolite": {
        "aliases": [
            "metabolite", "metabolite_name", "metabolite_id", "transformation", 
            "phase i metabolite", "phase ii metabolite", "degradation product", 
            "transformation product", "hydrolysis product", "degradant"
        ],
        "regex": [],
        "priority": 65,
        "category": "metadata",
        "label": "Metabolite / Fate Product"
    },
    "descriptor": {
        "aliases": [
            "logp", "xlogp", "tpsa", "hba", "hbd", "rotatable bonds", 
            "molecular complexity", "aromatic rings", "heavy atoms", 
            "fractional sp3", "qed", "synthetic accessibility", 
            "physicochemical", "topological", "constitutional", "electronic", 
            "geometrical", "quantum", "bcut", "chi", "kappa", "estate", "vsa", 
            "autocorr", "ats", "gats", "rdf", "whim", "getaway", "morse", 
            "lipophilicity", "partition_coefficient", "polar_surface_area"
        ],
        "regex": [],
        "priority": 50,
        "category": "physicochemical",
        "label": "Molecular Descriptor"
    },
    "ghs_classification": {
        "aliases": [
            "ghs", "hazard_class", "signal_word", "danger", "warning", 
            "h_statement", "p_statement", "hazard_category", "ghs_label"
        ],
        "regex": [],
        "priority": 70,
        "category": "metadata",
        "label": "GHS Hazard Classification"
    },
    "test_type": {
        "aliases": ["test_type", "test type", "study design", "study_type", "experiment_type", "assay design"],
        "regex": [],
        "priority": 80,
        "category": "metadata",
        "label": "Test Type / Study Design"
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
