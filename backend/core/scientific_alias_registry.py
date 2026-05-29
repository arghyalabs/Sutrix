"""
Universal Scientific Variable Registry
Contains alias ontologies for semantic mapping.
"""

CHEMICAL_IDENTIFIERS = {
    "canonical_smiles": [
        "smiles", "canonical_smiles", "canon_smiles", "isomeric_smiles", 
        "compound_smiles", "molecule_smiles", "structure", "chemical_structure", 
        "mol_smiles", "rdkit_smiles", "clean_smiles", "normalized_smiles", 
        "compound_structure", "ligand_smiles"
    ],
    "inchi": ["inchi", "inchi_key", "inchikey", "inchi-code"],
    "cas_number": ["cas", "cas_number", "cas_no", "cas_rn", "registry_number", "casid", "chemical_registry"],
    "chemical_name": [
        "compound", "compound_name", "molecule", "molecule_name", "drug", 
        "drug_name", "chemical", "chemical_name", "ligand", "substance", 
        "analyte", "sample_name"
    ]
}

BIOACTIVITY_VARIABLES = {
    "ic50": ["ic50", "ic_50", "pic50", "pic_50", "half_max_inhibitory_concentration", "inhibition_ic50"],
    "ec50": ["ec50", "ec_50", "pec50", "activation_ec50"],
    "ki": ["ki", "binding_affinity", "inhibition_constant"],
    "potency": ["potency", "activity", "bioactivity", "response", "effect", "activity_score"],
    "toxicity": ["toxicity", "toxic", "cytotoxicity", "hepatotoxicity", "cardiotoxicity", "neurotoxicity", "genotoxicity", "carcinogenicity", "mutagenicity", "teratogenicity"]
}

ADMET_VARIABLES = {
    "absorption": ["hia", "human_intestinal_absorption", "caco2", "caco_2", "absorption", "permeability"],
    "distribution": ["vd", "volume_distribution", "ppb", "plasma_protein_binding", "bbb", "blood_brain_barrier"],
    "metabolism": ["cyp3a4", "cyp2d6", "cyp2c9", "metabolism", "metabolic_stability", "clearance"],
    "excretion": ["renal_clearance", "excretion", "half_life", "t_half"],
    "toxicology": ["ld50", "lc50", "acute_toxicity", "chronic_toxicity", "tox21", "toxcast"]
}

PHYSICOCHEMICAL_VARIABLES = {
    "molecular_weight": ["mw", "mol_weight", "molecular_weight", "exact_mass", "formula_weight"],
    "logp": ["logp", "xlogp", "clogp", "alogp", "lipophilicity", "partition_coefficient"],
    "tpsa": ["tpsa", "polar_surface_area", "topological_surface_area"],
    "hbd": ["hbd", "hbond_donor", "hydrogen_bond_donor"],
    "hba": ["hba", "hbond_acceptor", "hydrogen_bond_acceptor"],
    "rotatable_bonds": ["rotb", "rotatable_bonds", "n_rotatable_bonds"]
}

METADATA_VARIABLES = {
    "target": ["target", "protein", "gene", "enzyme", "receptor", "pathway", "assay_target", "protein_target", "target_name", "gene_symbol"],
    "assay": ["assay", "assay_type", "bioassay", "screen", "experiment", "protocol", "test_type", "endpoint", "endpoint_name"],
    "classification_target": ["active", "inactive", "binary_class", "class", "label", "outcome", "response_class", "tox_class"],
    "regression_target": ["value", "score", "measurement", "concentration", "activity_value", "continuous_response", "response_value"]
}

# Compile all into one global registry
UNIVERSAL_ONTOLOGY = {}
for category in [CHEMICAL_IDENTIFIERS, BIOACTIVITY_VARIABLES, ADMET_VARIABLES, PHYSICOCHEMICAL_VARIABLES, METADATA_VARIABLES]:
    for standard_key, aliases in category.items():
        if standard_key not in UNIVERSAL_ONTOLOGY:
            UNIVERSAL_ONTOLOGY[standard_key] = []
        UNIVERSAL_ONTOLOGY[standard_key].extend(aliases)
