import logging
from typing import Callable, Dict, Any
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

logger = logging.getLogger("sdo.backend.descriptors.registry")

# Standard registry of calculations
# Each maps a metric name to a function taking an rdkit molecule.

DESCRIPTOR_FUNCTIONS: Dict[str, Callable[[Chem.Mol], Any]] = {
    "MolWt": lambda mol: Descriptors.ExactMolWt(mol),
    "LogP": lambda mol: Descriptors.MolLogP(mol),
    "TPSA": lambda mol: Descriptors.TPSA(mol),
    "HBA": lambda mol: Descriptors.NumHAcceptors(mol),
    "HBD": lambda mol: Descriptors.NumHDonors(mol),
    "RotatableBonds": lambda mol: Descriptors.NumRotatableBonds(mol),
    "RingCount": lambda mol: Descriptors.RingCount(mol),
    "HeavyAtomCount": lambda mol: Descriptors.HeavyAtomCount(mol),
    "FractionCSP3": lambda mol: Descriptors.FractionCSP3(mol)
}

def calculate_all(mol: Chem.Mol, mode: str = "fast", selected_descriptors: list = None) -> Dict[str, Any]:
    """Calculate registered descriptors for a given molecule according to selected descriptors."""
    results = {}
    
    if selected_descriptors is not None and len(selected_descriptors) > 0:
        selected_set = set(selected_descriptors)
        
        # Calculate RDKit descriptors only if they are in the selected_set
        # Check custom base functions first
        for name, func in DESCRIPTOR_FUNCTIONS.items():
            if name in selected_set:
                try:
                    results[name] = func(mol)
                except Exception as e:
                    logger.warning(f"Failed to calculate {name}: {str(e)}")
                    results[name] = None
                    
        # Check if any selected descriptors are standard RDKit descriptors not yet computed
        rdkit_desc_dict = dict(Descriptors._descList)
        for desc_name in selected_set:
            if desc_name not in results and desc_name in rdkit_desc_dict:
                try:
                    results[desc_name] = rdkit_desc_dict[desc_name](mol)
                except Exception as e:
                    logger.warning(f"Failed to calculate standard RDKit descriptor {desc_name}: {str(e)}")
                    results[desc_name] = None
    else:
        # Fallback to legacy mode behavior if no specific descriptors are provided
        if mode == "fast":
            for name, func in DESCRIPTOR_FUNCTIONS.items():
                try:
                    results[name] = func(mol)
                except Exception as e:
                    logger.warning(f"Failed to calculate {name} in fast mode: {str(e)}")
                    results[name] = None
        else:
            try:
                all_descs = Descriptors.CalcMolDescriptors(mol)
                results.update(all_descs)
            except Exception as e:
                logger.warning(f"Failed to calculate RDKit base descriptors: {str(e)}")

            for name, func in DESCRIPTOR_FUNCTIONS.items():
                if name not in results:
                    try:
                        val = func(mol)
                        results[name] = val
                    except Exception as e:
                        logger.warning(f"Failed to calculate {name}: {str(e)}")
                        results[name] = None
    return results
