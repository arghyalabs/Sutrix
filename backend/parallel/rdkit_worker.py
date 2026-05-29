import os
import sys
import logging
from typing import List, Dict, Any, Tuple

# Simple print logger as stderr/stdout is forwarded by ProcessPoolExecutor
def log_info(msg: str):
    print(f"[Worker PID {os.getpid()}] INFO: {msg}", flush=True)

def log_error(msg: str):
    print(f"[Worker PID {os.getpid()}] ERROR: {msg}", flush=True, file=sys.stderr)

# Ensure RDKit is imported safely inside worker subprocesses
_RDKIT_AVAILABLE = False
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    from backend.descriptor_engine.descriptor_registry import calculate_all, DESCRIPTOR_FUNCTIONS
    from backend.descriptor_engine.descriptor_validator import validate_descriptors
    from backend.descriptor_engine.mordred_engine import MordredEngine
    _RDKIT_AVAILABLE = True
except ImportError as err:
    pass

def compute_smiles_descriptors(smiles: str, include_mordred: bool = False, mode: str = "fast", selected_descriptors: List[str] = None) -> Dict[str, Any]:
    """Calculates molecular properties for a single SMILES string."""
    if not _RDKIT_AVAILABLE:
        return {"success": False, "error": "RDKIT_NOT_AVAILABLE", "data": {}}

    if not smiles or not isinstance(smiles, str) or not smiles.strip():
        return {"success": False, "error": "EMPTY_OR_INVALID_SMILES", "data": {}}

    clean_smiles = smiles.strip()
    
    try:
        mol = Chem.MolFromSmiles(clean_smiles)
        if mol is None:
            return {"success": False, "error": "PARSE_FAILURE: Invalid SMILES string", "data": {}}
        
        # Coerce computation mode
        if mode == "fast":
            rdkit_mode = "fast"
            run_mordred = False
        elif mode == "standard":
            rdkit_mode = "standard"
            run_mordred = False
        elif mode == "full":
            rdkit_mode = "standard"
            run_mordred = True
        else:
            rdkit_mode = "standard"
            run_mordred = include_mordred

        # Compute RDKit descriptors
        raw_descriptors = calculate_all(mol, mode=rdkit_mode, selected_descriptors=selected_descriptors)
        
        # Calculate structural identifiers
        try:
            raw_descriptors["CanonicalSMILES"] = Chem.MolToSmiles(mol, isomericSmiles=False)
            raw_descriptors["IsomericSMILES"] = Chem.MolToSmiles(mol, isomericSmiles=True)
            raw_descriptors["InChIKey"] = Chem.MolToInchiKey(mol)
            raw_descriptors["MolecularFormula"] = rdMolDescriptors.CalcMolFormula(mol)
        except Exception:
            pass

        # Validate results and prune NaNs
        expected_keys = list(DESCRIPTOR_FUNCTIONS.keys())
        validated_data = validate_descriptors(raw_descriptors, required_keys=expected_keys)
        
        for k in ["CanonicalSMILES", "IsomericSMILES", "InChIKey", "MolecularFormula"]:
            if k in raw_descriptors:
                validated_data[k] = raw_descriptors[k]

        # Calculate extended Mordred descriptors if requested
        if run_mordred:
            mordred_calc = MordredEngine(timeout_seconds=15)
            # Filter mordred calculation to only selected_descriptors if provided
            mordred_res = mordred_calc.calculate(mol, selected_descriptors=selected_descriptors)
            if mordred_res.get("success"):
                for k, v in mordred_res.get("data", {}).items():
                    if k not in validated_data:
                        validated_data[k] = v

        return {"success": True, "data": validated_data}

    except Exception as e:
        return {"success": False, "error": f"CRITICAL_ERROR: {str(e)}", "data": {}}

def calculate_batch_worker(smiles_list: List[str], include_mordred: bool = False, mode: str = "fast", selected_descriptors: List[str] = None) -> List[Tuple[str, Dict[str, Any]]]:
    """Processes a batch list of SMILES strings inside a worker subprocess."""
    log_info(f"Received calculation chunk of {len(smiles_list)} items in mode='{mode}'")
    results = []
    for smiles in smiles_list:
        res = compute_smiles_descriptors(smiles, include_mordred=include_mordred, mode=mode, selected_descriptors=selected_descriptors)
        results.append((smiles, res))
    log_info(f"Completed chunk of {len(smiles_list)} items.")
    return results
