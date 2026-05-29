import logging
from typing import Dict, Any
from .descriptor_registry import calculate_all, DESCRIPTOR_FUNCTIONS
from .descriptor_validator import validate_descriptors
from .mordred_engine import MordredEngine

try:
    from rdkit import Chem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

logger = logging.getLogger("sdo.backend.descriptors.engine")

class RDKitEngine:
    """
    Stable local RDKit descriptor calculation engine.
    No internet dependency required.
    """
    def __init__(self):
        if not RDKIT_AVAILABLE:
            logger.error("RDKit is not installed or available. Local descriptor calculations will fail.")
        self.mordred_engine = MordredEngine(timeout_seconds=15)
        self.total_molecules = 0
        self.successful_parses = 0
        self.failed_parses = 0
        self.validation_results = []
    def calculate_from_smiles(self, smiles: str, include_mordred: bool = False, mode: str = "fast") -> Dict[str, Any]:
        """
        Parses SMILES and computes registered molecular descriptors.
        Optionally calculates extended Mordred descriptors.
        """
        if not RDKIT_AVAILABLE:
            return {"success": False, "error": "RDKIT_NOT_AVAILABLE", "data": {}}
            
        if not smiles or not isinstance(smiles, str) or not smiles.strip():
            return {"success": False, "error": "EMPTY_OR_INVALID_SMILES", "data": {}}

        clean_smiles = smiles.strip()
        
        # --- RDKIT PARSE VALIDATION DEBUG ---
        mol = None
        error_reason = ""
        rdkit_success = False
        
        try:
            mol = Chem.MolFromSmiles(clean_smiles)
            if mol is None:
                error_reason = "PARSE_FAILURE"
            else:
                rdkit_success = True
        except Exception as e:
            error_reason = str(e)
            
        logger.info(f"RDKIT DEBUG: canonical_smiles='{clean_smiles}' | success={rdkit_success} | error='{error_reason}'")
        
        self.total_molecules += 1
        if rdkit_success:
            self.successful_parses += 1
        else:
            self.failed_parses += 1
            
        logger.info(f"RDKIT COUNTERS: total molecules={self.total_molecules}, successful parses={self.successful_parses}, failed parses={self.failed_parses}")
        
        if not rdkit_success:
            return {"success": False, "error": f"PARSE_FAILURE: {error_reason}", "data": {}}
        # --- END RDKIT PARSE VALIDATION DEBUG ---

        # Determine calculation details based on the high-level mode
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

        try:
            # Perform RDKit calculations according to the chosen mode
            raw_descriptors = calculate_all(mol, mode=rdkit_mode)
            
            # Extract identifiers (Canonical, Formula, etc.) separately
            try:
                raw_descriptors["CanonicalSMILES"] = Chem.MolToSmiles(mol, isomericSmiles=False)
                raw_descriptors["IsomericSMILES"] = Chem.MolToSmiles(mol, isomericSmiles=True)
                raw_descriptors["InChIKey"] = Chem.MolToInchiKey(mol)
                from rdkit.Chem import rdMolDescriptors
                raw_descriptors["MolecularFormula"] = rdMolDescriptors.CalcMolFormula(mol)
            except Exception:
                pass # Non-critical if identifier generation fails

            # Validate and clean NaNs
            expected_keys = list(DESCRIPTOR_FUNCTIONS.keys())
            validated_data = validate_descriptors(raw_descriptors, required_keys=expected_keys)
            
            # Ensure identifiers are passed through unmodified by validation
            for k in ["CanonicalSMILES", "IsomericSMILES", "InChIKey", "MolecularFormula"]:
                if k in raw_descriptors:
                    validated_data[k] = raw_descriptors[k]

            # Optionally include Mordred extended descriptors
            if run_mordred:
                mordred_res = self.mordred_engine.calculate(mol)
                if mordred_res.get("success"):
                    # Merge Mordred data into validated_data, preserving existing RDKit keys
                    for k, v in mordred_res.get("data", {}).items():
                        if k not in validated_data:
                            validated_data[k] = v

            return {"success": True, "data": validated_data}

        except Exception as e:
            logger.error(f"Critical error calculating descriptors for {smiles}: {str(e)}")
            return {"success": False, "error": f"CRITICAL_ERROR: {str(e)}", "data": {}}
